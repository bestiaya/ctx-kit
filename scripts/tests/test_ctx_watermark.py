#!/usr/bin/env python3
"""test_ctx_watermark.py — unit tests for scripts/ctx-watermark.py, the watermark doorbell.

Every test runs the script as a real subprocess and reads real stdin, stdout and exit codes.
Nothing is imported from it: the hook contract is "what claude CLI puts in and gets back out",
so that is what gets tested, not the shape of the functions inside.

The transcripts here are synthetic — a handful of made-up records with made-up numbers, written
under /tmp. No real session log is read or copied, and the script itself never touches
conversation text either way.

Run:
    python3 -m unittest discover -s scripts/tests
    python3 scripts/tests/test_ctx_watermark.py
Use a working python3 — on macOS /usr/bin/python3 is an Xcode shim that cannot even import json.
"""
import json, os, subprocess, sys, time, unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(os.path.dirname(HERE), "ctx-watermark.py")
FIXTURES = os.environ.get("CTXKIT_TEST_DIR") or "/tmp/ctx-watermark-tests"
PREFIX = "[ctx-kit watermark]"

# The defaults the script falls back to, restated here so a silent change to either one shows up
# as a failing test rather than as a doorbell that rings at a line nobody chose.
YELLOW_DEFAULT, RED_DEFAULT = 300000, 400000

# Three synthetic readings, picked to sit in each band under the default lines.
OVER_RED = (12000, 390000, 11000)       # 413000
IN_YELLOW = (10000, 300000, 8000)       # 318000
UNDER_BOTH = (40000, 20000, 3000)       # 63000


def setUpModule():
    os.makedirs(FIXTURES, exist_ok=True)


def assistant(numbers, sidechain=False, mid="msg_synthetic"):
    """A synthetic main-thread (or sidechain) assistant record, shaped like a transcript line.

    output_tokens is deliberately non-zero: the watermark is the other three added up, and a
    reading that includes this number is wrong.
    """
    given, read, created = numbers
    return {
        "type": "assistant",
        "isSidechain": sidechain,
        "timestamp": "2026-09-05T00:00:00.000Z",
        "message": {
            "id": mid,
            "role": "assistant",
            "usage": {
                "input_tokens": given,
                "cache_read_input_tokens": read,
                "cache_creation_input_tokens": created,
                "output_tokens": 4321,
                "service_tier": "standard",
            },
        },
    }


def write_transcript(name, records, tail=""):
    """Write one synthetic jsonl fixture, optionally with a half-written line stuck on the end."""
    path = os.path.join(FIXTURES, name)
    with open(path, "w") as handle:
        for record in records:
            handle.write(json.dumps(record) + "\n")
        handle.write(tail)
    return path


def run(path, **thresholds):
    """Run the hook the way claude CLI does: the event JSON on stdin, nothing else."""
    env = dict(os.environ)
    env.pop("CTXKIT_WATERMARK_YELLOW", None)  # never inherit the developer's own lines
    env.pop("CTXKIT_WATERMARK_RED", None)
    env.update(thresholds)
    event = json.dumps({
        "session_id": "synthetic-session",
        "transcript_path": path,
        "cwd": FIXTURES,
        "hook_event_name": "UserPromptSubmit",
        "prompt": "synthetic prompt",
    })
    return subprocess.run(
        [sys.executable, SCRIPT], input=event, env=env,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True,
    )


def run_raw(stdin_text):
    """Run the hook with whatever is handed to it on stdin, valid JSON or not."""
    env = dict(os.environ)
    env.pop("CTXKIT_WATERMARK_YELLOW", None)
    env.pop("CTXKIT_WATERMARK_RED", None)
    return subprocess.run(
        [sys.executable, SCRIPT], input=stdin_text, env=env,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True,
    )


