#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""case-lint.py — health check for case files, run against one file or a library.

Eight checks, each reported on its own (every finding prints as `file:line`):
  1. takeover load   what one takeover has to read in, in characters, in three
                     bands — <=10,000 green / <=15,000 yellow / above that must
                     be slimmed before the case changes hands
  2. E cell length   the Verdict cell and the Impact-on-plan cell, each capped at
                     200 characters — measured on the rows a takeover reads and no
                     others: the live rows plus the single most recent delivered
                     row — most recent by ID (E-10b-2 sorts before E-11), never by
                     the order the rows sit in the table, and a row marked done
                     counts as delivered here. An older delivered row is never read
                     in, so its length costs a successor nothing
  3. E status words  every status cell opens with one of the six agreed words
                     (running / awaiting acceptance / queued / to dispatch /
                     delivered / done). A verdict written into the status cell
                     makes the row invisible to every skill that reads the ledger
  4. D struck rows   a settled to-do is deleted, not struck through: a `~~N~~`
                     row, or one marked done, goes on costing every successor
  5. inbox disposal  a disposition cell that does not open with
                     done / dropped / moved to is read as still waiting, and
                     that row keeps its place in the slice for good
  6. table columns   any row whose cell count is off its header row — almost
                     always a bare `|` inside somebody's sentence, which puts
                     every column past it out of step
  7. archives tracked  every archive file the case cites by name is on the books
                     of the repository the case file itself lives in. A library
                     kept outside git is a legitimate shape and reports a skip,
                     not a finding
  8. pen-holder form  the header line carries a pen-holder cell, and where that
                     cell holds a session title it is one of the two naming forms
                     (`C07-03 …` now, `03-C07… ` before it) with a stint number
                     agreeing with the header's own `stint` field. Reported only,
                     never a finding: a title is set by hand and by a person

Checks 1 and 2 keep no second copy of the rule: check 1 runs `scripts/takeover-load.py`
as it stands — the same script `ctx-takeover` §2 tells a session to run — and check 2
lifts the python block out of `skills/ctx-handoff/SKILL.md` and runs that. So the kit
remains the one place each rule is written and the readings here cannot drift from what
a takeover or a close-out actually does. Change either and the readings follow.

Usage:
  case-lint.py <case file>         check one case
  case-lint.py <directory>         check every case in a library (archives and
                                   the board are skipped)
  case-lint.py --quiet <path>      print nothing unless something is wrong
  case-lint.py --skills <dir> ...  read the rules from another copy of the kit
                                   (for testing this script): the length block from
                                   that directory's ctx-handoff, and the loader from
                                   the `scripts/` beside it if there is one

Exit codes: 0 all clear, 1 findings, 2 bad usage or a file that would not read.

