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


if __name__ == "__main__":
    unittest.main(verbosity=2)
