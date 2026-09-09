#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""test_case_lint.py — unit tests for scripts/case-lint.py and the rule blocks it lifts.

case-lint keeps no second copy of two of its rules: it runs `scripts/takeover-load.py` as it
stands, and pulls the length block out of `skills/ctx-handoff/SKILL.md` and runs that. So
these tests run against the real skills and scripts of this repository, not against a copy: a
change to either rule that breaks the reading, the output shape or the loading shows up here
rather than in somebody's case file.

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
import shutil
import subprocess
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
SKILLS = os.path.join(ROOT, "skills")
SCRIPT = os.path.join(ROOT, "scripts", "case-lint.py")
LOADER = os.path.join(ROOT, "scripts", "takeover-load.py")
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


def case(name, e_rows=(), i_rows=(), goal="one synthetic goal", e_header=None, header=None):
    """A minimal but complete A~I case file, written under FIXTURES."""
    e_header = e_header or E_HEADER
    body = [
        "# %s" % name,
        header if header is not None else "status: 讨论中   持笔: (TBD)   更新: 2026-09-09",
        "",
        "## A 目标", goal, "",
        "## B 当前方案快照", "to be discussed", "",
        "## C 已拍决策", "",
        "## D 未决与候拍", "| # | 待办/待拍 | 说明 / 建议 |", "|---|---|---|", "",
        "## E 实验台账", e_header, "|" + "---|" * len(E_RULE.strip("|").split("|")),
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
            io.open(LOADER, encoding="utf-8").read(), ["takeover-load.py", path])
        self.assertNotIn("Cell count off the header", out)
        self.assertNotIn("quite settled", out)
        self.assertIn("all 0 undisposed in full", out)

    def test_all_four_places_carry_the_same_split(self):
        """Static check: one regex, written out in four files, and no naive `split('|')` left."""
        pattern = r"(?<!\\)\|"
        naive = ".split('|')"
        places = {
            "case-lint.py": io.open(SCRIPT, encoding="utf-8").read(),
            "takeover-load.py": io.open(LOADER, encoding="utf-8").read(),
        }
        for skill, marker in (("ctx-handoff", "§3"), ("ctx-checkup", "§4")):
            places[skill + " " + marker] = lint.extract_py_block(
                os.path.join(SKILLS, skill, "SKILL.md"))
        for where, text in places.items():
            with self.subTest(place=where):
                self.assertIn(pattern, text)
                self.assertNotIn(naive, text)


LONG = "达" * 500