Python 3.8+, standard library only.
"""

import argparse
import io
import os
import re
import subprocess
import sys
from contextlib import redirect_stdout

# ---------------------------------------------------------------- what counts as a case

EXCLUDE_MARKS = (
    "_决策附录_", "_实验档案_", "_编年志档案_",
    "_decision-archive_", "_experiment-archive_", "_chronicle-archive_",
)
EXCLUDE_NAMES = ("TASKBOARD.md",)

SECTION_RE = re.compile(r"^##\s+([A-Z])\.?(\s|$)")

# A `\|` inside a cell is content, not a separator (ctx-handoff §4 step 2). Three more places
# carry this same split and all four have to agree, or a row that escapes its pipes by the rule
# reads as one shape here and another there: `scripts/takeover-load.py` (the loader ctx-takeover
# §2 runs), the length block in `ctx-handoff` §3, and the same block over a library in
# `ctx-checkup` §4.
CELL_SPLIT = re.compile(r"(?<!\\)\|")

# The six status words and nothing else, both sides anchored; leading punctuation
# or `**` allowed, exactly as `scripts/takeover-load.py` reads them.
STATUS_RE = re.compile(
    r"^\W*(在跑|待验收|排队|待派|已交货|已完"
    r"|running|awaiting acceptance|queued|to dispatch|delivered|done)", re.I)
STATUS_WORDS = "在跑 / 待验收 / 排队 / 待派 / 已交货 / 已完 " \
               "(running / awaiting acceptance / queued / to dispatch / delivered / done)"

DISPOSAL_RE = re.compile(r"^\W*(已办|不办|已转|done|dropped|moved)", re.I)
D_DONE_RE = re.compile(r"已办|已完成|办完|\bdone\b", re.I)

CHECK_NAMES = [
    "1 takeover load",
    "2 E cell length",
    "3 E status words",
    "4 D struck rows",
    "5 inbox disposal",
    "6 table columns",
    "7 archives tracked",
    "8 pen-holder form",
]

# The header line's pen-holder cell. Anything but a session title — nobody signed yet, the
# case is closed, the predecessor retired, a bare terminal wrote a role instead of a name —
# is a legitimate cell and is left alone.
PEN_FIELD_RE = re.compile(r"(?:持笔|pen-holder)\s*[:：]\s*(.*)$", re.I)
STINT_FIELD_RE = re.compile(r"(?:任期|stint)\s*[:：]\s*(\d+)")
HEADER_FIELD_RE = re.compile(r"(?:更新|updated|状态|status|任期|stint)\s*[:：]", re.I)
PEN_PLACEHOLDER_RE = re.compile(
    r"^[(（]|^\W*(TBD|待定|待继任填|successor to fill in|closed|已关|已收口"
    r"|lead|exec|导师|执行)\b", re.I)
# Current form first, the one it replaced second — both are read, because old titles are
# never renamed and the two stand side by side for as long as their sessions live.
PEN_TITLE_NEW_RE = re.compile(r"^(?:✕\s*)?C(\d+)-(\d+)(?:\.\d+)*(?:\s|$)")
PEN_TITLE_OLD_RE = re.compile(r"^(?:✕\s*)?(\d+)(?:\.\d+)*-C\d+")


def is_case_file(path):
    """A .md that is neither an archive split off a case nor the board."""
    name = os.path.basename(path)
    if not name.endswith(".md"):
        return False
    if name in EXCLUDE_NAMES:
        return False
    for mark in EXCLUDE_MARKS:
        if mark in name:
            return False
    return True


# ---------------------------------------------------------------- table reading

def split_cells(line):
    """Cells of one markdown row, split on unescaped pipes only.

    The loader script and the two blocks the skills own split the same way, line for line. Measured on one
    8-column row carrying one `\\|`: they used to split at every `|` they saw and make 9 cells
    of it against the 8 counted here, so a row written by the rule read as malformed to a
    takeover and was loaded whole, while this checker never said a word about it.
    """
    parts = CELL_SPLIT.split(line.strip())
    if parts and not parts[0].strip():
        parts = parts[1:]
    if parts and not parts[-1].strip():
        parts = parts[:-1]
    return [p.strip() for p in parts]


def is_delimiter(line):
    s = line.strip()
    return bool(s) and "-" in s and not set(s) - set("|-: \t")


def strip_fenced(lines):
    """Line numbers of every line outside a ``` fence, plus the text."""
    out, fenced = [], False
    for i, line in enumerate(lines):
        if line.lstrip().startswith("```"):
            fenced = not fenced
            continue
        if not fenced:
            out.append((i + 1, line))
    return out


def sections(lines):
    """{'A': (start_index, end_index), ...} over the A~I headings."""
    marks = [i for i, l in enumerate(lines) if SECTION_RE.match(l)]
    got = {}
    for n, i in enumerate(marks):
        end = marks[n + 1] if n + 1 < len(marks) else len(lines)
        got[SECTION_RE.match(lines[i]).group(1)] = (i, end)
    return got


def table_rows(lines, span):
    """[(1-based line number, text)] for every table row in a section."""
    a, b = span
    return [(i + 1, lines[i]) for i in range(a, b) if lines[i].lstrip().startswith("|")]


def column_of(header, pattern):
    for i, cell in enumerate(header):
        if re.search(pattern, cell, re.I):
            return i
    return -1


def excerpt(s, n=60):
    s = " ".join(s.split())
    return s[:n] + ("…" if len(s) > n else "")


