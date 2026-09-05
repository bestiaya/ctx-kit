---
name: ctx-init
description: Initialize a project board — use on "new project", "set this project up", "what is this project for", or /ctx-init; reads the project's own docs first, proposes goal and milestones with a source cited per cell, writes nothing until you confirm, then lays down the board header. Also triggers on Chinese — 用户说"新项目开工""这项目开始了""先把项目定下来""项目是干啥的先写下来"，或显式 /ctx-init 时用。
---

# Kick-off: read → propose → confirm → write

> **Speak in the user's language, and write the board / case files / inbox rows in the user's language.** Status words and section letters are fixed bilingual, so a board written in either language must be readable by this skill. Board section names: `## Goal` (总目标) / `## Milestones` (里程碑) / `## Routines` (例行) / `## Cases on the books` (在册案) / `## One-offs` (散活); header-line fields `status` (状态) / `pen-holder` (持笔) / `updated` (更新). **The milestone table's status vocabulary is four words and only four**: **reached** (已达) / **running** (在跑) / **not started** (未起) / **on hold** (挂起). A case row on the board carries that case's own header-line status instead — **in discussion** (讨论中) / **queued** (排队) / **running** (在跑) / **awaiting decision** (候拍) / **awaiting acceptance** (待验收) / **awaiting takeover** (候接手) / **closed** (已收口) — and the full list sits at the top of `ctx-kickoff` and `ctx-takeover`.

The overview = the header of `TASKBOARD.md` inside the case library, in three zones: **top-level goal + milestone table + routine table**. Every case's R field in section A and every one-off's milestone tag hangs off it — without it, nothing that comes later has anything to hang on.

**A milestone is a tag, not a tier above the case**: one row = one sentence of "what is true once it is reached" + a status. A case or a one-off tags one or more of them, and one milestone carries as many cases as it likes; it settles no approvals, moves no pen and opens no second set of books. A job that matches none of them is tagged `candidate milestone: <one line>` and put to the owner, who decides whether to add a plan row or stop the job.

**A routine is a job with no finish line** (shipping releases, the weekly checkup, running the accounts): one row = cadence + health reading + last / next. It has no end state and keeps no ledger, so it is not a case that never closes; when a routine run hits something that needs converging, *that* is when a case gets opened for it.

## 0. Locate (nothing written)
Same rules as `ctx-kickoff` §0: **project root** = the git root if there is a `.git`, otherwise cwd; **the case library is only ever looked for inside the project root**, **resolved in this order: the path on the line `ctx-kit case library: <path relative to the project root>` in the project root's `CLAUDE.md` if there is one, otherwise an existing `_ops/CASES/`, otherwise `cases/`**.

When there is no such line and neither default exists, **glob `*/TASKBOARD.md` and `*/*/TASKBOARD.md` once inside the project root first** — the project may keep its case library elsewhere; if you find an existing board, use it, do not start a second one beside it.

**An existing `TASKBOARD.md` → review mode**: read it and take it as the baseline, and **raise only the differences** (which cell disagrees with the docs, which cell is empty, which milestone's or routine's status is stale); do not tear it down and rebuild, do not rewrite cells that have not changed. **A board still carrying the old section names** — `## Global plan` / `## 全局计划`, and the `tracks` / `线` layer under it — **is one of those differences: propose renaming the sections to `## Milestones` (里程碑) and `## Routines` (例行), and keep the rows underneath exactly as they stand** — a rename, never a rebuild; like every other proposal it goes in the step-2 table and not one character is written before the user confirms (§3). No board → new-build mode, run everything below.

## 1. Read the material (measure first, then read)
The candidates are only these: `README*` / `CLAUDE.md` / `docs/` at the project root plus the `*.md` files one level inside the root; package manifests (`package.json`, `pyproject.toml`, `Cargo.toml` and the like) — **read name + description only**; `git log --oneline | head -30`; two levels of the directory tree.

**Run `LC_ALL=en_US.UTF-8 wc -m` on every file before deciding whether to read it**: any single file >30k characters, or >60k characters in total (`wc -m` counts characters and `wc -c` counts bytes — a Chinese document runs about twice its character count in bytes, and counting the bytes is what made this check fire on the wrong side once; run it in a UTF-8 locale, because under `LC_ALL=C` even `wc -m` counts bytes; the denominator = the sum of `wc -m` over the whole candidate set — measure them all before deciding what to read; you may not pick a few first and add up only those) → **dispatch the `ctx-kit:digest` subagent to digest them and let the main context take the summary only** (under a manual install the subagent is named `digest`). Reading everything without measuring first is the easiest mistake to make at this step.

Do not read: session transcripts (`*.jsonl`), private directories outside the case library, `.env` or any credential file.