class LengthCheckScope(unittest.TestCase):
    """The cap is measured where a successor pays for it: on the rows a takeover reads.

    Reading before this batch, on a library of six real cases: one finding, on the verdict
    cell of a delivered row that was neither live nor the newest delivered one — a cell no
    takeover has loaded since the row was superseded.
    """

    def scope(self, name, rows, header=None):
        return results(case(name, e_rows=rows, e_header=header))["2 E cell length"]

    def test_an_old_delivered_row_over_the_cap_is_left_alone(self):
        status, items, _ = self.scope("scope-old.md", [
            e_row("E-01", "已交货", verdict=LONG),
            e_row("E-02", "已交货"),
            e_row("E-03", "已交货"),
        ])
        self.assertEqual("ok", status)
        self.assertEqual([], items)

    def test_the_same_cell_on_a_live_row_is_reported(self):
        status, items, _ = self.scope("scope-live.md", [
            e_row("E-01", "在跑", verdict=LONG),
            e_row("E-02", "已交货"),
            e_row("E-03", "已交货"),
        ])
        self.assertEqual("bad", status)
        self.assertEqual(1, len(items), items)
        self.assertIn("判定", items[0][1])
        self.assertIn("500 chars", items[0][1])

    def test_the_same_cell_on_the_newest_delivered_row_is_reported(self):
        status, items, _ = self.scope("scope-newest.md", [
            e_row("E-01", "已交货"),
            e_row("E-02", "已交货"),
            e_row("E-03", "已交货", verdict=LONG),
        ])
        self.assertEqual("bad", status)
        self.assertEqual(1, len(items), items)

    def test_newest_delivered_is_picked_by_id_not_by_table_order(self):
        """A newest-first ledger has the newest row at the top; the ID decides, not the row."""
        status, items, _ = self.scope("scope-order.md", [
            e_row("E-10", "已交货", verdict=LONG),
            e_row("E-02", "已交货", verdict=LONG),
            e_row("E-01", "已交货"),
        ])
        self.assertEqual("bad", status)
        self.assertEqual(1, len(items), items)  # E-10 only: E-02 is older whichever way it is listed

    def test_english_status_words_are_read_the_same_way(self):
        status, items, _ = self.scope("scope-english.md", [
            e_row("E-01", "delivered", verdict=LONG),
            e_row("E-02", "running", verdict=LONG),
            e_row("E-03", "delivered"),
        ])
        self.assertEqual("bad", status)
        self.assertEqual(1, len(items), items)  # the running row; E-01 is an older delivered one

    def test_with_no_status_column_the_last_three_rows_are_measured(self):
        """No status column: the loader falls back to the last three rows, so those are read."""
        header = "| ID | 要回答的问题 | 任务书路径 | 载体 | 阶段 | 交货路径 | 判定 | 对方案的影响 |"
        status, items, _ = self.scope("scope-nostatus.md", [
            e_row("E-01", "已交货", verdict=LONG),
            e_row("E-02", "已交货"),
            e_row("E-03", "已交货"),
            e_row("E-04", "已交货"),
            e_row("E-05", "已交货", verdict=LONG),
        ], header=header)
        self.assertEqual("bad", status)
        self.assertEqual(1, len(items), items)  # E-05 is in the last three, E-01 is not


GIT = shutil.which("git")


def git(where, *args):
    """One git command, with an identity of its own so a bare machine can still run these."""
    return subprocess.run(
        [GIT, "-C", where, "-c", "user.name=case-lint tests",
         "-c", "user.email=tests@example.invalid", "-c", "commit.gpgsign=false"] + list(args),
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)