# ---------------------------------------------------------------- the rules, lifted from the skills

_COMPILED = {}


def extract_py_block(skill_path):
    """The python between `<<'PY'` and the closing `PY` in a SKILL.md.

    The first such block, and a skill that carries more than one keeps `PY` for
    the one meant to be lifted from here — ctx-checkup's other block uses a tag
    of its own for exactly that reason.
    """
    with io.open(skill_path, encoding="utf-8") as fh:
        lines = fh.read().split("\n")
    start = None
    for i, line in enumerate(lines):
        if "<<'PY'" in line:
            start = i + 1
            break
    if start is None:
        raise RuntimeError("no <<'PY' block in " + skill_path)
    for j in range(start, len(lines)):
        if lines[j].strip() == "PY":
            return "\n".join(lines[start:j])
    raise RuntimeError("unterminated <<'PY' block in " + skill_path)


def run_py_block(code, argv):
    """Run a lifted block with argv set, and hand back everything it printed."""
    obj = _COMPILED.get(code)
    if obj is None:
        obj = compile(code, "<skill block>", "exec")
        _COMPILED[code] = obj
    buf = io.StringIO()
    saved = sys.argv
    sys.argv = argv
    try:
        with redirect_stdout(buf):
            exec(obj, {"__name__": "__skill_block__"})
    finally:
        sys.argv = saved
    return buf.getvalue()


def find_skills_dir(explicit):
    """Where this machine's skills are, after the repository copy beside this script.

    The install roots come in the one fixed order the whole kit uses — `CLAUDE_PLUGIN_ROOT`,
    then `CLAUDE_CONFIG_DIR`, then `~/.claude` — so somebody who keeps their claude CLI
    configuration somewhere other than the default is not read against a `~/.claude` that
    holds nothing of theirs.
    """
    if explicit:
        return explicit
    here = os.path.dirname(os.path.abspath(__file__))
    plugin_root = os.environ.get("CLAUDE_PLUGIN_ROOT", "")
    config_dir = os.environ.get("CLAUDE_CONFIG_DIR", "")
    for cand in (os.path.join(os.path.dirname(here), "skills"),
                 os.path.join(plugin_root, "skills") if plugin_root else None,
                 os.path.join(config_dir, "skills") if config_dir else None,
                 os.path.expanduser("~/.claude/skills")):
        if cand and os.path.isfile(os.path.join(cand, "ctx-handoff", "SKILL.md")):
            return cand
    return None


def find_loader(skills_dir):
    """`scripts/takeover-load.py`, the loader ctx-takeover §2 tells a session to run.

    A `scripts/` beside the skills directory first, so `--skills` picks up a whole second
    copy of the kit; then the directory this script itself sits in. Every layout the kit
    installs into keeps the two beside each other — repository, plugin root, a
    `CLAUDE_CONFIG_DIR`, `~/.claude/` — so the sibling rule covers all of them and nothing
    has to be typed by hand.
    """
    here = os.path.dirname(os.path.abspath(__file__))
    for cand in (os.path.join(os.path.dirname(os.path.abspath(skills_dir)), "scripts")
                 if skills_dir else None, here):
        if cand and os.path.isfile(os.path.join(cand, "takeover-load.py")):
            return os.path.join(cand, "takeover-load.py")
    return None


class Rules(object):
    """The two rules run as they stand, read once per run.

    The loader is a script file rather than a block inside the skill (it was moved out so a
    takeover stops pasting 5,800 characters of python into a shell every time), so it is read
    from disk here; the length rule is still a block inside ctx-handoff and is lifted out.
    """

    def __init__(self, skills_dir, loader_path=None):
        loader_path = loader_path or find_loader(skills_dir)
        if not loader_path or not os.path.isfile(loader_path):
            raise RuntimeError("no takeover-load.py beside %s or %s"
                               % (skills_dir, os.path.dirname(os.path.abspath(__file__))))
        with io.open(loader_path, encoding="utf-8") as fh:
            self.takeover = fh.read()
        self.loader_path = loader_path
        self.handoff = extract_py_block(
            os.path.join(skills_dir, "ctx-handoff", "SKILL.md"))


