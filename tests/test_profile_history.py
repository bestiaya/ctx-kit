"""Behavior fixtures for read-only, bounded native-history retrieval."""
import contextlib
import hashlib
import io
import json
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from profile_history import ConfigurationError, main, read_history


class HistoryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve()
        self.logs = self.root / "logs"
        self.logs.mkdir()
        self.config = self.root / "config.json"
        self.configure()

    def configure(self, roots=None, db=None):
        history = {"roots": [str(self.logs)] if roots is None else roots,
                   "metadata_db": str(db) if db else None}
        self.config.write_text(json.dumps({"agents": {
            "codex": {"history": history}, "claude_code": {"history": history}}}))

    def write(self, filename, records):
        path = self.logs / filename
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("".join(json.dumps(row) + "\n" for row in records), encoding="utf-8")
        return path

    def meta(self, sid="thread-1", cwd="/project"):
        return {"type": "session_meta", "payload": {"id": sid, "cwd": cwd}}

    def response(self, payload, timestamp="2026-10-08T15:00:00Z"):
        return {"type": "response_item", "timestamp": timestamp, "payload": payload}

    def discussion(self, text, role="user", **kwargs):
        return self.response({"type": "message", "role": role, "content": [
            {"type": "input_text", "text": text}], **kwargs})

    def test_canonical_codex_stream_and_tool_provenance_exclude_reasoning(self):
        path = self.write("rollout-thread-1.jsonl", [self.meta(),
            {"type": "event_msg", "payload": {"type": "user_message", "message": "topic"}},
            self.discussion("topic discussion"),
            self.discussion("topic secret analysis", role="assistant", channel="analysis"),
            self.response({"type": "reasoning", "summary": [{"text": "topic hidden"}]}),
            self.response({"type": "function_call", "name": "run", "call_id": "c1",
                           "arguments": "topic actual call"}),
            self.response({"type": "function_call_output", "call_id": "c1",
                           "output": "topic returned failure"})])
        before = path.read_bytes()
        report = read_history(self.config, "codex", session="thread-1", query="TOPIC")
        self.assertEqual([m["kind"] for m in report["matches"]],
                         ["discussion", "tool_call", "tool_result"])
        self.assertEqual([m["line"] for m in report["matches"]], [3, 6, 7])
        self.assertEqual([m["call_id"] for m in report["matches"]], [None, "c1", "c1"])
        self.assertEqual(report["matches"][0]["path"], str(path))
        self.assertEqual(report["matches"][0]["session"], "thread-1")
        self.assertEqual(report["matches"][0]["timestamp"], "2026-10-08T15:00:00Z")
        self.assertEqual(report["coverage"]["skipped_event_messages"], 1)
        self.assertEqual(path.read_bytes(), before)
        discussions = read_history(self.config, "codex", session="thread-1", query="topic", kind="discussion")
        self.assertEqual([m["text"] for m in discussions["matches"]], ["topic discussion"])

    def test_sqlite_exact_id_fallback_and_source_identity_check_are_read_only(self):
        actual = self.write("nonstandard-name.jsonl", [self.meta(), self.discussion("topic")])
        wrong = self.write("rollout-thread-1-wrong.jsonl", [self.meta("thread-2"), self.discussion("wrong topic")])
        db = self.root / "metadata.sqlite"
        with contextlib.closing(sqlite3.connect(str(db))) as conn, conn:
            conn.execute("CREATE TABLE threads (id TEXT PRIMARY KEY, rollout_path TEXT)")
            conn.execute("INSERT INTO threads VALUES (?, ?)", ("thread-1", str(actual)))
        self.configure(db=db)
        original = hashlib.sha256(db.read_bytes()).digest()
        before_files = set(self.root.iterdir())
        report = read_history(self.config, "codex", session="thread-1", project="/project", query="topic")
        self.assertEqual(len(report["matches"]), 1)
        self.assertEqual(report["matches"][0]["path"], str(actual))
        self.assertTrue(report["coverage"]["metadata_lookup"])
        self.assertEqual(report["coverage"]["filtered_files"], 1)
        self.assertEqual(hashlib.sha256(db.read_bytes()).digest(), original)
        self.assertEqual(set(self.root.iterdir()), before_files)
        # An injection-looking ID cannot broaden the exact parameterized lookup.
        empty = read_history(self.config, "codex", session="' OR 1=1 --", query="topic")
        self.assertEqual(empty["matches"], [])
        self.assertIn("metadata_id_missing", {w["code"] for w in empty["warnings"]})

    def test_db_cannot_replace_rollout_project_or_session_verification(self):
        path = self.write("other.jsonl", [self.meta("another", "/other"), self.discussion("topic")])
        db = self.root / "metadata.sqlite"
        with contextlib.closing(sqlite3.connect(str(db))) as conn, conn:
            conn.execute("CREATE TABLE threads (id TEXT, rollout_path TEXT)")
            conn.execute("INSERT INTO threads VALUES (?, ?)", ("thread-1", str(path)))
        self.configure(roots=[], db=db)
        report = read_history(self.config, "codex", session="thread-1", project="/project")
        self.assertEqual(report["matches"], [])
        self.assertEqual(report["coverage"]["verified_files"], 0)

    def test_project_date_and_limit_preserve_precise_coverage(self):
        records = [self.meta()]
        for text, stamp in [("too early", "2026-10-07T23:59:59Z"),
                            ("first", "2026-10-08T00:00:00Z"),
                            ("second", "2026-10-09T00:30:00+08:00"),
                            ("too late", "2026-10-09T00:00:00Z"),
                            ("undated", None)]:
            row = self.discussion(text)
            row["timestamp"] = stamp
            records.append(row)
        self.write("thread-1.jsonl", records)
        self.write("thread-2.jsonl", [self.meta("thread-2", "/other"), self.discussion("outside")])
        report = read_history(self.config, "codex", project="/project/", limit=1,
                              date_from="2026-10-08", date_to="2026-10-08")
        self.assertEqual([m["text"] for m in report["matches"]], ["first"])
        self.assertEqual(report["coverage"]["matched_records"], 2)
        self.assertEqual(report["coverage"]["undated_records"], 1)
        self.assertEqual(report["coverage"]["filtered_files"], 1)
        self.assertTrue(report["coverage"]["truncated"])

    def test_corrupt_line_and_unfinished_tail_report_but_keep_valid_evidence(self):
        path = self.write("thread-1.jsonl", [self.meta(), self.discussion("valid")])
        with path.open("a") as stream:
            stream.write('bad\n{"unfinished":')
        self.configure(roots=[str(self.logs), str(self.root / "missing")])
        report = read_history(self.config, "codex", session="thread-1")
        self.assertEqual([m["text"] for m in report["matches"]], ["valid"])
        self.assertEqual(report["status"], "partial")
        self.assertEqual(report["coverage"]["malformed_lines"], 1)
        self.assertEqual(report["coverage"]["truncated_lines"], 1)
        self.assertEqual({w["code"] for w in report["warnings"]},
                         {"missing_root", "malformed_lines", "truncated_lines"})
        self.assertIn("不能推断从未发生", report["note"])

    def test_missing_meta_and_missing_db_never_create_files(self):
        self.write("thread-1.jsonl", [self.discussion("unverified")])
        missing = self.root / "does-not-exist.sqlite"
        self.configure(db=missing)
        report = read_history(self.config, "codex", session="thread-1")
        self.assertEqual(report["matches"], [])
        self.assertFalse(missing.exists())
        self.assertIn("unreadable_metadata", {w["code"] for w in report["warnings"]})
        self.assertIn("missing_identity", {w["code"] for w in report["warnings"]})

    def test_claude_text_calls_results_and_uuid_dedup_without_thinking_or_subagents(self):
        assistant = {"type": "assistant", "sessionId": "claude-session", "cwd": "/project",
                     "timestamp": "2026-10-08T00:00:00Z", "uuid": "reply-1",
                     "message": {"content": [{"type": "thinking", "thinking": "topic secret"},
                         {"type": "text", "text": "topic discussion"},
                         {"type": "tool_use", "id": "tool-1", "name": "Read", "input": {"path": "topic"}}]}}
        result = {"type": "user", "sessionId": "claude-session", "cwd": "/project",
                  "timestamp": "2026-10-08T00:01:00Z", "uuid": "result-1",
                  "message": {"content": [{"type": "tool_result", "tool_use_id": "tool-1",
                      "content": [{"type": "text", "text": "topic actual return"},
                                  {"type": "thinking", "thinking": "topic hidden"}]}]}}
        path = self.write("claude-session.jsonl", [assistant, assistant, result,
                         {**assistant, "uuid": "sub-reply", "isSidechain": True}])
        self.write("claude-session/subagents/agent-x.jsonl", [assistant])
        report = read_history(self.config, "claude_code", session="claude-session", query="topic")
        self.assertEqual([m["kind"] for m in report["matches"]], ["discussion", "tool_call", "tool_result"])
        self.assertEqual(report["matches"][-1]["text"], "topic actual return")
        self.assertEqual(report["matches"][-1]["call_id"], "tool-1")
        self.assertEqual(report["matches"][0]["path"], str(path))
        self.assertEqual(report["coverage"]["skipped_subagents"], 2)
        self.assertNotIn("secret", json.dumps(report))

    def test_claude_filename_is_hint_and_actual_session_is_verified(self):
        self.write("claude-session.jsonl", [{"type": "user", "sessionId": "different",
                    "cwd": "/project", "message": {"content": "do not return"}}])
        report = read_history(self.config, "claude_code", session="claude-session")
        self.assertEqual(report["matches"], [])
        self.assertEqual(report["coverage"]["filtered_records"], 1)

    def test_relative_roots_empty_adapter_and_cli_configuration_error(self):
        self.configure(roots=["logs"])
        self.write("thread-1.jsonl", [self.meta(), self.discussion("topic")])
        self.assertEqual(len(read_history(self.config, "codex")["matches"]), 1)
        self.configure(roots=[])
        report = read_history(self.config, "claude_code")
        self.assertEqual(report["status"], "partial")
        self.assertIn("unconfigured_history", {w["code"] for w in report["warnings"]})
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            exit_code = main(["--config", str(self.root / "missing-config"), "--agent", "codex"])
        self.assertEqual(exit_code, 2)
        self.assertEqual(json.loads(output.getvalue())["status"], "error")
        with self.assertRaises(ConfigurationError):
            read_history(self.config, "codex", date_from="not-a-date")
        with self.assertRaises(ConfigurationError):
            read_history(self.config, "codex", limit=0)

    def test_default_limit_and_invalid_metadata_schema_are_explicit(self):
        self.write("thread-1.jsonl", [self.meta()] + [self.discussion(str(n)) for n in range(25)])
        db = self.root / "metadata.sqlite"
        with contextlib.closing(sqlite3.connect(str(db))) as conn, conn:
            conn.execute("CREATE TABLE threads (unknown TEXT)")
        self.configure(db=db)
        report = read_history(self.config, "codex", session="thread-1")
        self.assertEqual(len(report["matches"]), 20)
        self.assertEqual(report["coverage"]["matched_records"], 25)
        self.assertTrue(report["coverage"]["truncated"])
        self.assertIn("unsupported_metadata", {w["code"] for w in report["warnings"]})


if __name__ == "__main__":
    unittest.main()