class Ringing(unittest.TestCase):
    """Over the line: one line of JSON, both channels carrying the same reading."""

    def assert_rings(self, result, numbers, band, line):
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual(1, len(result.stdout.splitlines()), repr(result.stdout))
        payload = json.loads(result.stdout)
        self.assertIsInstance(payload, dict)

        message = payload["systemMessage"]
        specific = payload["hookSpecificOutput"]
        context = specific["additionalContext"]
        self.assertEqual("UserPromptSubmit", specific["hookEventName"])
        self.assertTrue(message.startswith(PREFIX), message)
        self.assertIn(PREFIX, context)

        # The reading is the three usage numbers added up — and nothing else. output_tokens is
        # 4321 in every fixture, so a sum that included it would land on a different thousand.
        expected = "%dk" % round(sum(numbers) / 1000.0)
        self.assertIn(expected, message)
        self.assertIn("%s %dk" % (band, round(line / 1000.0)), message)
        # The model is told the same thing the owner is told, plus what to do about it.
        self.assertIn(message, context)
        self.assertIn("/ctx-handoff", context)
        return payload

    def test_over_the_red_line_rings_red(self):
        path = write_transcript("over-red.ndjson", [
            {"type": "user", "message": {"role": "user", "content": "synthetic prompt"}},
            assistant(UNDER_BOTH, mid="msg_older"),
            assistant(OVER_RED, mid="msg_newest"),
        ])
        payload = self.assert_rings(run(path), OVER_RED, "red", RED_DEFAULT)
        self.assertIn("413k", payload["systemMessage"])  # the newest record, not the older one

    def test_between_the_lines_rings_yellow(self):
        path = write_transcript("yellow.ndjson", [assistant(IN_YELLOW)])
        self.assert_rings(run(path), IN_YELLOW, "yellow", YELLOW_DEFAULT)

    def test_under_the_line_prints_nothing(self):
        path = write_transcript("under.ndjson", [assistant(UNDER_BOTH)])
        result = run(path)
        self.assertEqual("", result.stdout)  # zero bytes, not an empty line
        self.assertEqual(0, result.returncode, result.stderr)

    def test_a_half_written_tail_does_not_hide_the_last_full_record(self):
        # The transcript is written asynchronously, so the last line can be half there.
        path = write_transcript(
            "torn-tail.ndjson", [assistant(OVER_RED)], tail='{"type":"assistant","mess'
        )
        self.assert_rings(run(path), OVER_RED, "red", RED_DEFAULT)


class Silence(unittest.TestCase):
    """Nothing to report, or nothing to read: zero bytes, exit 0, no stack trace."""

    def assert_silent(self, result):
        self.assertEqual("", result.stdout)
        self.assertEqual(0, result.returncode)
        self.assertNotIn("Traceback", result.stderr)
        self.assertEqual("", result.stderr.strip())

    def test_bad_material_is_survived_silently(self):
        cases = {
            "empty file": write_transcript("empty.ndjson", []),
            "half a line and nothing else": write_transcript(
                "truncated.ndjson", [], tail='{"type":"assistant","message":{"usa'
            ),
            "assistant records with no usage": write_transcript("no-usage.ndjson", [
                {"type": "assistant", "isSidechain": False,
                 "message": {"id": "msg_x", "role": "assistant"}},
                {"type": "assistant", "isSidechain": False,
                 "message": {"id": "msg_y", "role": "assistant", "usage": {"output_tokens": 12}}},
            ]),
            "path that is not there": os.path.join(FIXTURES, "no-such-transcript.ndjson"),
        }
        for label, path in cases.items():
            with self.subTest(material=label):
                self.assert_silent(run(path))

    def test_junk_on_stdin_is_survived_silently(self):
        for label, text in {
            "not json": "this is not json",
            "json but not an object": "[1, 2, 3]",
            "object with no transcript_path": '{"session_id": "s"}',
            "empty stdin": "",
        }.items():
            with self.subTest(stdin=label):
                self.assert_silent(run_raw(text))