LOAD_RE = re.compile(r"characters loaded this time:\s*([\d,]+)")
CELL_DETAIL_RE = re.compile(r"^(?P<path>.+):(?P<line>\d+)\s+\[(?P<col>.*)\]\s+(?P<n>\d+)\s+chars\s*$")
CELL_TOTAL_RE = re.compile(r"^---\s+(?P<n>\d+)\s+cells over (?P<limit>\d+) characters")


# -------------------------------------------------------------- the eight checks

def check_takeover_load(path, rules):
    """1. What one takeover reads in, measured by the loader the skill owns."""
    try:
        out = run_py_block(rules.takeover, ["ctx-takeover", path])
    except Exception as exc:  # a case the loader cannot read is a finding in itself
        return "bad", [("-", "the ctx-takeover loader failed on this file: %s" % exc)], \
               "fix the malformed section it choked on, then run again"
    hit = LOAD_RE.search(out)
    if not hit:
        return "bad", [("-", "the ctx-takeover loader printed no character count; "
                             "its last line has changed shape and case-lint needs updating")], \
               "re-read scripts/takeover-load.py and update the parse here"
    n = int(hit.group(1).replace(",", ""))
    if n > 15000:
        return "bad", [("-", "%s characters — red" % format(n, ","))], \
               "slim it before the case changes hands: old C rows into the decision " \
               "appendix, delivered E rows into the experiment archive, settled D rows deleted"
    if n > 10000:
        return "warn", [("-", "%s characters — yellow" % format(n, ","))], \
               "slim it at the next close-out (red starts at 15,000)"
    return "ok", [("-", "%s characters — green" % format(n, ","))], ""


def check_e_cell_length(path, rules):
    """2. Verdict / Impact cells over the cap, measured by the block ctx-handoff owns.

    That block reads only the rows a takeover reads — the live ones plus the newest
    delivered one — so a library full of old delivered rows no longer reports cells
    nobody will ever load. Change the scope in the skill and this reading follows.
    """
    try:
        out = run_py_block(rules.handoff, ["ctx-handoff", path])
    except Exception as exc:
        return "bad", [("-", "the ctx-handoff length block failed on this file: %s" % exc)], ""
    lines = [l for l in out.split("\n") if l.strip()]
    if not lines:
        return "bad", [("-", "the ctx-handoff length block printed nothing; "
                             "its output has changed shape and case-lint needs updating")], ""
    total = CELL_TOTAL_RE.match(lines[-1])
    if not total:
        return "bad", [("-", "the ctx-handoff length block no longer ends in a total line; "
                             "its output has changed shape and case-lint needs updating")], ""
    limit = int(total.group("limit"))
    items = []
    for line in lines[:-1]:
        hit = CELL_DETAIL_RE.match(line)
        if not hit:
            continue
        n = int(hit.group("n"))
        items.append((hit.group("line"),
                      "[%s] %d chars, %d over" % (excerpt(hit.group("col"), 24), n, n - limit)))
    if len(items) != int(total.group("n")):
        return "bad", [("-", "the ctx-handoff length block reported %s cells but printed %d "
                             "readable ones; its output has changed shape and case-lint "
                             "needs updating" % (total.group("n"), len(items)))], ""
    items.sort(key=lambda t: int(t[0]))
    fix = "put one sentence of verdict in the cell (%d characters at most) and the path to " \
          "the deliverable beside it — the account belongs in the results section of that " \
          "deliverable, and the row only points at it" % limit
    return ("bad" if items else "ok"), items, fix


