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


def call(when, tid, name, mid, inp=None):
    """One assistant record that calls a tool, optionally with something written into it."""
    return {
        "type": "assistant",
        "isSidechain": False,
        "timestamp": when,
        "message": {
            "id": mid,
            "role": "assistant",
            "content": [{"type": "tool_use", "id": tid, "name": name,
                         "input": {} if inp is None else inp}],
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


def said(text):
    """One assistant record that says something back, with no tool call in it."""
    return {
        "type": "assistant",
        "isSidechain": False,
        "timestamp": "2026-09-09T10:00:00.000Z",
        "message": {"id": "m_said", "role": "assistant",
                    "content": [{"type": "text", "text": text}],
                    "usage": {"input_tokens": 1, "cache_read_input_tokens": 1,
                              "cache_creation_input_tokens": 1, "output_tokens": 1}},
    }


def typed(text):
    """One user record carrying plain text — an arrival, or the owner typing."""
    return {"type": "user", "timestamp": "2026-09-09T10:00:00.000Z",
            "message": {"role": "user", "content": text}}


EXT = ".jsonl"  # what cache-audit globs for; the tests below name stems and let this add it


def session(where, stem, echoes):
    """A synthetic session log: one call and one result per (tool name, characters) pair."""
    path = os.path.join(where, stem + EXT)
    with io.open(path, "w", encoding="utf-8") as fh:
        for n, (tool, size) in enumerate(echoes):
            tid = "t%d" % n
            fh.write(json.dumps(call("2026-09-09T10:0%d:00.000Z" % n, tid, tool, "m%d" % n)) + "\n")
            fh.write(json.dumps(result(tid, "x" * size)) + "\n")
    return path


def subagent(where, parent_stem, stem, echoes):
    """The same, written where a subagent of `parent_stem` keeps its transcript."""
    here = os.path.join(where, parent_stem, "subagents")
    os.makedirs(here, exist_ok=True)
    return session(here, stem, echoes)


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

    def echo_of(self, out, stem):
        """The echo cell of one row, as an integer."""
        for line in out.split("\n"):
            if line.startswith(stem + EXT):
                return int(line.split()[-2].replace(",", ""))
        self.fail("no row for %s in:\n%s" % (stem, out))

    def bash_of(self, out, stem):
        for line in out.split("\n"):
            if line.startswith(stem + EXT):
                return int(line.split()[-1].rstrip("%").replace("⚠️", "").strip())
        self.fail("no row for %s in:\n%s" % (stem, out))

    def test_a_subagents_echo_is_counted_into_the_session_that_dispatched_it(self):
        session(self.where, "s", [("Bash", 1000), ("Read", 500)])
        subagent(self.where, "s", "agent-one", [("Bash", 2500)])
        done = run(self.where)
        self.assertEqual(0, done.returncode, done.stderr)
        self.assertEqual(4000, self.echo_of(done.stdout, "s"))
        self.assertEqual(88, self.bash_of(done.stdout, "s"))  # 3500 of 4000
        self.assertIn("subagent transcripts included", done.stdout)

    def test_a_workflow_journal_under_subagents_is_not_counted(self):
        session(self.where, "s", [("Read", 100)])
        subagent(self.where, "s", "journal", [("Bash", 9999)])
        done = run(self.where)
        self.assertEqual(100, self.echo_of(done.stdout, "s"))

    def test_the_same_tool_use_id_written_twice_arrives_once(self):
        # a resumed or forked log writes the same result again; it is one arrival in one context
        path = os.path.join(self.where, "s" + EXT)
        with io.open(path, "w", encoding="utf-8") as fh:
            fh.write(json.dumps(call("2026-09-09T10:00:00.000Z", "t1", "Read", "m1")) + "\n")
            fh.write(json.dumps(result("t1", "R" * 700)) + "\n")
            fh.write(json.dumps(result("t1", "R" * 700)) + "\n")
        done = run(self.where)
        self.assertEqual(700, self.echo_of(done.stdout, "s"))

    def test_a_result_written_before_its_own_tool_use_is_still_named(self):
        # order is normally the other way round; a forked log can invert it, and an echo
        # charged to no tool at all would silently drop out of the bash share
        path = os.path.join(self.where, "s" + EXT)
        with io.open(path, "w", encoding="utf-8") as fh:
            fh.write(json.dumps(result("t1", "B" * 400)) + "\n")
            fh.write(json.dumps(call("2026-09-09T10:00:00.000Z", "t1", "Bash", "m1")) + "\n")
        done = run(self.where)
        self.assertEqual(400, self.echo_of(done.stdout, "s"))
        self.assertEqual(100, self.bash_of(done.stdout, "s"))

    def test_a_part_that_is_not_text_counts_zero_characters(self):
        path = os.path.join(self.where, "s" + EXT)
        with io.open(path, "w", encoding="utf-8") as fh:
            fh.write(json.dumps(call("2026-09-09T10:00:00.000Z", "t1", "Read", "m1")) + "\n")
            fh.write(json.dumps({
                "type": "user", "timestamp": "2026-09-09T10:00:01.000Z",
                "message": {"role": "user", "content": [{
                    "type": "tool_result", "tool_use_id": "t1",
                    "content": [{"type": "text", "text": "x" * 250},
                                {"type": "image", "source": {"data": "y" * 5000}}]}]}}) + "\n")
        done = run(self.where)
        self.assertEqual(250, self.echo_of(done.stdout, "s"))

    def test_the_blind_spot_count_takes_the_sessions_the_per_call_gate_never_sees(self):
        # over the gate in total, never in one call: the reading the count exists for
        session(self.where, "quiet", [("Bash", 20000), ("Bash", 20000)])
        # one call past the gate on its own: the gate saw this session, so it is not counted
        session(self.where, "loud", [("Read", 40000)])
        done = run(self.where)
        self.assertIn("1 of 2 session(s) echo more than 30,000 characters in total", done.stdout)
        self.assertIn("a reading, no line is set on it", done.stdout)

    def test_out_writes_the_same_text_the_terminal_got(self):
        session(self.where, "s", [("Read", 120)])
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

    def test_out_makes_the_directory_it_was_pointed_at(self):
        # a project's first checkup points --out at a CHECKUP/ that does not exist yet.
        # Before this, the audit printed in full and then exited 2, leaving no artifact.
        session(self.where, "s", [("Read", 120)])
        target = os.path.join(self.where, "CHECKUP", "2026-09-09.md")
        done = subprocess.run(
            [sys.executable, SCRIPT, "--project", self.where, "--cases", self.where,
             "--out", target, "--all", "0"],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
        self.assertEqual(0, done.returncode, done.stderr)
        self.assertTrue(os.path.isfile(target), done.stdout + done.stderr)
        self.assertIn("# written to " + target, done.stdout)
        self.assertIn("session", io.open(target, encoding="utf-8").read())

    def test_out_is_off_unless_asked_for(self):
        session(self.where, "s", [("Read", 120)])
        done = run(self.where)
        self.assertNotIn("# written to", done.stdout)
        self.assertEqual([], [n for n in os.listdir(self.where) if n.endswith(".md")])

    def test_out_without_a_path_is_a_usage_error(self):
        done = subprocess.run(
            [sys.executable, SCRIPT, "--out"],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
        self.assertEqual(2, done.returncode)
        self.assertIn("--out needs a path", done.stderr)


def billed(when, mid, ctx, out=100):
    """One billable assistant record whose context reads exactly `ctx` tokens."""
    given = 10
    read = (ctx - given) // 2
    return {
        "type": "assistant", "isSidechain": False, "timestamp": when,
        "message": {"id": mid, "role": "assistant",
                    "usage": {"input_tokens": given, "cache_read_input_tokens": read,
                              "cache_creation_input_tokens": ctx - given - read,
                              "output_tokens": out}},
    }


class EntryPhase(unittest.TestCase):
    """floor / entry / at: what a session pays before anybody speaks, and what the opening job added.

    The boundary is the owner's second turn — on a session opened with a takeover, the
    spot-check that ends the recite. Where there is no second turn there is no boundary, and
    the two cells say so rather than standing in a number that would be read as a takeover.
    """

    def setUp(self):
        self.where = os.path.join(FIXTURES, self._testMethodName)
        if os.path.isdir(self.where):
            shutil.rmtree(self.where)
        os.makedirs(self.where)

    def write(self, stem, records):
        path = os.path.join(self.where, stem + EXT)
        with io.open(path, "w", encoding="utf-8") as fh:
            for r in records:
                fh.write(json.dumps(r) + "\n")
        return path

    def cells(self, out, stem):
        """(floor, entry, at) off one row — echo and bash% stay the last two columns."""
        for line in out.split("\n"):
            if line.startswith(stem + EXT):
                parts = line.split()
                return parts[-7], parts[-6], parts[-5]
        self.fail("no row for %s in:\n%s" % (stem, out))

    def test_the_owners_second_turn_ends_the_entry_phase(self):
        self.write("s", [
            typed("take over the case"),
            billed("2026-09-09T10:00:00.000Z", "m0", 10_000),
            billed("2026-09-09T10:01:00.000Z", "m1", 30_000),
            typed("looks right, carry on"),
            billed("2026-09-09T10:02:00.000Z", "m2", 45_000),
            billed("2026-09-09T10:03:00.000Z", "m3", 60_000),
        ])
        done = run(self.where)
        self.assertEqual(0, done.returncode, done.stderr)
        self.assertEqual(("10,000", "35,000", "3"), self.cells(done.stdout, "s"))

    def test_with_no_second_turn_both_cells_say_so(self):
        """A dispatched session is given one brief and left to run: no boundary to measure."""
        self.write("s", [
            typed("here is the brief, get on with it"),
            billed("2026-09-09T10:00:00.000Z", "m0", 12_000),
            billed("2026-09-09T10:01:00.000Z", "m1", 90_000),
        ])
        done = run(self.where)
        self.assertEqual(("12,000", "-", "-"), self.cells(done.stdout, "s"))
        self.assertIn("1 of 1 row(s) print `-`", done.stdout)

    def test_what_the_client_writes_is_not_the_owner_taking_a_turn(self):
        """A slash command writes its own name and its output before the owner's text."""
        self.write("s", [
            typed("<command-name>/ctx-takeover</command-name>"),
            typed("<local-command-stdout>ran it</local-command-stdout>"),
            typed("take over the case"),
            billed("2026-09-09T10:00:00.000Z", "m0", 10_000),
            typed("<task-notification>a subagent finished</task-notification>"),
            billed("2026-09-09T10:01:00.000Z", "m1", 20_000),
            typed("now the spot-check"),
            billed("2026-09-09T10:02:00.000Z", "m2", 50_000),
        ])
        done = run(self.where)
        self.assertEqual(("10,000", "40,000", "3"), self.cells(done.stdout, "s"))

    def test_the_header_and_the_note_carry_the_three_readings(self):
        self.write("s", [billed("2026-09-09T10:00:00.000Z", "m0", 5_000)])
        done = run(self.where)
        head = next(l for l in done.stdout.split("\n") if l.startswith("session"))
        for word in ("floor", "entry", "at"):
            self.assertIn(word, head)
        self.assertIn("no line is set on either", done.stdout)


class MakeUp(unittest.TestCase):
    """The self and reports columns, and the line that splits one log five ways.

    What these two columns are for is the opposite question from the echo column's: echo asks
    what the whole dispatched job read, so a subagent's results count into the session that
    sent it; self and reports ask what filled *this* context, so a subagent's own writing does
    not. The two live side by side in the same table, and the difference is stated in the
    printed line as well as here.
    """

    def setUp(self):
        self.where = os.path.join(FIXTURES, self._testMethodName)
        if os.path.isdir(self.where):
            shutil.rmtree(self.where)
        os.makedirs(self.where)

    def write(self, stem, records):
        path = os.path.join(self.where, stem + EXT)
        with io.open(path, "w", encoding="utf-8") as fh:
            for r in records:
                fh.write(json.dumps(r) + "\n")
        return path

    # Counted from the right-hand end, because the header's own `p50 ctx` is two words and
    # would throw a count from the left off by one. No fixture here crosses a line, so no row
    # carries the trailing flag that would shift these.
    FROM_THE_RIGHT = {"self": -4, "reports": -3, "echo": -2}

    def cell(self, out, stem, which):
        """One numeric cell of a row, by column name."""
        row = next(l for l in out.split("\n") if l.startswith(stem + EXT))
        self.assertNotIn("\u26a0", row, "a flagged row shifts the columns counted here")
        return int(row.split()[self.FROM_THE_RIGHT[which]].replace(",", ""))

    def test_what_the_session_wrote_into_tool_calls_is_counted_as_self(self):
        # 300 characters of command, 40 of description: the values, not the JSON around them
        self.write("s", [
            call("2026-09-09T10:00:00.000Z", "t1", "Bash", "m1",
                 {"command": "x" * 300, "description": "y" * 40}),
            result("t1", "z" * 10),
        ])
        done = run(self.where)
        self.assertEqual(0, done.returncode, done.stderr)
        self.assertEqual(340, self.cell(done.stdout, "s", "self"))

    def test_a_subagents_own_writing_is_not_counted_into_the_parents_self(self):
        # the subagent's echo is the parent's echo; the subagent's heredoc is not the
        # parent's self, because it was never in the parent's context
        self.write("s", [call("2026-09-09T10:00:00.000Z", "t1", "Agent", "m1",
                              {"prompt": "p" * 100}),
                         result("t1", "r" * 50)])
        here = os.path.join(self.where, "s", "subagents")
        os.makedirs(here)
        with io.open(os.path.join(here, "agent-one" + EXT), "w", encoding="utf-8") as fh:
            fh.write(json.dumps(call("2026-09-09T10:01:00.000Z", "t9", "Bash", "m9",
                                     {"command": "q" * 7000})) + "\n")
            fh.write(json.dumps(result("t9", "e" * 400)) + "\n")
        done = run(self.where)
        self.assertEqual(100, self.cell(done.stdout, "s", "self"))
        self.assertEqual(450, self.cell(done.stdout, "s", "echo"))

    def test_what_came_back_from_elsewhere_is_counted_as_reports(self):
        self.write("s", [
            said("ok"),
            typed("<task-notification>\n<task-id>abc</task-id>\n" + "n" * 100),
            typed('Another Claude session sent a message:\n<cross-session-message from="x">'
                  + "m" * 100),
            typed("please carry on"),  # the owner: not a report
        ])
        done = run(self.where)
        reports = self.cell(done.stdout, "s", "reports")
        self.assertEqual(len("<task-notification>\n<task-id>abc</task-id>\n" + "n" * 100)
                         + len('Another Claude session sent a message:\n'
                               '<cross-session-message from="x">' + "m" * 100), reports)
        # the owner's own line lands in `other`, so it is neither self nor reports
        self.assertIn("other", done.stdout)

    def test_the_make_up_line_names_five_routes_and_the_dispatch_share(self):
        self.write("s", [
            call("2026-09-09T10:00:00.000Z", "t1", "Agent", "m1", {"prompt": "p" * 250}),
            result("t1", "e" * 250),
            typed("<task-notification>" + "n" * 230),
            said("s" * 250),
        ])
        done = run(self.where)
        line = next(l for l in done.stdout.split("\n") if l.startswith("# make-up"))
        for route in ("self", "echo", "reports", "replies", "other"):
            self.assertIn(route, line)
        self.assertIn("prompts written for a subagent", line)
        # the fixed part is named as outside the split rather than silently missing from it
        self.assertIn("system prompt and tool definitions", line)
        self.assertIn("outside this split", line)
        # every character in this fixture went down one of the four routes it exercises
        self.assertIn("self 25%", line)
        self.assertIn("echo 25%", line)


if __name__ == "__main__":
    unittest.main(verbosity=2)