## 2. Propose (not one character on disk)
Give the user one table, five blocks. **In review mode all five blocks are given anyway**, with each cell prefixed 「matches / differs / empty」: cells marked 「matches」 carry only the current value and its source and are not expanded; step 3 only asks about cells marked 「differs」, 「empty」 or 「you tell me」.
1. **Three questions about the top-level goal**: what is the final thing to get / who is it for / what counts as done;
2. **Milestone list**: one row each, **worded as a result — "what is true once it is reached", not "what we will be working on"** — plus a status (reached / running / not started / on hold). These are top-down guesses to open with, and the jobs that actually get done correct them from the bottom up later; **correction is the normal case, not a failed plan**, so three to six rough milestones beat ten precise ones;
3. **Routine list**: the jobs with no finish line, one row each — cadence + the health reading that says it is going well + last / next;
4. **Case library location and prefix**: for a public repo suggest `_internal/` + `.gitignore`, or a private nested repo; for a private project `_ops/CASES/`; add the case-number prefix (initials of the project name) and the session-title prefix;
5. **The items you cannot read out.**

**Cite a source in every cell**: name the file and the section it came from (e.g. `README.md §2`), or say plainly "my inference". For anything you cannot read out, write **"you tell me"** — **never make it up**: get one cell of the top-level goal wrong and every case after it hangs off the wrong milestone.

## 3. Ask one round only
> **Run your eye down this table cell by cell — which is right, which to change, and fill in the "you tell me" ones.**

Ask nothing else (do not ask whether to create it, do not ask about the format, do not ask about priority). **Nothing is written before the user confirms**: no directory created, no file touched, no half-written draft. What you are waiting for is one confirmation, not step-by-step authorisation.

## 4. Write once confirmed
Create the case library directory if it does not exist; write / update the header of `<case library>/TASKBOARD.md`. **Read the target absolute path back to the user before writing** (the hard rule in kickoff §0: a case file must never be written into a different project).

Copy the format below exactly — `ctx-status` / `ctx-kickoff` / `ctx-takeover` read precisely this:

```markdown
# <project name> board

updated: <today>

## Goal

**<top-level goal in one sentence>.** <who it is for and what counts as done, two or three sentences>

## Milestones

> A milestone is a tag, not a tier above the case: each row is one sentence of "what is true once it is reached" plus a status; a case or a one-off tags one or more of them, and anything that matches none is tagged "candidate milestone".

| # | What is true once it is reached | Status | Who is pushing it |
|---|---|---|---|
| M1 | <what is true once this one is reached, one sentence> | **<reached / running / not started / on hold>** — <current state in one sentence> | (no case yet) |

## Routines

| Routine | Cadence | Health reading | Last / next |
|---|---|---|---|
| <the job that just keeps running> | <weekly / one per release / …> | <the number that says it is going well> | <last: …; next: …> |

## Cases on the books

| Case | Name | Milestone | Status | Pen-holder | Where it is | Next step |
|---|---|---|---|---|---|---|

(None yet. Open the first one with ctx-kickoff.)

## One-offs

(None yet. A one-off on the board must name the milestone it pushes; if it matches none, write `candidate milestone: <one line>`, tell the owner, and let them decide whether to add a plan row or stop the job.)
```

**The Status column of the milestone table takes one of the four status words** — `reached` / `running` / `not started` / `on hold` — followed by a dash and one sentence of current state; nothing else goes in that cell, because `ctx-status` counts the milestones by these words. The Status column of 「Cases on the books」 is a different vocabulary: it mirrors that case's own header-line status (`in discussion`, `awaiting decision`, `closed` …), listed at the top of `ctx-kickoff`.

The section names and table headers are **not to be changed by one character** (`## Goal` / `## Milestones` with `# | What is true once it is reached | Status | Who is pushing it` / `## Routines` with `Routine | Cadence | Health reading | Last / next` / `## Cases on the books` with its **seven** columns / `## One-offs`) — change them and the three downstream skills cannot read the board. For a Chinese-speaking user write the Chinese names given in the note at the top of this skill; either language is fine, mixing them is not. Review mode only edits the cells that differ and leaves every other line alone.

**The board is maintained by hand — it is nobody's projection.** You and the owner write the header (goal / milestones / routines) here at kick-off and edit a line whenever it changes; from then on each case edits its own row of the case index and touches no other. A generator script is optional; where a project has one, whatever that script writes is not hand-edited as well.

If the case library is somewhere other than the default (a public repo that keeps its cases outside the published tree, say), **tell the user to add one line to the project root's `CLAUDE.md` themselves, in exactly this format** — `ctx-kit case library: docs/cases` — the marker `ctx-kit case library:` written character for character, then the path **relative to the project root**, one line of its own, nothing else on it. That line is what all six skills read to find the library (§0), so without it every session has to be handed the path by hand. **Do not edit `CLAUDE.md` for them** — quote the line and let them paste it.

## 5. Closing three lines
1. the top-level goal in one sentence;
2. how many milestones (reached / running / not started / on hold) and how many routines;
3. the absolute path of the overview.

One last sentence: **you can name the first job now (ctx-kickoff).**