def check_e_status(path, lines):
    """3. Status cells outside the six words."""
    span = sections(lines).get("E")
    if not span:
        return "n/a", [], ""
    rows = table_rows(lines, span)
    if not rows:
        return "n/a", [], ""
    header = split_cells(rows[0][1])
    col = column_of(header, r"状态|status")
    fix = "the status cell takes one of the six words only — %s; a verdict " \
          "(通过 / 部分达成 / 已停 / 移交 …) belongs in the verdict cell, and a row " \
          "worded otherwise is read as neither live nor finished and drops out of " \
          "every takeover" % STATUS_WORDS
    if col < 0:
        return "bad", [(rows[0][0], "no status column in the E header — every takeover "
                                    "falls back to \"last 3 rows, scan by hand\"")], fix
    items = []
    for ln, text in rows[2:]:
        cells = split_cells(text)
        if len(cells) != len(header):
            continue  # column count is off: position means nothing here, check 6 has it
        cell = cells[col] if col < len(cells) else ""
        if not cell:
            items.append((ln, "status cell is empty"))
        elif not STATUS_RE.match(cell):
            items.append((ln, "status reads \"%s\"" % excerpt(cell, 40)))
    return ("bad" if items else "ok"), items, fix


def check_d_struck(path, lines):
    """4. To-dos struck through or marked done instead of deleted."""
    span = sections(lines).get("D")
    if not span:
        return "n/a", [], ""
    rows = table_rows(lines, span)
    if not rows:
        return "n/a", [], ""
    items = []
    for ln, text in rows[2:]:
        cells = split_cells(text)
        if not cells:
            continue
        first = cells[0]
        if "~~" in first:
            items.append((ln, "id cell struck through: \"%s\"" % excerpt(first, 40)))
        elif D_DONE_RE.search(first):
            items.append((ln, "id cell marked done: \"%s\"" % excerpt(first, 40)))
    fix = "a settled to-do is deleted, not struck through — the row still costs every " \
          "successor the whole of its own text; move the account into the chronicle (F) " \
          "and delete the row"
    return ("bad" if items else "ok"), items, fix


def check_inbox_disposal(path, lines):
    """5. Disposition cells no skill will read as disposed."""
    span = sections(lines).get("I")
    if not span:
        return "n/a", [], ""
    rows = table_rows(lines, span)
    if not rows:
        return "n/a", [], ""
    header = split_cells(rows[0][1])
    col = column_of(header, r"处置|disposition")
    fix = "write the disposition opening with 已办 / 不办 / 已转 (done / dropped / " \
          "moved to) — the rule reads the opening and nothing else, so a cell worded " \
          "any other way never sweeps out and keeps its place in every future slice"
    if col < 0:
        return "bad", [(rows[0][0], "no disposition column in the inbox header — every "
                                    "takeover loads the whole inbox in full")], fix
    items = []
    for ln, text in rows[2:]:
        cells = split_cells(text)
        if len(cells) != len(header):
            continue  # column count is off: check 6 has it, the cell here is a fragment
        cell = cells[col] if col < len(cells) else ""
        if cell and not DISPOSAL_RE.match(cell):
            items.append((ln, "disposition reads \"%s\"" % excerpt(cell, 40)))
    return ("bad" if items else "ok"), items, fix


def tables(lines):
    """[(header line, header width, [(line, cell count, is delimiter), ...]), ...]."""
    found, current = [], None
    for ln, text in strip_fenced(lines):
        if not text.lstrip().startswith("|"):
            current = None
            continue
        cells = split_cells(text)
        if current is None:
            current = (ln, len(cells), [])
            found.append(current)
            continue
        current[2].append((ln, len(cells), is_delimiter(text) and ln == current[0] + 1))
    return found


def check_table_columns(path, lines):
    """6. Rows out of step with their header row."""
    items = []
    for header, width, rows in tables(lines):
        body = [r for r in rows if not r[2]]
        off = [r for r in body if r[1] != width]
        for ln, n, _ in [r for r in rows if r[2] and r[1] != width]:
            items.append((ln, "delimiter row has %d cells, header (line %d) has %d"
                          % (n, header, width)))
        if body and len(off) == len(body) and len(off) > 1:
            # every row is off: say so once, and name only the rows that differ from the rest
            counts = {}
            for _, n, _d in off:
                counts[n] = counts.get(n, 0) + 1
            mode = max(sorted(counts), key=lambda n: counts[n])
            items.append((off[0][0], "lines %d-%d: all %d rows are off the header (line %d "
                                     "declares %d cells), %d of them at %d — the header row is "
                                     "the one short of a column"
                          % (off[0][0], off[-1][0], len(off), header, width, counts[mode], mode)))
            off = [r for r in off if r[1] != mode]
        for ln, n, _ in off:
            items.append((ln, "%d cells, header (line %d) has %d" % (n, header, width)))
    items.sort(key=lambda t: t[0])
    fix = "escape every pipe inside a cell as `\\|` — an unescaped one puts every column past " \
          "it out of step, and a takeover reads that row as malformed and loads it whole; where " \
          "a whole table is off, the header row is the one missing a column"
    return ("bad" if items else "ok"), items, fix