class MainThreadOnly(unittest.TestCase):
    """A subagent's bill is not this session's watermark."""

    def test_a_bigger_sidechain_record_at_the_tail_is_ignored(self):
        path = write_transcript("sidechain.ndjson", [
            assistant(OVER_RED, mid="msg_main"),
            assistant((900000, 900000, 900000), sidechain=True, mid="msg_sub_a"),
            assistant((800000, 800000, 800000), sidechain=True, mid="msg_sub_b"),
        ])
        result = run(path)
        message = json.loads(result.stdout)["systemMessage"]
        self.assertIn("413k", message)
        self.assertNotIn("2700k", message)

    def test_only_sidechain_records_means_no_reading(self):
        path = write_transcript("sidechain-only.ndjson", [
            assistant(OVER_RED, sidechain=True, mid="msg_sub_only"),
        ])
        self.assertEqual("", run(path).stdout)


class Thresholds(unittest.TestCase):
    """The lines move with the environment, and never crash on a typo."""

    def setUp(self):
        self.path = write_transcript("thresholds.ndjson", [assistant(IN_YELLOW)])  # 318000

    def test_lowering_red_to_30k_changes_the_band(self):
        result = run(self.path, CTXKIT_WATERMARK_RED="30k")
        message = json.loads(result.stdout)["systemMessage"]
        self.assertIn("318k / red 30k", message)
        self.assertEqual(0, result.returncode)

    def test_both_spellings_are_accepted(self):
        for spelling in ("30000", "30k", "30K", " 30k "):
            with self.subTest(spelling=spelling):
                result = run(self.path, CTXKIT_WATERMARK_RED=spelling)
                self.assertIn("red 30k", json.loads(result.stdout)["systemMessage"])

    def test_raising_the_lines_silences_the_bell(self):
        result = run(self.path, CTXKIT_WATERMARK_YELLOW="1000k", CTXKIT_WATERMARK_RED="2000k")
        self.assertEqual("", result.stdout)
        self.assertEqual(0, result.returncode)

    def test_junk_thresholds_fall_back_to_the_defaults(self):
        for junk in ("abc", "", "-5", "0", "300k000", "k"):
            with self.subTest(value=junk):
                result = run(self.path, CTXKIT_WATERMARK_YELLOW=junk, CTXKIT_WATERMARK_RED=junk)
                self.assertEqual(0, result.returncode, result.stderr)
                self.assertNotIn("Traceback", result.stderr)
                # 318000 is yellow under the defaults, so falling back is visible in the band.
                message = json.loads(result.stdout)["systemMessage"]
                self.assertIn("318k / yellow 300k", message)

    def test_the_shipped_default_lines_are_300k_and_400k(self):
        """Where the bell rings when nothing is configured — the defaults, checked from outside.

        Every other test here moves the lines or reads a fixture chosen to sit in a band; this one
        pins the two numbers the kit ships with, so raising or lowering a default cannot pass
        silently. Both boundaries are checked on the token, and 399,999 is in on purpose: it
        rounds to "400k" in the printed reading while still being a yellow-band watermark, so a
        band picked off the rounded number instead of the raw one fails here.
        """
        for numbers, expected in (
            ((1000, 297999, 1000), ""),                    # 299,999 — one token under yellow
            ((1000, 298000, 1000), "300k / yellow 300k"),  # 300,000 — exactly on yellow
            ((1000, 397999, 1000), "400k / yellow 300k"),  # 399,999 — one token under red
            ((1000, 398000, 1000), "400k / red 400k"),     # 400,000 — exactly on red
        ):
            with self.subTest(watermark=sum(numbers)):
                path = write_transcript("default-%d.ndjson" % sum(numbers), [assistant(numbers)])
                result = run(path)
                self.assertEqual(0, result.returncode, result.stderr)
                if expected:
                    self.assertIn(expected, json.loads(result.stdout)["systemMessage"])
                else:
                    self.assertEqual("", result.stdout)

    def test_a_junk_threshold_still_leaves_a_quiet_session_quiet(self):
        quiet = write_transcript("quiet.ndjson", [assistant(UNDER_BOTH)])
        result = run(quiet, CTXKIT_WATERMARK_YELLOW="abc", CTXKIT_WATERMARK_RED="abc")
        self.assertEqual("", result.stdout)
        self.assertEqual(0, result.returncode)


