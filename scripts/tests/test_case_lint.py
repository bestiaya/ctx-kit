#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""test_case_lint.py — unit tests for scripts/case-lint.py and the rule blocks it lifts.

case-lint keeps no second copy of two of its rules: it pulls the python block out of
`skills/ctx-takeover/SKILL.md` and `skills/ctx-handoff/SKILL.md` and runs it as it stands. So
these tests run against the real skills directory of this repository, not against a copy: a
change to either block that breaks the extraction, the output shape or the reading shows up
here rather than in somebody's case file.

The case files under /tmp here are synthetic — made-up rows with made-up text. No real case
library is read or written.

Run:
    python3 -m pytest scripts/tests -q
    python3 -m unittest discover -s scripts/tests
Use a working python3 — on macOS /usr/bin/python3 is an Xcode shim that cannot even import json.
"""
import importlib.util
import io
import os
import subprocess
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
SKILLS = os.path.join(ROOT, "skills")
SCRIPT = os.path.join(ROOT, "scripts", "case-lint.py")
FIXTURES = os.environ.get("CTXKIT_TEST_DIR") or "/tmp/ctx-case-lint-tests"


def _load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


lint = _load(SCRIPT, "case_lint_under_test")


def setUpModule():
    os.makedirs(FIXTURES, exist_ok=True)


E_HEADER = "| ID | 要回答的问题 | 任务书路径 | 载体 | 状态 | 交货路径 | 判定 | 对方案的影响 |"
E_RULE = "|---|---|---|---|---|---|---|---|"
I_HEADER = "| 日期 | 来自 | 来话 | 处置 |"
I_RULE = "|---|---|---|---|"


def e_row(rid, status, verdict="达成", impact="无", question="does it hold"):
    return "| %s | %s | brief.md | sub | %s | out.md | %s | %s |" % (
        rid, question, status, verdict, impact)


def case(name, e_rows=(), i_rows=(), goal="one synthetic goal"):
    """A minimal but complete A~I case file, written under FIXTURES."""
    body = [
        "# %s" % name,
        "status: 讨论中   持笔: (TBD)   更新: 2026-09-09",
        "",
        "## A 目标", goal, "",
        "## B 当前方案快照", "to be discussed", "",
        "## C 已拍决策", "",
        "## D 未决与候拍", "| # | 待办/待拍 | 说明 / 建议 |", "|---|---|---|", "",
        "## E 实验台账", E_HEADER, E_RULE,
    ]
    body += list(e_rows)
    body += ["", "## F 编年志", "", "## G 档案指针", "", "## H 未落盘清单", "",
             "## I 收件位", I_HEADER, I_RULE]
    body += list(i_rows)
    body += [""]
    path = os.path.join(FIXTURES, name)
    with io.open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(body))
    return path


def results(path, skills=SKILLS):
    """{check name: (status, items, fix)} for one case file."""
    got = lint.lint_file(path, lint.Rules(skills))
    return {name: (status, items, fix) for name, status, items, fix in got}


class SplitAgreement(unittest.TestCase):
    """One row, one shape: the four places that split a table row have to count it the same.

    Reading before this batch, on the 8-column row below carrying one `\\|`: the loader in
    ctx-takeover §2 and the length block in ctx-handoff §3 both made 9 cells of it, while
    `split_cells` made 8 — so a row that escaped its pipes exactly as the docs say came out
    one column wide to a takeover, was read as malformed and loaded whole, and this checker
    never mentioned it.
    """

    ESCAPED = r"a cell holding a \| of its own"

    def test_split_cells_counts_the_row_as_the_header_declares_it(self):
        row = e_row("E-01", "在跑", question=self.ESCAPED)
        self.assertEqual(len(lint.split_cells(E_HEADER)), 8)
        self.assertEqual(len(lint.split_cells(row)), 8)
        # the escaped pipe stays inside its own cell, it does not open a new one
        self.assertIn(r"\|", lint.split_cells(row)[1])

    def test_the_handoff_block_reads_the_cell_the_header_points_at(self):
        """The long text sits in the last column; one extra cell would put it out of reach.

        A block that split at every `|` would count 9 cells and find the over-long text at
        index 8, past the two columns the header names — and report nothing at all.
        """
        long_impact = "影" * 260
        path = case("split-handoff.md",
                    e_rows=[e_row("E-01", "在跑", question=self.ESCAPED, impact=long_impact)])
        status, items, _ = results(path)["2 E cell length"]
        self.assertEqual("bad", status)
        self.assertEqual(1, len(items), items)
        self.assertIn("对方案的影响", items[0][1])

    def test_the_takeover_loader_reads_an_escaped_row_as_disposed(self):
        """An escaped pipe must not make a settled inbox row look malformed and live.

        Four disposed rows, the escaped one oldest: the loader keeps the last three and leaves
        this one in the case. Counted as malformed it would come back undisposed, in full.
        """
        rows = ["| 2026-09-0%d | other case | %s | 已办 |" % (n, text) for n, text in (
            (1, "an old message with a \\| inside it, quite settled"),
            (2, "second"), (3, "third"), (4, "fourth"))]
        path = case("split-loader.md", i_rows=rows)
        out = lint.run_py_block(
            lint.extract_py_block(os.path.join(SKILLS, "ctx-takeover", "SKILL.md")),
            ["ctx-takeover", path])
        self.assertNotIn("Cell count off the header", out)
        self.assertNotIn("quite settled", out)
        self.assertIn("all 0 undisposed in full", out)

    def test_all_four_places_carry_the_same_split(self):
        """Static check: one regex, written out in four files, and no naive `split('|')` left."""
        pattern = r"(?<!\\)\|"
        naive = ".split('|')"
        places = {
            "case-lint.py": io.open(SCRIPT, encoding="utf-8").read(),
        }
        for skill, marker in (("ctx-takeover", "§2"), ("ctx-handoff", "§3"), ("ctx-checkup", "§4")):
            places[skill + " " + marker] = lint.extract_py_block(
                os.path.join(SKILLS, skill, "SKILL.md"))
        for where, text in places.items():
            with self.subTest(place=where):
                self.assertIn(pattern, text)
                self.assertNotIn(naive, text)


class LiftedBlocks(unittest.TestCase):
    """The two blocks are lifted out of the skills at run time; the lifting has to keep working."""

    def test_the_handoff_block_extracts_and_runs_and_ends_in_a_total(self):
        path = case("lifted.md", e_rows=[e_row("E-01", "在跑")])
        code = lint.extract_py_block(os.path.join(SKILLS, "ctx-handoff", "SKILL.md"))
        out = lint.run_py_block(code, ["ctx-handoff", path])
        last = [l for l in out.split("\n") if l.strip()][-1]
        self.assertIsNotNone(lint.CELL_TOTAL_RE.match(last), last)
        self.assertEqual(200, int(lint.CELL_TOTAL_RE.match(last).group("limit")))

    def test_the_takeover_block_extracts_and_runs_and_ends_in_a_count(self):
        path = case("lifted-loader.md", e_rows=[e_row("E-01", "在跑")])
        code = lint.extract_py_block(os.path.join(SKILLS, "ctx-takeover", "SKILL.md"))
        out = lint.run_py_block(code, ["ctx-takeover", path])
        self.assertIsNotNone(lint.LOAD_RE.search(out), out[-200:])

    def test_the_command_line_reports_a_clean_case_as_clean(self):
        here = os.path.join(FIXTURES, "cli")
        os.makedirs(here, exist_ok=True)
        path = os.path.join(here, "cli-one.md")
        os.replace(case("cli-one.md", e_rows=[e_row("E-01", "在跑")]), path)
        done = subprocess.run(
            [sys.executable, SCRIPT, "--skills", SKILLS, here],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
        self.assertEqual(0, done.returncode, done.stdout + done.stderr)
        self.assertIn("checks clean", done.stdout)


if __name__ == "__main__":
    unittest.main(verbosity=2)