# ---------------------------------------------------------------- the repository a case lives in

_TOPLEVEL = {}


def git_toplevel(directory):
    """The repository `directory` belongs to, or None if it belongs to none.

    Asked of the directory the case file is in, never of the working directory: a case library
    kept as its own private repository nested inside a public one is the ordinary shape, and
    the outer repository knows nothing about what the inner one has on its books. `git status`
    run in the outer one comes back clean whatever the inner one is carrying.
    """
    directory = os.path.abspath(directory)
    if directory in _TOPLEVEL:
        return _TOPLEVEL[directory]
    top = None
    try:
        got = subprocess.run(["git", "-C", directory, "rev-parse", "--show-toplevel"],
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                             universal_newlines=True, timeout=20)
        if got.returncode == 0 and got.stdout.strip():
            top = got.stdout.strip()
    except (OSError, subprocess.SubprocessError):
        top = None
    _TOPLEVEL[directory] = top
    return top


def untracked(top, paths):
    """Which of `paths` this repository does not have on its books, in the order given."""
    if not paths:
        return []
    try:
        got = subprocess.run(["git", "-C", top, "ls-files", "--error-unmatch", "--"] + paths,
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                             universal_newlines=True, timeout=30)
    except (OSError, subprocess.SubprocessError):
        return []  # git itself is unusable: say nothing rather than report a false finding
    if got.returncode == 0:
        return []  # every one of them is tracked, in one call
    if len(paths) == 1:
        return list(paths)
    out = []
    for one in paths:  # the call above stops at the first miss, so name them one at a time
        out += untracked(top, [one])
    return out


def cited_archives(path, lines):
    """[(file name, first line it is named on)] for the archives this case points at.

    An archive is a file beside the case whose name starts with the case file's own name —
    `<case>_decision-archive_<date>.md` and its two siblings, and anything else a project
    splits off the same way. Cited = its name appears somewhere in the case text: a file
    sitting in the directory that the case never mentions is not this case's to answer for.
    """
    directory = os.path.dirname(os.path.abspath(path))
    here = os.path.basename(path)
    stem = here[:-3]
    try:
        beside = sorted(os.listdir(directory))
    except OSError:
        return []
    found = []
    for name in beside:
        if name == here or not name.endswith(".md") or not name.startswith(stem + "_"):
            continue
        for n, line in enumerate(lines, 1):
            if name in line:
                found.append((name, n))
                break
    return found


def check_archives_tracked(path, lines):
    """7. The archives a case cites, checked against the books of the repository it lives in.

    Slimming a case moves rows verbatim into an archive file and leaves a pointer behind. Until
    that file is committed the pointer leads nowhere for anybody but this machine, and the
    move has quietly deleted the rows. Measured in this project's own books on 2026-09-08:
    three archive files cited in full by their cases had never been added at all.
    """
    directory = os.path.dirname(os.path.abspath(path))
    cited = cited_archives(path, lines)
    fix = "`git add` it in the repository the case file is in and commit it — until then the " \
          "pointer in the case leads nowhere for anybody else, and the rows it points at were " \
          "moved out of the case and are on no other copy. A clean `git status` in an outer " \
          "repository says nothing about a case library nested inside it"
    if not cited:
        return "ok", [("-", "no archive file is cited by name")], ""  # nothing to ask git about
    top = git_toplevel(directory)
    if not top:
        return "skip", [("-", "not inside a git repository — nothing to check against")], ""
    if untracked(top, [os.path.abspath(path)]):
        return "skip", [("-", "the case file itself is not on this repository's books "
                              "(%s) — a library kept outside git is a legitimate shape" % top)], ""
    missing = set(untracked(top, [os.path.join(directory, n) for n, _ in cited]))
    items = [(n, "%s is cited here but is not on the books of %s" % (name, top))
             for name, n in cited if os.path.join(directory, name) in missing]
    if items:
        return "bad", items, fix
    return "ok", [("-", "%d cited archive%s, all tracked in %s"
                   % (len(cited), "" if len(cited) == 1 else "s", top))], ""


