#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""test_cache_audit.py — unit tests for scripts/cache-audit.py, the weekly checkup script.

The script is run as a real subprocess against synthetic jsonl transcripts written under /tmp
— a handful of made-up assistant records with made-up numbers. No real session log is read.

Run:
    python3 -m pytest scripts/tests -q
    python3 -m unittest discover -s scripts/tests
Use a working python3 — on macOS /usr/bin/python3 is an Xcode shim that cannot even import json.
"""
import io
import json
import os
import shutil
import subprocess
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
SCRIPT = os.path.join(ROOT, "scripts", "cache-audit.py")
FIXTURES = os.environ.get("CTXKIT_TEST_DIR") or "/tmp/ctx-cache-audit-tests"


def setUpModule():
    os.makedirs(FIXTURES, exist_ok=True)


def record(when, tokens=(1000, 2000, 3000), mid="msg_synthetic"):
    given, read, created = tokens
    return {
        "type": "assistant",
        "isSidechain": False,
        "timestamp": when,
        "message": {
            "id": mid,
            "role": "assistant",
            "usage": {
                "input_tokens": given,
                "cache_read_input_tokens": read,
                "cache_creation_input_tokens": created,
                "output_tokens": 100,
            },
        },
    }


def transcript(where, name, stamps, mtime):
    """One synthetic session log, with its mtime set by hand."""
    path = os.path.join(where, name)
    with io.open(path, "w", encoding="utf-8") as fh:
        for n, when in enumerate(stamps):
            fh.write(json.dumps(record(when, mid="msg_%d" % n)) + "\n")
    os.utime(path, (mtime, mtime))
    return path


def call(when, tid, name, mid):
    """One assistant record that calls a tool."""
    return {
        "type": "assistant",
        "isSidechain": False,
        "timestamp": when,
        "message": {
            "id": mid,
            "role": "assistant",
            "content": [{"type": "tool_use", "id": tid, "name": name, "input": {}}],
            "usage": {
                "input_tokens": 10,
                "cache_read_input_tokens": 20,
                "cache_creation_input_tokens": 30,
                "output_tokens": 5,
            },
        },
    }


def result(tid, text):
    """One user record carrying the tool result that answers `tid`."""
    return {
        "type": "user",
        "timestamp": "2026-09-09T10:00:01.000Z",
        "message": {
            "role": "user",
            "content": [{"type": "tool_result", "tool_use_id": tid,
                         "content": [{"type": "text", "text": text}]}],
        },
    }


def session(where, name, echoes):
    """A synthetic session log: one call and one result per (tool name, characters) pair."""
    path = os.path.join(where, name)
    with io.open(path, "w", encoding="utf-8") as fh:
        for n, (tool, size) in enumerate(echoes):
            tid = "t%d" % n
            fh.write(json.dumps(call("2026-09-09T10:0%d:00.000Z" % n, tid, tool, "m%d" % n)) + "\n")
            fh.write(json.dumps(result(tid, "x" * size)) + "\n")
    return path


def subagent(where, parent_stem, name, echoes):
    """The same, written where a subagent of `parent_stem` keeps its transcript."""
    here = os.path.join(where, parent_stem, "subagents")
    os.makedirs(here, exist_ok=True)
    return session(here, name, echoes)


def run(where):
    return subprocess.run(
        [sys.executable, SCRIPT, "--project", where, "--cases", where, "--all", "0"],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)


def table(out):
    """The session column of the printed table, in the order it was printed."""
    rows = []
    for line in out.split("\n"):
        if not line or line.startswith("#") or line.startswith("session") or line.startswith("("):
            continue
        rows.append(line.split()[0])
    return rows


class Order(unittest.TestCase):
    """Newest first — by what the log says, not by what the filesystem says.

    A directory that has been copied, restored or synced carries the same mtime on every file
    in it, so an order taken off mtime is an accident of the copy. Measured on this machine's
    own project directory while this was changed: 15 of 21 rows moved, and one session moved
    from fifth place to eighteenth.
    """

    def setUp(self):
        self.where = os.path.join(FIXTURES, self._testMethodName)
        os.makedirs(self.where, exist_ok=True)
        for name in os.listdir(self.where):
            os.remove(os.path.join(self.where, name))

    def test_the_order_follows_the_timestamps_not_the_mtimes(self):
        # older inside, newer mtime — the two orders are exact opposites
        transcript(self.where, "older.jsonl",
                   ["2026-09-01T10:00:00.000Z", "2026-09-01T11:00:00.000Z"], mtime=2_000_000_000)
        transcript(self.where, "newer.jsonl",
                   ["2026-09-08T10:00:00.000Z", "2026-09-08T11:00:00.000Z"], mtime=1_000_000_000)
        done = run(self.where)
        self.assertEqual(0, done.returncode, done.stderr)
        self.assertEqual(["newer.jsonl", "older.jsonl"], table(done.stdout), done.stdout)
        self.assertIn("newest first, by the last timestamp inside each log", done.stdout)

    def test_the_last_timestamp_decides_not_the_first(self):
        # started first, still running last: it is the newest session in the directory
        transcript(self.where, "long.jsonl",
                   ["2026-09-01T09:00:00.000Z", "2026-09-09T09:00:00.000Z"], mtime=1_000_000_000)
        transcript(self.where, "short.jsonl",
                   ["2026-09-05T09:00:00.000Z", "2026-09-05T09:30:00.000Z"], mtime=2_000_000_000)
        done = run(self.where)
        self.assertEqual(["long.jsonl", "short.jsonl"], table(done.stdout), done.stdout)

    def test_a_log_with_an_unreadable_timestamp_falls_back_to_its_mtime_and_says_so(self):
        transcript(self.where, "good.jsonl",
                   ["2026-09-01T10:00:00.000Z"], mtime=1_000_000_000)
        transcript(self.where, "broken.jsonl",
                   ["not a timestamp at all"], mtime=2_000_000_000)
        done = run(self.where)
        self.assertEqual(0, done.returncode, done.stderr)
        self.assertIn("1 of 2 by file mtime instead", done.stdout)
        # the broken one keeps the newer mtime, so it still sorts first — on the fallback
        self.assertEqual(["broken.jsonl", "good.jsonl"], table(done.stdout), done.stdout)


class Echo(unittest.TestCase):
    """The echo column: characters this session's tool results put into a context.

    The count has to match the one the read-gate replication used, or the two sets of
    readings cannot be set side by side. What that count does: text parts of a tool_result
    only, one arrival per tool_use_id, subagent transcripts folded into the session that
    dispatched them, workflow journals left out.
    """

    def setUp(self):
        self.where = os.path.join(FIXTURES, self._testMethodName)
        if os.path.isdir(self.where):
            shutil.rmtree(self.where)
        os.makedirs(self.where)

    def echo_of(self, out, name):
        """The echo cell of one row, as an integer."""
        for line in out.split("\n"):
            if line.startswith(name):
                return int(line.split()[-2].replace(",", ""))
        self.fail("no row for %s in:\n%s" % (name, out))

    def bash_of(self, out, name):
        for line in out.split("\n"):
            if line.startswith(name):
                return int(line.split()[-1].rstrip("%").replace("⚠️", "").strip())
        self.fail("no row for %s in:\n%s" % (name, out))

    def test_a_subagents_echo_is_counted_into_the_session_that_dispatched_it(self):
        session(self.where, "s.jsonl", [("Bash", 1000), ("Read", 500)])
        subagent(self.where, "s", "agent-one.jsonl", [("Bash", 2500)])
        done = run(self.where)
        self.assertEqual(0, done.returncode, done.stderr)
        self.assertEqual(4000, self.echo_of(done.stdout, "s.jsonl"))
        self.assertEqual(88, self.bash_of(done.stdout, "s.jsonl"))  # 3500 of 4000
        self.assertIn("subagent transcripts included", done.stdout)

    def test_a_workflow_journal_under_subagents_is_not_counted(self):
        session(self.where, "s.jsonl", [("Read", 100)])
        subagent(self.where, "s", "journal.jsonl", [("Bash", 9999)])
        done = run(self.where)
        self.assertEqual(100, self.echo_of(done.stdout, "s.jsonl"))

    def test_the_same_tool_use_id_written_twice_arrives_once(self):
        # a resumed or forked log writes the same result again; it is one arrival in one context
        path = os.path.join(self.where, "s.jsonl")
        with io.open(path, "w", encoding="utf-8") as fh:
            fh.write(json.dumps(call("2026-09-09T10:00:00.000Z", "t1", "Read", "m1")) + "\n")
            fh.write(json.dumps(result("t1", "R" * 700)) + "\n")
            fh.write(json.dumps(result("t1", "R" * 700)) + "\n")
        done = run(self.where)
        self.assertEqual(700, self.echo_of(done.stdout, "s.jsonl"))

    def test_a_result_written_before_its_own_tool_use_is_still_named(self):
        # order is normally the other way round; a forked log can invert it, and an echo
        # charged to no tool at all would silently drop out of the bash share
        path = os.path.join(self.where, "s.jsonl")
        with io.open(path, "w", encoding="utf-8") as fh:
            fh.write(json.dumps(result("t1", "B" * 400)) + "\n")
            fh.write(json.dumps(call("2026-09-09T10:00:00.000Z", "t1", "Bash", "m1")) + "\n")
        done = run(self.where)
        self.assertEqual(400, self.echo_of(done.stdout, "s.jsonl"))
        self.assertEqual(100, self.bash_of(done.stdout, "s.jsonl"))

    def test_a_part_that_is_not_text_counts_zero_characters(self):
        path = os.path.join(self.where, "s.jsonl")
        with io.open(path, "w", encoding="utf-8") as fh:
            fh.write(json.dumps(call("2026-09-09T10:00:00.000Z", "t1", "Read", "m1")) + "\n")
            fh.write(json.dumps({
                "type": "user", "timestamp": "2026-09-09T10:00:01.000Z",
                "message": {"role": "user", "content": [{
                    "type": "tool_result", "tool_use_id": "t1",
                    "content": [{"type": "text", "text": "x" * 250},
                                {"type": "image", "source": {"data": "y" * 5000}}]}]}}) + "\n")
        done = run(self.where)
        self.assertEqual(250, self.echo_of(done.stdout, "s.jsonl"))

    def test_the_blind_spot_count_takes_the_sessions_the_per_call_gate_never_sees(self):
        # over the gate in total, never in one call: the reading the count exists for
        session(self.where, "quiet.jsonl", [("Bash", 20000), ("Bash", 20000)])
        # one call past the gate on its own: the gate saw this session, so it is not counted
        session(self.where, "loud.jsonl", [("Read", 40000)])
        done = run(self.where)
        self.assertIn("1 of 2 session(s) echo more than 30,000 characters in total", done.stdout)
        self.assertIn("a reading, no line is set on it", done.stdout)

    def test_out_writes_the_same_text_the_terminal_got(self):
        session(self.where, "s.jsonl", [("Read", 120)])
        target = os.path.join(self.where, "artifact.md")
        done = subprocess.run(
            [sys.executable, SCRIPT, "--project", self.where, "--cases", self.where,
             "--out", target, "--all", "0"],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
        self.assertEqual(0, done.returncode, done.stderr)
        written = io.open(target, encoding="utf-8").read()
        # the terminal gets one extra line saying where the file went; the rest is identical
        shown = [l for l in done.stdout.split("\n") if l and not l.startswith("# written to ")]
        self.assertEqual(shown, [l for l in written.split("\n") if l])
        self.assertIn("# written to " + target, done.stdout)

    def test_out_is_off_unless_asked_for(self):
        session(self.where, "s.jsonl", [("Read", 120)])
        done = run(self.where)
        self.assertNotIn("# written to", done.stdout)
        self.assertEqual([], [n for n in os.listdir(self.where) if n.endswith(".md")])

    def test_out_without_a_path_is_a_usage_error(self):
        done = subprocess.run(
            [sys.executable, SCRIPT, "--out"],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
        self.assertEqual(2, done.returncode)
        self.assertIn("--out needs a path", done.stderr)


if __name__ == "__main__":
    unittest.main(verbosity=2)
