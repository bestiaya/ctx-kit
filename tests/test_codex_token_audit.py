"""Small, hand-calculated accounting examples for the Codex token audit."""
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / "codex/setup/scripts/token-audit.py"
SPEC = importlib.util.spec_from_file_location("codex_token_audit", SCRIPT)
audit = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(audit)


def event(kind, payload, timestamp="2026-10-08T00:00:00Z"):
    return {"type": kind, "timestamp": timestamp, "payload": payload}


def usage(i, c, o, reasoning=0, **extra):
    return {"input_tokens": i, "cached_input_tokens": c,
            "output_tokens": o, "reasoning_output_tokens": reasoning,
            "total_tokens": i + o, **extra}


def response(identity, values, timestamp="2026-10-08T00:00:00Z"):
    return event("token_usage_record", {"response_id": identity, "usage": values}, timestamp)


def notice(total, last, timestamp="2026-10-08T00:00:00Z"):
    return event("event_msg", {"type": "token_count", "info": {
        "total_token_usage": total, "last_token_usage": last}}, timestamp)


class TokenAuditTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def file(self, name, *events):
        path = self.root / name
        path.write_text("".join(json.dumps(e) + "\n" for e in events), encoding="utf-8")
        return path

    def rollout(self, name, *events, model="gpt-6-astra", session="session-1"):
        return self.file(name, event("session_meta", {"id": session}),
                         event("turn_context", {"model": model, "effort": "xhigh"}), *events)

    def report(self, *paths, **options):
        return audit.audit_paths(paths, include_records=True, **options)

    def test_cache_read_is_part_of_input_and_reasoning_part_of_output(self):
        path = self.rollout("base.jsonl", response("r1", usage(100, 80, 20, 12)))
        result = self.report(path)
        totals = result["summary"]
        self.assertEqual(result["status"], "ok")
        self.assertEqual((totals["input_tokens"], totals["cached_input_tokens"],
                          totals["uncached_input_tokens"], totals["output_tokens"],
                          totals["reasoning_output_tokens"], totals["total_tokens"]),
                         (100, 80, 20, 20, 12, 120))
        self.assertEqual(totals["weighted_tokens"], "128.0")  # 20 + 8 + 100

    def test_duplicate_response_across_files_is_counted_once(self):
        first = self.rollout("first.jsonl", response("same", usage(100, 50, 10)))
        second = self.rollout("second.jsonl", response("same", usage(100, 50, 10)))
        result = self.report(first, second)
        self.assertEqual(result["summary"]["records"], 1)
        self.assertEqual(result["summary"]["total_tokens"], 110)
        self.assertEqual(result["duplicate_response_records"], 1)
        self.assertEqual(len(result["records"][0]["duplicate_sources"]), 1)

    def test_conflicting_same_id_is_excluded_and_report_is_partial(self):
        first = self.rollout("first.jsonl", response("same", usage(100, 50, 10)))
        second = self.rollout("second.jsonl", response("same", usage(101, 50, 10)))
        result = self.report(first, second)
        self.assertEqual(result["status"], "partial")
        self.assertEqual(result["summary"]["records"], 0)
        self.assertIn("response_conflict", {i["code"] for i in result["issues"]})

    def test_identical_usage_with_distinct_response_ids_counts_twice(self):
        path = self.rollout("distinct.jsonl", response("r1", usage(20, 10, 5)),
                            response("r2", usage(20, 10, 5)))
        totals = self.report(path)["summary"]
        self.assertEqual((totals["records"], totals["input_tokens"],
                          totals["output_tokens"], totals["weighted_tokens"]),
                         (2, 40, 10, "72.0"))  # 2 * (10 + 1 + 25)

    def test_overlapping_files_check_their_own_cumulative_before_global_dedup(self):
        a, b, total = usage(10, 5, 2), usage(20, 10, 4), usage(30, 15, 6)
        first = event("token_usage_record", {"response_id": "a", "usage": a, "thread_token_usage": a})
        second = event("token_usage_record", {"response_id": "b", "usage": b, "thread_token_usage": total})
        one = self.rollout("short.jsonl", first)
        two = self.rollout("extended.jsonl", first, second)
        result = self.report(one, two)
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["summary"]["total_tokens"], 36)
        self.assertEqual([f["cumulative_check"]["status"] for f in result["source_files"]], ["matched", "matched"])

    def test_missing_cache_count_remains_unknown_not_zero(self):
        path = self.rollout("missing-cache.jsonl", response("a", {"input_tokens": 100, "output_tokens": 10}))
        totals = self.report(path)["summary"]
        self.assertEqual(totals["total_tokens"], 110)
        self.assertIsNone(totals["cached_input_tokens"])
        self.assertIsNone(totals["weighted_tokens"])

    def test_explicit_response_mode_does_not_silently_accept_legacy_only(self):
        values = usage(10, 2, 1)
        path = self.rollout("legacy-only.jsonl", notice(values, values))
        result = self.report(path, source_mode="responses")
        self.assertEqual(result["status"], "partial")
        self.assertIn("missing_response_records", {x["code"] for x in result["issues"]})

    def test_token_count_notification_does_not_add_to_response_total(self):
        values = usage(30, 20, 4)
        path = self.rollout("notice.jsonl", response("r1", values),
                            notice(values, values), notice(values, values))
        result = self.report(path)
        self.assertEqual(result["summary"]["records"], 1)
        self.assertEqual(result["summary"]["total_tokens"], 34)
        self.assertEqual(result["source_files"][0]["repeated_token_count_notifications"],
                         {"3": [4, 5]})

    def test_response_after_compaction_remains_counted_without_notice(self):
        path = self.rollout("compact.jsonl", response("r1", usage(10, 0, 2)),
                            event("compacted", {}), response("r2", usage(30, 20, 3)))
        result = self.report(path)
        self.assertEqual((result["summary"]["records"], result["summary"]["total_tokens"]), (2, 45))
        self.assertEqual(result["source_files"][0]["compaction_lines"], [4])

    def test_legacy_repeated_cumulative_notice_only_counts_change(self):
        a, b = usage(10, 2, 3), usage(17, 5, 7)
        path = self.rollout("legacy.jsonl", notice(a, a), notice(a, a),
                            notice(b, usage(7, 3, 4)))
        result = self.report(path)
        totals = result["summary"]
        self.assertEqual((totals["records"], totals["input_tokens"],
                          totals["cached_input_tokens"], totals["output_tokens"]),
                         (2, 17, 5, 7))
        self.assertEqual(totals["legacy_delta_records"], 2)

    def test_legacy_reset_starts_new_segment_from_last_usage(self):
        first, reset_last = usage(20, 4, 5), usage(3, 1, 2)
        path = self.rollout("reset.jsonl", notice(first, first),
                            notice(usage(7, 2, 4), reset_last))
        result = self.report(path)
        self.assertEqual(result["status"], "ok")
        self.assertEqual((result["summary"]["input_tokens"],
                          result["summary"]["output_tokens"]), (23, 7))
        self.assertIn("legacy_counter_reset", {i["code"] for i in result["issues"]})

    def test_since_is_inclusive_until_exclusive(self):
        path = self.rollout("times.jsonl",
                            response("before", usage(1, 0, 1), "2026-10-07T23:59:59Z"),
                            response("start", usage(2, 0, 1), "2026-10-08T00:00:00Z"),
                            response("middle", usage(3, 0, 1), "2026-10-08T00:59:59Z"),
                            response("end", usage(4, 0, 1), "2026-10-08T01:00:00Z"))
        result = self.report(path, since="2026-10-08T00:00:00Z", until="2026-10-08T01:00:00Z")
        self.assertEqual([r["response_id"] for r in result["records"]], ["start", "middle"])
        self.assertEqual(result["summary"]["input_tokens"], 5)

    def test_mixed_models_preserve_raw_totals_without_combined_weight(self):
        astra = self.rollout("astra.jsonl", response("a", usage(10, 5, 2)))
        other = self.rollout("other.jsonl", response("b", usage(20, 10, 4)), model="gpt-6-luna")
        result = self.report(astra, other)
        self.assertEqual(result["summary"]["total_tokens"], 36)
        self.assertIsNone(result["summary"]["weighted_tokens"])
        self.assertEqual(result["summary"]["weighted_covered_records"], 1)
        self.assertEqual({m["model"]: m["weighted_tokens"] for m in result["by_model"]},
                         {"gpt-6-astra": "15.5", "gpt-6-luna": None})
        filtered = self.report(astra, other, models=["gpt-6-luna"])
        self.assertEqual((filtered["summary"]["records"], filtered["summary"]["total_tokens"]), (1, 24))

    def test_invalid_usage_and_bad_json_are_reported_without_inventing_totals(self):
        path = self.rollout("bad.jsonl", response("good", usage(10, 5, 2)),
                            response("negative", usage(-1, 0, 2)),
                            response("missing", {"input_tokens": 5}),
                            response("bad-total", {**usage(5, 0, 2), "total_tokens": 99}))
        with path.open("a", encoding="utf-8") as handle:
            handle.write('{"type":')
        result = self.report(path)
        self.assertEqual(result["status"], "partial")
        self.assertEqual(result["summary"]["total_tokens"], 12)
        self.assertEqual([i["code"] for i in result["issues"]].count("invalid_record"), 3)
        self.assertIn("invalid_json_line", {i["code"] for i in result["issues"]})

    def test_custom_fixed_profile_changes_only_eligible_weight(self):
        path = self.rollout("custom.jsonl", response("r1", usage(100, 80, 20)))
        profile = {"id": "test-weights", "models": ["gpt-6-astra"],
                   "weights": {"uncached_input": "2", "cached_input": "0.25", "output": "3"}}
        result = self.report(path, profile=profile)
        self.assertEqual(result["summary"]["weighted_tokens"], "120.00")  # 40 + 20 + 60
        self.assertEqual(result["summary"]["total_tokens"], 120)
        self.assertEqual(result["profile"]["money_conversion"], False)

    def test_cli_json_records_and_filters(self):
        path = self.rollout("cli.jsonl", response("r1", usage(10, 5, 2)),
                            response("r2", usage(20, 10, 4), "2026-10-09T00:00:00Z"))
        completed = subprocess.run([sys.executable, str(SCRIPT), "--json", "--records",
                                    "--model", "gpt-6-astra", "--since", "2026-10-08",
                                    "--until", "2026-10-09", str(path)],
                                   capture_output=True, text=True, check=False)
        self.assertEqual(completed.returncode, 0, completed.stderr)
        result = json.loads(completed.stdout)
        self.assertEqual([r["response_id"] for r in result["records"]], ["r1"])
        self.assertEqual(result["summary"]["total_tokens"], 12)


if __name__ == "__main__":
    unittest.main()