def header_line(lines):
    """The case's header line: the first line above section A carrying a pen-holder field."""
    for i, line in enumerate(lines):
        if SECTION_RE.match(line):
            return -1, ""
        if PEN_FIELD_RE.search(line):
            return i + 1, line
    return -1, ""


def check_pen_holder(path, lines):
    """8. The pen-holder cell, and the stint number a title in it carries (report only).

    A delivery from another case is addressed off this cell, and a successor takes its own
    stint number off the `stint` field beside it (ctx-takeover §3). Both are written by hand,
    so this says what looks off and fixes nothing — the cell belongs to whoever holds the pen.
    """
    fix = "the pen-holder cell holds either a session title in the current form " \
          "`C<case><stint> <short name>-<what this stint does>` (中文同形), or one of the " \
          "stand-ins — (TBD) / (closed <date>) / (successor to fill in; predecessor … " \
          "retired) / a role where the title tool was unavailable; the `stint` field beside " \
          "it carries the same number the title does"
    ln, line = header_line(lines)
    if ln < 0:
        first = next((i + 1 for i, l in enumerate(lines) if l.strip()), 1)
        return "warn", [(first, "no pen-holder field on the header line — a delivery from "
                                "another case has no address to read")], fix
    cell = PEN_FIELD_RE.search(line).group(1).strip()
    cut = HEADER_FIELD_RE.search(cell)
    if cut:
        cell = cell[:cut.start()].strip()
    cell = cell.split("|")[0].strip()
    if not cell:
        return "warn", [(ln, "the pen-holder cell is empty — write (TBD) where nobody "
                             "holds it yet, so an empty cell is never read as an oversight")], fix
    if PEN_PLACEHOLDER_RE.match(cell):
        return "ok", [("-", "pen-holder: %s" % excerpt(cell, 40))], ""
    new = PEN_TITLE_NEW_RE.match(cell)
    if not new and not PEN_TITLE_OLD_RE.match(cell):
        return "warn", [(ln, "the pen-holder title is in neither naming form: \"%s\""
                         % excerpt(cell, 40))], fix
    if new:
        said = STINT_FIELD_RE.search(line)
        if not said:
            return "warn", [(ln, "the title says stint %s, and the header line has no "
                                 "stint field to take the next one from" % new.group(2))], fix
        if int(said.group(1)) != int(new.group(2)):
            return "warn", [(ln, "the stint field says %s, the pen-holder's title says %s — "
                                 "the next successor would reuse a number"
                             % (said.group(1), new.group(2)))], fix
    return "ok", [("-", "pen-holder: %s" % excerpt(cell, 40))], ""


# ---------------------------------------------------------------- running and reporting

def lint_file(path, rules):
    with io.open(path, encoding="utf-8") as fh:
        lines = fh.read().split("\n")
    got = sections(lines)
    if len(got) < 3:
        return None  # not a case file: no A~I structure to check
    return [
        (CHECK_NAMES[0],) + check_takeover_load(path, rules),
        (CHECK_NAMES[1],) + check_e_cell_length(path, rules),
        (CHECK_NAMES[2],) + check_e_status(path, lines),
        (CHECK_NAMES[3],) + check_d_struck(path, lines),
        (CHECK_NAMES[4],) + check_inbox_disposal(path, lines),
        (CHECK_NAMES[5],) + check_table_columns(path, lines),
        (CHECK_NAMES[6],) + check_archives_tracked(path, lines),
        (CHECK_NAMES[7],) + check_pen_holder(path, lines),
    ]


