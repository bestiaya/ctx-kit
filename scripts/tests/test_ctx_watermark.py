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
import ast, datetime, glob, json, os, re, shutil, subprocess, sys, time, unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(os.path.dirname(HERE), "ctx-watermark.py")
# The rest of the kit this file also holds to account: the sync script names which files an
# install is made of, and the two hook files carry the same install-root chain in `sh`.
REPO = os.path.dirname(os.path.dirname(HERE))
SYNC = os.path.join(REPO, "scripts", "sync-installed.sh")
HOOKS = os.path.join(REPO, "hooks", "hooks.json")
CANDIDATE_HOOK = os.path.join(REPO, "hooks", "case-lint.PostToolUse.candidate.json")
FIXTURES = os.environ.get("CTXKIT_TEST_DIR") or "/tmp/ctx-watermark-tests"
PREFIX = "[ctx-kit watermark]"
UPDATE_PREFIX = "[ctx-kit update]"

# When every fixture session in here opened, as the log spells it and as a number of seconds.
# The installed copies built below are stamped either side of this moment.
SESSION_START = "2026-09-05T00:00:00.000Z"
SESSION_STARTED = datetime.datetime.fromisoformat("2026-09-05T00:00:00+00:00").timestamp()
HOUR = 3600

# The defaults the script falls back to, restated here so a silent change to either one shows up
# as a failing test rather than as a doorbell that rings at a line nobody chose.
YELLOW_DEFAULT, RED_DEFAULT = 400000, 500000

# Three synthetic readings, picked to sit in each band under the default lines.
OVER_RED = (12000, 490000, 11000)       # 513000
IN_YELLOW = (10000, 400000, 8000)       # 418000
UNDER_BOTH = (40000, 20000, 3000)       # 63000


# An install root with nothing ctx-kit-shaped underneath it. Pointing CLAUDE_PLUGIN_ROOT here
# is what keeps every test below about the one thing it is about: with no installed files to
# stat, the "this session predates the installed files" reading has nothing to say, and a run
# under the line stays silent. The tests that are about that reading point it somewhere else.
NO_INSTALL = os.path.join(FIXTURES, "no-install")


def setUpModule():
    os.makedirs(FIXTURES, exist_ok=True)
    os.makedirs(NO_INSTALL, exist_ok=True)