@unittest.skipUnless(GIT, "git is not on PATH")
class ArchivesTracked(unittest.TestCase):
    """A case that cites an archive nobody committed is a case whose rows are on one disk only.

    Measured in this project's own books on 2026-09-08: three archive files quoted by name in
    their cases had never been `git add`ed, and the check that would have caught it did not
    exist. The library sits in a private repository nested inside a public one, so the outer
    `git status` was clean throughout.
    """

    NAME = "C-01_synthetic.md"
    ARCHIVE = "C-01_synthetic_决策附录_2026-09-09.md"

    def library(self, where):
        """A case citing one archive, both on disk, in a directory of their own."""
        os.makedirs(where, exist_ok=True)
        path = os.path.join(where, self.NAME)
        os.replace(case(self.NAME, e_rows=[e_row("E-01", "在跑")],
                        goal="rows moved out to `%s`" % self.ARCHIVE), path)
        with io.open(os.path.join(where, self.ARCHIVE), "w", encoding="utf-8") as fh:
            fh.write("# moved verbatim, nothing deleted or altered\n")
        return path

    def check(self, path):
        return results(path)["7 archives tracked"]

    def fresh(self, name):
        where = os.path.join(FIXTURES, name)
        shutil.rmtree(where, ignore_errors=True)
        return where

    def test_an_archive_nobody_added_is_a_finding_and_git_add_settles_it(self):
        where = self.fresh("gate-plain")
        path = self.library(where)
        git(where, "init", "-q")
        git(where, "add", self.NAME)
        git(where, "commit", "-q", "-m", "the case, without its archive")

        status, items, fix = self.check(path)
        self.assertEqual("bad", status)
        self.assertEqual(1, len(items), items)
        self.assertIn(self.ARCHIVE, items[0][1])
        self.assertIn("git add", fix)

        git(where, "add", self.ARCHIVE)
        lint._TOPLEVEL.clear()
        status, items, _ = self.check(path)
        self.assertEqual("ok", status)
        self.assertIn("all tracked", items[0][1])

    def test_a_clean_outer_repository_does_not_speak_for_a_nested_one(self):
        outer = self.fresh("gate-nested")
        inner = os.path.join(outer, "private")
        os.makedirs(inner, exist_ok=True)
        with io.open(os.path.join(outer, ".gitignore"), "w", encoding="utf-8") as fh:
            fh.write("private/\n")
        git(outer, "init", "-q")
        git(outer, "add", ".gitignore")
        git(outer, "commit", "-q", "-m", "outer repository, ignoring the private one")

        path = self.library(inner)
        git(inner, "init", "-q")
        git(inner, "add", self.NAME)
        git(inner, "commit", "-q", "-m", "the case, without its archive")

        self.assertEqual("", git(outer, "status", "--porcelain").stdout.strip(),
                         "the outer repository has to look clean for this test to mean anything")
        lint._TOPLEVEL.clear()
        status, items, _ = self.check(path)
        self.assertEqual("bad", status)
        self.assertEqual(1, len(items), items)
        self.assertIn(os.path.realpath(inner), os.path.realpath(items[0][1].split("books of ")[-1]))

    def test_a_library_outside_git_reports_a_skip_and_no_finding(self):
        where = self.fresh("gate-nogit")
        path = self.library(where)
        lint._TOPLEVEL.clear()
        status, items, _ = self.check(path)
        self.assertEqual("skip", status)
        self.assertIn("not inside a git repository", items[0][1])

    def test_a_library_git_ignores_reports_a_skip_and_no_finding(self):
        """A repository that keeps its cases out of git is a legitimate shape, not a failure."""
        where = self.fresh("gate-ignored")
        os.makedirs(where, exist_ok=True)
        git(where, "init", "-q")
        cases = os.path.join(where, "cases")
        path = self.library(cases)
        with io.open(os.path.join(where, ".gitignore"), "w", encoding="utf-8") as fh:
            fh.write("cases/\n")
        git(where, "add", ".gitignore")
        git(where, "commit", "-q", "-m", "cases stay out of the repository")
        lint._TOPLEVEL.clear()
        status, items, _ = self.check(path)
        self.assertEqual("skip", status)
        self.assertIn("not on this repository's books", items[0][1])

    def test_an_archive_the_case_never_names_is_not_this_case_s_to_answer_for(self):
        where = self.fresh("gate-uncited")
        os.makedirs(where, exist_ok=True)
        path = os.path.join(where, self.NAME)
        os.replace(case(self.NAME, e_rows=[e_row("E-01", "在跑")]), path)
        with io.open(os.path.join(where, self.ARCHIVE), "w", encoding="utf-8") as fh:
            fh.write("# an archive the case does not point at\n")
        git(where, "init", "-q")
        git(where, "add", self.NAME)
        git(where, "commit", "-q", "-m", "the case only")
        lint._TOPLEVEL.clear()
        status, items, _ = self.check(path)
        self.assertEqual("ok", status)
        self.assertIn("no archive file is cited", items[0][1])