BADGE = {"ok": "ok  ", "warn": "WARN", "bad": "FAIL", "n/a": "--  ", "skip": "--  "}


def render(path, results, terse=False):
    """terse = only what is wrong, for a hook that has to be cheap to be tolerated."""
    out = ["=== %s ===" % path]
    for name, status, items, fix in results:
        if terse and status != "bad":
            continue
        if status == "n/a":
            out.append("  %s  %-18s no such section" % (BADGE[status], name))
            continue
        if not items:
            out.append("  %s  %-18s clean" % (BADGE[status], name))
            continue
        if len(items) == 1 and items[0][0] == "-":
            out.append("  %s  %-18s %s" % (BADGE[status], name, items[0][1]))
            if fix and status != "ok":
                out.append("        -> %s" % fix)
            continue
        out.append("  %s  %-18s %d finding%s"
                   % (BADGE[status], name, len(items), "" if len(items) == 1 else "s"))
        for ln, note in items:
            out.append("        line %-5s %s" % (ln, note))
        if fix:
            out.append("        -> %s" % fix)
    return "\n".join(out)


def collect(target):
    if os.path.isdir(target):
        found = sorted(os.path.join(target, n) for n in os.listdir(target)
                       if is_case_file(os.path.join(target, n)))
        return found, []
    if os.path.isfile(target):
        if not is_case_file(target):
            return [], ["%s is an archive or the board, not a case file — nothing checked" % target]
        return [target], []
    return [], None  # unreadable


def main(argv=None):
    ap = argparse.ArgumentParser(
        prog="case-lint.py", add_help=True,
        description="Health check for case files: eight rules the docs state, checked in one run.")
    ap.add_argument("target", help="a case file, or a case library directory")
    ap.add_argument("--quiet", action="store_true",
                    help="print nothing unless something is wrong (for hooks)")
    ap.add_argument("--skills", metavar="DIR", default=None,
                    help="read the two rule blocks from this skills directory")
    args = ap.parse_args(argv)

    skills_dir = find_skills_dir(args.skills)
    if not skills_dir:
        sys.stderr.write("case-lint: cannot find skills/ctx-handoff/SKILL.md; "
                         "pass --skills <dir>\n")
        return 2
    try:
        rules = Rules(skills_dir)
    except (IOError, OSError, RuntimeError) as exc:
        sys.stderr.write("case-lint: %s\n" % exc)
        return 2

    files, notes = collect(args.target)
    if notes is None:
        sys.stderr.write("case-lint: cannot read %s\n" % args.target)
        return 2
    if not files and not notes:
        sys.stderr.write("case-lint: no case files under %s\n" % args.target)
        return 2

    blocks, files_seen = [], []
    bad_checks, warn_checks, ok_checks, findings = 0, 0, 0, 0
    for path in files:
        try:
            results = lint_file(path, rules)
        except (IOError, OSError, UnicodeDecodeError) as exc:
            sys.stderr.write("case-lint: cannot read %s: %s\n" % (path, exc))
            return 2
        if results is None:
            notes.append("%s has no A~I sections — not a case file, nothing checked" % path)
            continue
        here = 0
        for _, status, items, _ in results:
            if status == "bad":
                bad_checks += 1
                here += 1
                findings += len(items)
            elif status == "warn":
                warn_checks += 1
            elif status == "ok":
                ok_checks += 1
        files_seen.append(path)
        if args.quiet and not here:
            continue  # a hook is only worth having if a clean file costs nothing to read
        blocks.append(render(path, results, terse=args.quiet))

    if args.quiet and not bad_checks:
        return 0

    report = "\n\n".join(blocks)
    tail = "--- %d checks clean, %d with findings (%d finding%s over %d file%s)" % (
        ok_checks, bad_checks, findings, "" if findings == 1 else "s",
        len(files_seen), "" if len(files_seen) == 1 else "s")
    if warn_checks:
        tail += ", %d yellow" % warn_checks
    tail += " ---"
    text = "\n\n".join([b for b in (report,) if b] + notes + [tail])
    sys.stdout.write(text + "\n")
    return 1 if bad_checks else 0


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    sys.exit(main())
