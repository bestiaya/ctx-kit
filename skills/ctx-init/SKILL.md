---
name: ctx-init
description: Initialize a project board — use on "new project", "set this project up", "what is this project for", or /ctx-init; reads the project's own docs first, proposes goal and milestones with a source cited per cell, writes nothing until you confirm, then lays down the board header. Also triggers on Chinese — 用户说"新项目开工""这项目开始了""先把项目定下来""项目是干啥的先写下来"，或显式 /ctx-init 时用。
---

# Kick-off: read → propose → confirm → write

> **Speak in the user's language, and write the board / case files / inbox rows in the user's language.** Status words and section letters are fixed bilingual, so a board written in either language must be readable by this skill. Board section names: `## Goal` (总目标) / `## Global plan` (全局计划) / `## Cases on the books` (在册案) / `## One-offs` (散活); header-line fields `status` (状态) / `pen-holder` (持笔) / `updated` (更新); status word used here: **running** (在跑).

The overview = the header of `TASKBOARD.md` inside the case library (top-level goal + global plan). Every case's R field in section A and every one-off's "serves which milestone" hangs off it — without it, nothing that comes later has anything to hang on.

## 0. Locate (nothing written)
Same rules as `ctx-kickoff` §0: **project root** = the git root if there is a `.git`, otherwise cwd; **the case library is only ever looked for inside the project root**, preferring an existing `<project root>/_ops/CASES/`, otherwise `<project root>/cases/`.

When neither of the two defaults exists, **glob `*/TASKBOARD.md` and `*/*/TASKBOARD.md` once inside the project root first** — the project may keep its case library elsewhere; if you find an existing board, use it, do not start a second one beside it.

**An existing `TASKBOARD.md` → review mode**: read it and take it as the baseline, and **raise only the differences** (which cell disagrees with the docs, which cell is empty, which milestone's status is stale); do not tear it down and rebuild, do not rewrite cells that have not changed. No board → new-build mode, run everything below.

## 1. Read the material (measure first, then read)
The candidates are only these: `README*` / `CLAUDE.md` / `docs/` at the project root plus the `*.md` files one level inside the root; package manifests (`package.json`, `pyproject.toml`, `Cargo.toml` and the like) — **read name + description only**; `git log --oneline | head -30`; two levels of the directory tree.

**Run `wc -c` on every file before deciding whether to read it**: any single file >30k characters, or >60k in total (the denominator = the sum of `wc -c` over the whole candidate set — measure them all before deciding what to read; you may not pick a few first and add up only those) → **dispatch the `ctx-kit:digest` subagent to digest them and let the main context take the summary only** (under a manual install the subagent is named `digest`). Reading everything without measuring first is the easiest mistake to make at this step.

Do not read: session transcripts (`*.jsonl`), private directories outside the case library, `.env` or any credential file.

## 2. Propose (not one character on disk)
Give the user one table, four blocks. **In review mode all four blocks are given anyway**, with each cell prefixed 「matches / differs / empty」: cells marked 「matches」 carry only the current value and its source and are not expanded; step 3 only asks about cells marked 「differs」, 「empty」 or 「you tell me」.
1. **Three questions about the top-level goal**: what is the final thing to get / who is it for / what counts as done;
2. **Milestone list**: how many are in flight / done / waiting to start, one status line each (a milestone = one row of the overview's "global plan");
3. **Case library location and prefix**: for a public repo suggest `_internal/` + `.gitignore`, or a private nested repo; for a private project `_ops/CASES/`; add the case-number prefix (initials of the project name) and the session-title prefix;
4. **The items you cannot read out.**

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

## Global plan

| # | Milestone | Status | Who is pushing it |
|---|---|---|---|
| 1 | <milestone in one sentence> | **running** — <current state in one sentence> | (no case yet) |

**Where we stand**: <which milestones are taken, where it is stuck now>

## Cases on the books

| Case | Name | Status | Pen-holder | Where it is | Next step |
|---|---|---|---|---|---|

(None yet. Open the first one with ctx-kickoff.)

## One-offs

(None yet. A one-off on the board must state "serves which milestone" — which milestone of the global plan above it hangs off; if it hangs off nothing, list it separately for review and do not start it.)
```

The section names and table headers are **not to be changed by one character** (`## Goal` / `## Global plan` with `# | Milestone | Status | Who is pushing it` / `## Cases on the books` / `## One-offs`) — change them and the three downstream skills cannot read the board. For a Chinese-speaking user write the Chinese names given in the note at the top of this skill; either language is fine, mixing them is not. Review mode only edits the cells that differ and leaves every other line alone.

If the case library is somewhere other than the default (a public repo using `_internal/`, say), **tell the user to add a line about it to the project `CLAUDE.md` themselves** — do not edit `CLAUDE.md` for them.

## 5. Closing three lines
1. the top-level goal in one sentence;
2. how many milestones (in flight / done / waiting to start);
3. the absolute path of the overview.

One last sentence: **you can name the first job now (ctx-kickoff).**