class PenHolderForm(unittest.TestCase):
    """Check 8 reports and never fixes: the cell is written by hand, by whoever holds the pen."""

    def check(self, path):
        with io.open(path, encoding="utf-8") as fh:
            lines = fh.read().split("\n")
        return lint.check_pen_holder(path, lines)

    def test_a_stand_in_is_a_legitimate_cell(self):
        for cell in ("(TBD)", "(closed 2026-09-09)", "（待继任填；前任 X 已退役）",
                     "lead (title tool unavailable)"):
            with self.subTest(cell=cell):
                path = case("pen-standin.md",
                            header="status: 讨论中   持笔: %s   更新: 2026-09-09" % cell)
                self.assertEqual("ok", self.check(path)[0])

    def test_the_form_this_kit_produces_passes_when_the_stint_agrees(self):
        path = case("pen-new.md",
                    header="status: 讨论中   持笔: C07-03 billing-two-routes @synthetic   "
                           "任期: 03   更新: 2026-09-09")
        self.assertEqual("ok", self.check(path)[0])

    def test_the_form_it_replaced_is_still_read(self):
        """Old titles are never renamed, so both forms have to pass while their sessions live."""
        path = case("pen-old.md",
                    header="status: 讨论中   持笔: 07-C07billing-two-routes @synthetic   "
                           "更新: 2026-09-09")
        self.assertEqual("ok", self.check(path)[0])

    def test_a_stint_field_disagreeing_with_the_title_is_reported(self):
        path = case("pen-drift.md",
                    header="status: 讨论中   持笔: C07-03 billing-two-routes   stint: 02   "
                           "更新: 2026-09-09")
        status, items, _ = self.check(path)
        self.assertEqual("warn", status)
        self.assertIn("reuse a number", items[0][1])

    def test_a_title_with_no_stint_field_to_count_from_is_reported(self):
        path = case("pen-nostint.md",
                    header="status: 讨论中   持笔: C07-03 billing-two-routes   更新: 2026-09-09")
        status, items, _ = self.check(path)
        self.assertEqual("warn", status)
        self.assertIn("no stint field", items[0][1])

    def test_a_title_in_neither_form_is_reported(self):
        path = case("pen-free.md",
                    header="status: 讨论中   持笔: whatever I felt like calling it   更新: 2026-09-09")
        status, items, _ = self.check(path)
        self.assertEqual("warn", status)
        self.assertIn("neither naming form", items[0][1])

    def test_no_pen_holder_field_at_all_is_reported(self):
        path = case("pen-missing.md", header="status: 讨论中   更新: 2026-09-09")
        status, items, _ = self.check(path)
        self.assertEqual("warn", status)
        self.assertIn("no pen-holder field", items[0][1])

    def test_it_never_fails_a_file(self):
        """Report-only: whatever it finds, the exit code is somebody else's to change."""
        path = case("pen-free-2.md",
                    header="status: 讨论中   持笔: nothing like a title   更新: 2026-09-09")
        self.assertNotEqual("bad", self.check(path)[0])


class LiftedBlocks(unittest.TestCase):
    """One rule is a script and one is lifted out of a skill; both have to keep running."""

    def test_the_handoff_block_extracts_and_runs_and_ends_in_a_total(self):
        path = case("lifted.md", e_rows=[e_row("E-01", "在跑")])
        code = lint.extract_py_block(os.path.join(SKILLS, "ctx-handoff", "SKILL.md"))
        out = lint.run_py_block(code, ["ctx-handoff", path])
        last = [l for l in out.split("\n") if l.strip()][-1]
        self.assertIsNotNone(lint.CELL_TOTAL_RE.match(last), last)
        self.assertEqual(200, int(lint.CELL_TOTAL_RE.match(last).group("limit")))

    def test_the_loader_script_runs_and_ends_in_a_count(self):
        path = case("lifted-loader.md", e_rows=[e_row("E-01", "在跑")])
        code = io.open(LOADER, encoding="utf-8").read()
        out = lint.run_py_block(code, ["takeover-load.py", path])
        self.assertIsNotNone(lint.LOAD_RE.search(out), out[-200:])

    def test_the_loader_is_found_beside_the_skills_directory_given(self):
        """`--skills <a second copy>` has to pick up that copy's loader, not this one's."""
        self.assertEqual(LOADER, lint.find_loader(SKILLS))
        self.assertEqual(LOADER, lint.Rules(SKILLS).loader_path)

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