class TailRead(unittest.TestCase):
    """The doorbell fires every turn on logs that reach tens of MB. It has to read the tail."""

    # The reading is part of the name on purpose: these fixtures are expensive and are kept
    # between runs, and the reuse check below only looks at the size. Without the number in the
    # name, a fixture built under an earlier pair of default lines would be reused after those
    # lines moved, and the suite would fail on a stale /tmp rather than on the code.
    BIG = os.path.join(FIXTURES, "big-30mb-%d.ndjson" % sum(OVER_RED))
    TARGET_BYTES = 30 * 1024 * 1024

    @classmethod
    def setUpClass(cls):
        if os.path.exists(cls.BIG) and os.path.getsize(cls.BIG) >= cls.TARGET_BYTES:
            return
        # Filler records are real-looking main-thread records that sit under both lines, so a
        # script that read the head instead of the tail would print nothing and fail this test.
        filler = assistant((1000, 2000, 3000), mid="msg_filler")
        filler["padding"] = "x" * 900
        block = (json.dumps(filler) + "\n") * 256
        with open(cls.BIG, "w") as handle:
            written = 0
            while written < cls.TARGET_BYTES:
                handle.write(block)
                written += len(block)
            handle.write(json.dumps(assistant(OVER_RED, mid="msg_last")) + "\n")

    @staticmethod
    def padded(name, head, trailing_bytes):
        """A fixture whose only countable record sits `trailing_bytes` back from the end.

        The padding is made of records the doorbell must not count — sidechain assistant
        records with enormous numbers, and user records — so a run that read the padding
        instead of the head would give a loud, obviously wrong answer.
        """
        path = os.path.join(FIXTURES, name)
        if os.path.exists(path) and os.path.getsize(path) >= trailing_bytes:
            return path
        noise = assistant((999000, 999000, 999000), sidechain=True, mid="msg_noise")
        noise["padding"] = "x" * 900
        block = (json.dumps(noise) + "\n") * 64
        with open(path, "w") as handle:
            handle.write(json.dumps(head) + "\n")
            written = 0
            while written < trailing_bytes:
                handle.write(block)
                written += len(block)
        return path

    def test_a_record_beyond_the_first_windows_is_still_found(self):
        # 600KB of tail noise: past the 64KB and 256KB windows, so the widening has to work,
        # and the second window must not re-parse or skip the lines the first one saw.
        path = self.padded("beyond-window-%d.ndjson" % sum(OVER_RED),
                           assistant(OVER_RED, mid="msg_buried"), 600 * 1024)
        result = run(path)
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertIn("413k", json.loads(result.stdout)["systemMessage"])

    def test_a_record_past_the_8mb_cap_is_left_alone(self):
        # The cap is deliberate: past 8MB of tail the answer is "no reading", not "read the
        # whole file". Silence, not a wrong number and not a slow turn.
        path = self.padded("past-cap-%d.ndjson" % sum(OVER_RED),
                           assistant(OVER_RED, mid="msg_too_far"), 9 * 1024 * 1024)
        started = time.perf_counter()
        result = run(path)
        elapsed = time.perf_counter() - started
        self.assertEqual("", result.stdout)
        self.assertEqual(0, result.returncode)
        self.assertLess(elapsed, 1.0, "took %.3fs" % elapsed)

    def test_a_30mb_transcript_is_read_in_under_a_second(self):
        self.assertGreaterEqual(os.path.getsize(self.BIG), self.TARGET_BYTES)
        started = time.perf_counter()
        result = run(self.BIG)
        elapsed = time.perf_counter() - started
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertIn("413k", json.loads(result.stdout)["systemMessage"])
        self.assertLess(elapsed, 1.0, "took %.3fs on a %.1fMB transcript" % (
            elapsed, os.path.getsize(self.BIG) / 1048576.0))
        print("\n  30MB transcript, one run end to end: %.3fs" % elapsed)


if __name__ == "__main__":
    unittest.main(verbosity=2)