def assistant(numbers, sidechain=False, mid="msg_synthetic"):
    """A synthetic main-thread (or sidechain) assistant record, shaped like a transcript line.

    output_tokens is deliberately non-zero: the watermark is the other three added up, and a
    reading that includes this number is wrong.
    """
    given, read, created = numbers
    return {
        "type": "assistant",
        "isSidechain": sidechain,
        "timestamp": SESSION_START,
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


def installed(name, written_at):
    """A directory shaped like an installed ctx-kit, every file stamped `written_at`.

    Two files, one of each shape the script looks for, so a run that found only one of the
    two globs would still be reading a real mtime and the test would go on passing. The
    bodies are never read — only the mtimes are — so one word in each is enough.
    """
    root = os.path.join(FIXTURES, name)
    for parts in (("skills", "ctx-status", "SKILL.md"), ("scripts", "ctx-watermark.py")):
        path = os.path.join(root, *parts)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as handle:
            handle.write("synthetic\n")
        os.utime(path, (written_at, written_at))
    return root


def run(path, **thresholds):
    """Run the hook the way claude CLI does: the event JSON on stdin, nothing else."""
    env = dict(os.environ)
    env.pop("CTXKIT_WATERMARK_YELLOW", None)  # never inherit the developer's own lines
    env.pop("CTXKIT_WATERMARK_RED", None)
    env["CLAUDE_PLUGIN_ROOT"] = NO_INSTALL  # nor the developer's own installed copy
    env.pop("CLAUDE_CONFIG_DIR", None)      # nor a config dir they moved off the default path
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
    env["CLAUDE_PLUGIN_ROOT"] = NO_INSTALL
    env.pop("CLAUDE_CONFIG_DIR", None)
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
        self.assertIn("513k", payload["systemMessage"])  # the newest record, not the older one

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
        self.assertIn("513k", message)
        self.assertNotIn("2700k", message)

    def test_only_sidechain_records_means_no_reading(self):
        path = write_transcript("sidechain-only.ndjson", [
            assistant(OVER_RED, sidechain=True, mid="msg_sub_only"),
        ])
        self.assertEqual("", run(path).stdout)


class Thresholds(unittest.TestCase):
    """The lines move with the environment, and never crash on a typo."""

    def setUp(self):
        self.path = write_transcript("thresholds.ndjson", [assistant(IN_YELLOW)])  # 418000

    def test_lowering_red_to_30k_changes_the_band(self):
        result = run(self.path, CTXKIT_WATERMARK_RED="30k")
        message = json.loads(result.stdout)["systemMessage"]
        self.assertIn("418k / red 30k", message)
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
                # 418000 is yellow under the defaults, so falling back is visible in the band.
                message = json.loads(result.stdout)["systemMessage"]
                self.assertIn("418k / yellow 400k", message)

    def test_the_shipped_default_lines_are_400k_and_500k(self):
        """Where the bell rings when nothing is configured — the defaults, checked from outside.

        Every other test here moves the lines or reads a fixture chosen to sit in a band; this one
        pins the two numbers the kit ships with, so raising or lowering a default cannot pass
        silently. Both boundaries are checked on the token, and 499,999 is in on purpose: it
        rounds to "500k" in the printed reading while still being a yellow-band watermark, so a
        band picked off the rounded number instead of the raw one fails here.
        """
        for numbers, expected in (
            ((1000, 397999, 1000), ""),                    # 399,999 — one token under yellow
            ((1000, 398000, 1000), "400k / yellow 400k"),  # 400,000 — exactly on yellow
            ((1000, 497999, 1000), "500k / yellow 400k"),  # 499,999 — one token under red
            ((1000, 498000, 1000), "500k / red 500k"),     # 500,000 — exactly on red
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


class BandMemory(unittest.TestCase):
    """What happens after the reading drops back — a compact, say — and climbs again.

    The doorbell keeps nothing between turns: every run reads the newest record and decides
    from that alone. So it goes quiet the moment the reading falls under the line, and it rings
    again the moment the reading is back over one, band already reported or not. "Once per
    band" is not enforced here at all: it is an instruction to the session, which checks it
    against its own earlier replies, and the band is named inside that instruction so the
    question it asks — "have I already said yellow?" — has an answer in the visible thread.
    """

    def test_a_reading_that_drops_back_under_the_line_prints_nothing(self):
        # over red, then a compact: the newest record is what counts, so the bell stops
        path = write_transcript("dropped.ndjson", [
            assistant(OVER_RED, mid="msg_before_compact"),
            assistant(UNDER_BOTH, mid="msg_after_compact"),
        ])
        result = run(path)
        self.assertEqual("", result.stdout)
        self.assertEqual(0, result.returncode, result.stderr)

    def test_climbing_back_into_a_band_rings_the_bell_again(self):
        """The hook has no memory of the earlier crossing, and does not pretend to."""
        path = write_transcript("climbed-back.ndjson", [
            assistant(IN_YELLOW, mid="msg_first_crossing"),
            assistant(UNDER_BOTH, mid="msg_after_compact"),
            assistant(IN_YELLOW, mid="msg_second_crossing"),
        ])
        first = json.loads(run(path).stdout)["systemMessage"]
        self.assertIn("418k / yellow 400k", first)
        # and the same transcript read twice gives the same line: nothing is carried over
        self.assertEqual(first, json.loads(run(path).stdout)["systemMessage"])

    def test_the_instruction_names_the_band_it_is_about(self):
        """Suppression is the session's to do, so the sentence has to be checkable by it."""
        for numbers, band in ((IN_YELLOW, "yellow"), (OVER_RED, "red")):
            with self.subTest(band=band):
                path = write_transcript("band-%s.ndjson" % band, [assistant(numbers)])
                context = json.loads(run(path).stdout)["hookSpecificOutput"]["additionalContext"]
                self.assertIn("already passed a %s reading" % band, context)
                self.assertIn("until the band changes", context)
                self.assertIn("Never act unasked", context)


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
        self.assertIn("513k", json.loads(result.stdout)["systemMessage"])

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
        self.assertIn("513k", json.loads(result.stdout)["systemMessage"])
        self.assertLess(elapsed, 1.0, "took %.3fs on a %.1fMB transcript" % (
            elapsed, os.path.getsize(self.BIG) / 1048576.0))
        print("\n  30MB transcript, one run end to end: %.3fs" % elapsed)


def clock(stamp):
    """The script's own way of printing a moment, restated so the two can be compared."""
    return datetime.datetime.fromtimestamp(stamp).strftime("%Y-%m-%d %H:%M")


class StaleInstall(unittest.TestCase):
    """A session that opened before the ctx-kit files it is running were last written.

    This reading is not about spending, so it is not about a band either: it rides on whatever
    the watermark happens to be, a watermark under both lines included. Two moments are
    compared — the first timestamp in this session's log, and the newest mtime under the
    install root — and something is said only when the second one is later. Every case below
    fixes both moments, so nothing here depends on when the suite is run.
    """

    def quiet_log(self, name):
        """A transcript under both lines, so the only thing that can print is this reading."""
        return write_transcript(name, [assistant(UNDER_BOTH)])

    def test_an_install_written_after_the_session_opened_is_reported(self):
        path = self.quiet_log("stale-newer.ndjson")
        root = installed("install-newer", SESSION_STARTED + HOUR)
        result = run(path, CLAUDE_PLUGIN_ROOT=root)
        self.assertEqual(0, result.returncode, result.stderr)
        message = json.loads(result.stdout)["systemMessage"]
        self.assertTrue(message.startswith(UPDATE_PREFIX), message)
        # Its own mark, not the watermark's: the docs define the watermark as the reading on
        # the line starting `[ctx-kit watermark]`, and this line is not a watermark.
        self.assertNotIn(PREFIX, message)
        # Both moments are in it, so the owner can see how far back the session opened.
        self.assertIn(clock(SESSION_STARTED), message)
        self.assertIn(clock(SESSION_STARTED + HOUR), message)

    def test_an_install_no_newer_than_the_session_says_nothing(self):
        for label, written_at in (
            ("written an hour before the session opened", SESSION_STARTED - HOUR),
            ("written in the same second", SESSION_STARTED),
        ):
            with self.subTest(install=label):
                path = self.quiet_log("stale-older.ndjson")
                root = installed("install-older", written_at)
                result = run(path, CLAUDE_PLUGIN_ROOT=root)
                self.assertEqual("", result.stdout)
                self.assertEqual(0, result.returncode, result.stderr)

    def test_nothing_installed_to_compare_against_says_nothing(self):
        """An empty root — somebody who keeps the kit somewhere else entirely gets silence."""
        result = run(self.quiet_log("stale-no-install.ndjson"))  # CLAUDE_PLUGIN_ROOT=NO_INSTALL
        self.assertEqual("", result.stdout)
        self.assertEqual(0, result.returncode, result.stderr)

    def test_a_log_with_no_timestamp_to_read_says_nothing(self):
        """One moment missing is no comparison, and no comparison is silence, not a guess."""
        record = assistant(UNDER_BOTH)
        del record["timestamp"]
        path = write_transcript("stale-no-timestamp.ndjson", [record])
        root = installed("install-newer", SESSION_STARTED + HOUR)
        result = run(path, CLAUDE_PLUGIN_ROOT=root)
        self.assertEqual("", result.stdout)
        self.assertEqual(0, result.returncode, result.stderr)

    def test_the_instruction_is_once_per_session_not_once_per_band(self):
        """The fact does not change while the session lives, so neither does the suppression.

        Same shape as the watermark instruction — the session checks its own earlier replies —
        but the thing being checked is "have I said this at all", not "have I said this band".
        """
        path = self.quiet_log("stale-once.ndjson")
        root = installed("install-newer", SESSION_STARTED + HOUR)
        context = json.loads(run(path, CLAUDE_PLUGIN_ROOT=root).stdout)
        context = context["hookSpecificOutput"]["additionalContext"]
        self.assertIn("once per session", context)
        self.assertIn("look back over your own earlier replies", context)
        self.assertNotIn("band", context)
        # A fact to pass on, not something to act on.
        self.assertIn("do not reinstall anything", context)

    def test_the_switch_turns_the_reading_off(self):
        """`CTXKIT_UPDATE_HINT=off` and there is nothing to say, however stale the session.

        The watermark lines need no such switch — they can be moved instead — but this
        comparison holds for the whole life of a session that opened before the last install,
        and the hook re-prints on every turn, so without a switch there is no way out of it.
        """
        path = self.quiet_log("stale-switched-off.ndjson")
        root = installed("install-newer", SESSION_STARTED + HOUR)
        for word in ("off", "0", "no", "false"):
            with self.subTest(setting=word):
                result = run(path, CLAUDE_PLUGIN_ROOT=root, CTXKIT_UPDATE_HINT=word)
                self.assertEqual("", result.stdout)
                self.assertEqual(0, result.returncode, result.stderr)
        # Anything else is not an off word, and the reading comes back.
        result = run(path, CLAUDE_PLUGIN_ROOT=root, CTXKIT_UPDATE_HINT="on")
        self.assertTrue(json.loads(result.stdout)["systemMessage"].startswith(UPDATE_PREFIX))

    def test_somebody_elses_script_in_that_directory_is_not_an_update(self):
        """The scripts are named one by one, so a stray .py next to them moves nothing.

        `~/.claude/scripts/` is the owner's directory, not the kit's. Globbing `*.py` there
        read every script anybody keeps in it as a ctx-kit file, and editing one of those
        would have told every older session that ctx-kit had been updated.
        """
        root = installed("install-with-a-stray", SESSION_STARTED - HOUR)
        stray = os.path.join(root, "scripts", "my-own-helper.py")
        with open(stray, "w") as handle:
            handle.write("synthetic\n")
        os.utime(stray, (SESSION_STARTED + HOUR, SESSION_STARTED + HOUR))
        result = run(self.quiet_log("stale-stray.ndjson"), CLAUDE_PLUGIN_ROOT=root)
        self.assertEqual("", result.stdout)
        self.assertEqual(0, result.returncode, result.stderr)

    def test_it_rides_along_with_the_bell_as_a_second_line(self):
        path = write_transcript("stale-and-ringing.ndjson", [assistant(OVER_RED)])
        root = installed("install-newer", SESSION_STARTED + HOUR)
        payload = json.loads(run(path, CLAUDE_PLUGIN_ROOT=root).stdout)
        lines = payload["systemMessage"].splitlines()
        self.assertEqual(2, len(lines), lines)
        self.assertTrue(lines[0].startswith(PREFIX), lines[0])
        self.assertIn("513k / red 500k", lines[0])
        self.assertTrue(lines[1].startswith(UPDATE_PREFIX), lines[1])
        # Both readings reach the model, and each keeps its own instruction.
        context = payload["hookSpecificOutput"]["additionalContext"]
        self.assertIn("already passed a red reading", context)
        self.assertIn("once per session", context)


class InstallRootOrder(unittest.TestCase):
    """Which of the three install roots answers, and in what order.

    `installed_root()` is never called directly — the contract this suite tests is what the
    hook prints — so each tier is read off the moment carried in the `[ctx-kit update]` line:
    three roots are laid down an hour apart and the one whose mtime comes back is the one that
    won. `CLAUDE_CONFIG_DIR` is the tier the kit had no case for until 2026-09-10: a session
    belonging to somebody who keeps their claude CLI configuration off the default path was
    being compared against a `~/.claude` holding none of their files.
    """

    PLUGIN_AT = SESSION_STARTED + HOUR
    CONFIG_AT = SESSION_STARTED + 2 * HOUR
    HOME_AT = SESSION_STARTED + 3 * HOUR

    def roots(self):
        """One installed copy per tier, each stamped a different hour after the session opened."""
        plugin = installed("root-plugin", self.PLUGIN_AT)
        config = installed("root-config", self.CONFIG_AT)
        installed(os.path.join("root-home", ".claude"), self.HOME_AT)
        return plugin, config, os.path.join(FIXTURES, "root-home")

    def reading(self, name, **env):
        """The staleness line from a transcript that is under both watermark lines."""
        result = run(write_transcript(name, [assistant(UNDER_BOTH)]), **env)
        self.assertEqual(0, result.returncode, result.stderr)
        message = json.loads(result.stdout)["systemMessage"]
        self.assertTrue(message.startswith(UPDATE_PREFIX), message)
        return message

    def test_the_plugin_root_answers_first(self):
        plugin, config, home = self.roots()
        message = self.reading("root-order-plugin.ndjson", CLAUDE_PLUGIN_ROOT=plugin,
                               CLAUDE_CONFIG_DIR=config, HOME=home)
        self.assertIn(clock(self.PLUGIN_AT), message)
        self.assertNotIn(clock(self.CONFIG_AT), message)
        self.assertNotIn(clock(self.HOME_AT), message)

    def test_the_config_dir_answers_when_there_is_no_plugin_root(self):
        """The tier that was missing: set it, and it is read instead of `~/.claude`."""
        plugin, config, home = self.roots()
        message = self.reading("root-order-config.ndjson", CLAUDE_PLUGIN_ROOT="",
                               CLAUDE_CONFIG_DIR=config, HOME=home)
        self.assertIn(clock(self.CONFIG_AT), message)
        self.assertNotIn(clock(self.PLUGIN_AT), message)
        self.assertNotIn(clock(self.HOME_AT), message)

    def test_home_answers_when_neither_variable_is_set(self):
        plugin, config, home = self.roots()
        message = self.reading("root-order-home.ndjson", CLAUDE_PLUGIN_ROOT="",
                               CLAUDE_CONFIG_DIR="", HOME=home)
        self.assertIn(clock(self.HOME_AT), message)
        self.assertNotIn(clock(self.PLUGIN_AT), message)
        self.assertNotIn(clock(self.CONFIG_AT), message)

    def silence(self, name, **env):
        """A run with nothing to say: under both lines, and no install newer than the session."""
        result = run(write_transcript(name, [assistant(UNDER_BOTH)]), **env)
        self.assertEqual("", result.stdout)
        self.assertEqual(0, result.returncode, result.stderr)

    def test_a_config_dir_holding_nothing_reads_nothing_rather_than_the_next_root(self):
        """A tier answers because it is set, not because something was found underneath it.

        Somebody who sets `CLAUDE_CONFIG_DIR` and installs into `~/.claude` anyway has a
        half-moved install, and this line goes quiet for them: `~/.claude` here holds files
        three hours newer than the session, so a fallback would print a reading. Silence is
        the intended answer, not a gap -- reading the next root down would put a directory
        the session does not name up against the session's own clock. The `sh` chain in
        hooks.json does fall back and still finds a script to run, because it is answering
        whether there is anything to run, not which install this session is running.
        """
        plugin, config, home = self.roots()
        self.silence("root-order-config-empty.ndjson", CLAUDE_PLUGIN_ROOT="",
                     CLAUDE_CONFIG_DIR=NO_INSTALL, HOME=home)

    def test_the_plugin_root_answers_over_a_config_dir_even_holding_nothing(self):
        """Both set: the plugin root wins, and it does not hand over when it is empty.

        The direction `test_the_plugin_root_answers_first` cannot see, because there the
        plugin root has files of its own and would win either way. Here it has none, while
        the config dir below it holds files two hours newer than the session -- so anything
        printed at all would be the config dir's reading, and the run is held to silence.
        """
        plugin, config, home = self.roots()
        self.silence("root-order-plugin-empty.ndjson", CLAUDE_PLUGIN_ROOT=NO_INSTALL,
                     CLAUDE_CONFIG_DIR=config, HOME=home)


class ShippedHookCommand(unittest.TestCase):
    """The shell one-liner in hooks.json, run the way a shell runs it.

    The script resolves an install root in python and the hook resolves the path to the script
    in `sh`, separately. A tier added to one and forgotten in the other leaves the hook finding
    nothing to run and the doorbell silent for good, with every test above still green — so the
    shipped string is run here rather than read.
    """

    def command(self, path=HOOKS):
        with open(path, encoding="utf-8") as handle:
            wired = json.load(handle)
        if path == HOOKS:
            return wired["hooks"]["UserPromptSubmit"][0]["hooks"][0]["command"]
        return wired["PostToolUse"][0]["hooks"][0]["command"]

    def stub(self, name):
        """An install root whose `scripts/ctx-watermark.py` only says which root it is."""
        path = os.path.join(FIXTURES, name, "scripts", "ctx-watermark.py")
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as handle:
            handle.write("print(%r)\n" % name)
        return os.path.join(FIXTURES, name)

    def shell(self, stdin_text="{}", **overrides):
        env = dict(os.environ)
        for name in ("CLAUDE_PLUGIN_ROOT", "CLAUDE_CONFIG_DIR"):
            env.pop(name, None)
        # Which interpreter the command settles on is not what is under test here, and the
        # macOS shim in the search list makes the answer machine-dependent. Pin it.
        env["CTXKIT_PYTHON"] = sys.executable
        env.update(overrides)
        return subprocess.run(
            ["sh", "-c", self.command()], input=stdin_text, env=env,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True,
        )

    def test_each_tier_wins_in_the_shipped_order(self):
        plugin, config = self.stub("hook-plugin"), self.stub("hook-config")
        home_root = os.path.join("hook-home", ".claude")
        self.stub(home_root)
        home = os.path.join(FIXTURES, "hook-home")
        for label, env, expected in (
            ("plugin root first",
             dict(CLAUDE_PLUGIN_ROOT=plugin, CLAUDE_CONFIG_DIR=config, HOME=home), "hook-plugin"),
            ("config dir second", dict(CLAUDE_CONFIG_DIR=config, HOME=home), "hook-config"),
            ("home last", dict(HOME=home), home_root),
        ):
            with self.subTest(tier=label):
                result = self.shell(**env)
                self.assertEqual(0, result.returncode, result.stderr)
                self.assertEqual(expected, result.stdout.strip())

    def test_the_config_dir_tier_runs_the_real_script(self):
        """The finding this closes: with only `CLAUDE_CONFIG_DIR` set, nothing was found to run.

        Not a stub — the shipped command finds the real script under that root and the real
        reading comes back out of it. The copy is stamped before the session opened so the
        staleness line stays out of the way and the watermark is the only thing printed.
        """
        root = os.path.join(FIXTURES, "hook-real-config")
        target = os.path.join(root, "scripts", "ctx-watermark.py")
        os.makedirs(os.path.dirname(target), exist_ok=True)
        shutil.copyfile(SCRIPT, target)
        os.utime(target, (SESSION_STARTED - HOUR, SESSION_STARTED - HOUR))
        empty_home = os.path.join(FIXTURES, "hook-empty-home")
        os.makedirs(empty_home, exist_ok=True)
        event = json.dumps({
            "session_id": "synthetic-session",
            "transcript_path": write_transcript("hook-real.ndjson", [assistant(OVER_RED)]),
            "cwd": FIXTURES,
            "hook_event_name": "UserPromptSubmit",
            "prompt": "synthetic prompt",
        })
        result = self.shell(event, CLAUDE_CONFIG_DIR=root, HOME=empty_home)
        self.assertEqual(0, result.returncode, result.stderr)
        message = json.loads(result.stdout)["systemMessage"]
        self.assertTrue(message.startswith(PREFIX), message)
        self.assertIn("513k / red 500k", message)

    def test_both_hook_files_name_the_three_tiers_in_the_same_order(self):
        """The opt-in lint hook ships the same chain; a reader should not find two orders."""
        for path in (HOOKS, CANDIDATE_HOOK):
            with self.subTest(hook=os.path.basename(path)):
                command = self.command(path)
                where = [command.find(marker) for marker in
                         ("${CLAUDE_PLUGIN_ROOT:-}", "${CLAUDE_CONFIG_DIR:-}", "$HOME/.claude")]
                self.assertNotIn(-1, where, command)
                self.assertEqual(sorted(where), where, command)


class WatchedFiles(unittest.TestCase):
    """`INSTALLED` against the list `scripts/sync-installed.sh` actually copies.

    The two are hand-written in two files and they had drifted: the sync script installed
    `scripts/takeover-load.py` and `agents/digest.md` while `INSTALLED` named neither, so an
    update touching only those two moved no mtime the doorbell could see and told nobody.
    Holding one list to the other makes the next file added to one and forgotten in the other
    a red test, instead of a hint that quietly stops seeing things.
    """

    def watched(self):
        """`INSTALLED` read out of the script's source — parsed, never imported or run."""
        with open(SCRIPT, encoding="utf-8") as handle:
            tree = ast.parse(handle.read())
        for node in tree.body:
            if isinstance(node, ast.Assign) and any(
                    isinstance(target, ast.Name) and target.id == "INSTALLED"
                    for target in node.targets):
                names = set()
                for parts in ast.literal_eval(node.value):
                    for path in glob.glob(os.path.join(REPO, *parts)):
                        names.add(os.path.relpath(path, REPO))
                return names
        self.fail("no INSTALLED assignment found in %s" % SCRIPT)

    def synced(self):
        """What `--check` names, from a real run of the shipped script against an empty root."""
        empty = os.path.join(FIXTURES, "sync-empty-home")
        os.makedirs(empty, exist_ok=True)
        env = dict(os.environ)
        for name in ("CLAUDE_PLUGIN_ROOT", "CLAUDE_CONFIG_DIR"):
            env.pop(name, None)
        env["HOME"] = empty
        result = subprocess.run(
            ["bash", SYNC, "--check"], env=env, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, universal_newlines=True,
        )
        # 1 = differences found, which is the whole point of pointing it at an empty root.
        self.assertEqual(1, result.returncode, result.stdout + result.stderr)
        found = set()
        for line in result.stdout.splitlines():
            match = re.match(r"^ {2}(?:same|differs|not installed) +(\S.*)$", line)
            if match:
                found.add(match.group(1))
        return found

    def test_installed_names_every_file_the_sync_script_copies(self):
        synced = self.synced()
        self.assertTrue(synced, "the sync script listed no files at all")
        self.assertEqual(synced, self.watched())

    def test_the_loader_and_the_digest_agent_are_watched(self):
        """Named outright, because these two are the files the hint was blind to."""
        watched = self.watched()
        self.assertIn(os.path.join("scripts", "takeover-load.py"), watched)
        self.assertIn(os.path.join("agents", "digest.md"), watched)


class MakeUp(unittest.TestCase):
    """The line the bell carries with it: by which route this context filled up.

    The split is not this script's own. It is imported from cache-audit.py next door, so the
    doorbell and the weekly checkup cannot answer one question two ways. What is checked here
    is that the doorbell quotes it, that the shares are the ones the fixture was built to
    produce, and that a session under the line is never parsed for it.
    """

    # What the fixture puts in each route: 300 characters this session wrote (a 100-character
    # Bash command and a 200-character prompt handed to a subagent), 400 characters of tool
    # result echoed back, 50 characters of reply. 750 in all, so the shares are 40 / 53 / 7,
    # with 27% of the whole being the prompt written for the subagent.
    def log(self, name, numbers):
        record = assistant(numbers, mid="msg_calls")
        record["message"]["content"] = [
            {"type": "tool_use", "id": "toolu_bash", "name": "Bash",
             "input": {"command": "x" * 100}},
            {"type": "tool_use", "id": "toolu_agent", "name": "Agent",
             "input": {"prompt": "p" * 200}},
            {"type": "text", "text": "y" * 50},
        ]
        echoed = {"type": "user", "message": {"role": "user", "content": [
            {"type": "tool_result", "tool_use_id": "toolu_bash", "content": "z" * 400},
        ]}}
        return write_transcript(name, [record, echoed])

    def test_the_bell_says_which_route_the_context_came_in_by(self):
        result = run(self.log("make-up-ringing.ndjson", OVER_RED))
        self.assertEqual(0, result.returncode, result.stderr)
        payload = json.loads(result.stdout)
        lines = payload["systemMessage"].splitlines()
        self.assertEqual(2, len(lines), lines)
        self.assertTrue(lines[0].startswith(PREFIX), lines[0])
        made = lines[1]
        self.assertTrue(made.startswith(PREFIX), made)
        for share in ("self 40%", "echo 53%", "reports 0%", "replies 7%", "other 0%",
                      "27% is prompts written for a subagent"):
            self.assertIn(share, made)
        # The total the percentages are of, so a reader can recompute any one of them —
        # the same thing cache-audit.py prints under its own table.
        self.assertIn("out of 750 characters", made)
        # The part nobody can see in a log is named rather than counted as zero.
        self.assertIn("outside this split", made)
        # It reaches the model as a reading, and brings no instruction of its own with it.
        context = payload["hookSpecificOutput"]["additionalContext"]
        self.assertIn(made, context)
        self.assertEqual(1, context.count("Report this once per band"))

    def test_no_bell_means_the_log_is_not_parsed_for_it(self):
        """Same content, a watermark under both lines: nothing at all, make-up included."""
        result = run(self.log("make-up-quiet.ndjson", UNDER_BOTH))
        self.assertEqual("", result.stdout)
        self.assertEqual(0, result.returncode, result.stderr)


if __name__ == "__main__":
    unittest.main(verbosity=2)
