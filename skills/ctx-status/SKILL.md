---
name: ctx-status
description: Report status — use on "what's the status", "where do things stand", "show the board", or /ctx-status; reads the board and case files, reports goal chain, case states, pending decisions and one-offs in plain language. Also triggers on Chinese — 用户说"现在什么情况""进展如何""有哪些案""资产都在哪""看一下板"，或显式 /ctx-status 时用。
---

# Status: board → cases → a plain-language report

> **Speak in the user's language, and write the board / case files / inbox rows in the user's language.** Status words and section letters are fixed bilingual, so a board or case written in either language must be readable by this skill. Section letters A~I never change. Status words used here: **running** (在跑) / **awaiting acceptance** (待验收) / **awaiting decision** (候拍); header-line fields `status` (状态) / `pen-holder` (持笔) / `updated` (更新).

## 1. What to read (only these — no transcripts, no bodies of deliverables)
- **The board** (`TASKBOARD.md` inside the case library — the library is **resolved in this order: the path on the line `ctx-kit case library: <path relative to the project root>` in the project root's `CLAUDE.md` if there is one, otherwise an existing `_ops/CASES/`, otherwise `cases/`**; project root = the git root if there is a `.git`, otherwise cwd, and the old location `_ops/TASKBOARD.md` is the last fallback): the goal chain in the header + the case index + the one-off area. No board → read the file list of the case directory instead, and suggest "a board would help".
- **For every active case**: the header line (status / pen-holder / updated date) + **the Measurable line of section A (the number or condition that counts as done)** + **every row of section D** (D holds open items only: a decided row has moved into C, a done row has been deleted). When there are many cases, expand only the ones the user names and give the rest one line each.

## 2. Report format (four fixed sections, plain language)
1. **Goal chain**: the product top-level goal in one sentence + one line per track (milestone / goal / status);
2. **Where each case stands**: case number + plain-language name | who holds the pen | latest reading | the top open item (waiting on whom);
3. **Waiting on the owner**: **report every row of section D of every case as awaiting decision** — a row still standing in D is open by definition (`ctx-kickoff` §2: decided rows move to C, done rows are deleted) — one sentence each plus a recommendation. Do not filter on the wording of the row: a row still standing in D is still waiting on the owner, whatever it is labelled. An older case may still carry struck-through rows (`~~like this~~`) or rows already moved into C: treat those as closed, and say in one line that the case wants tidying;
4. **One-offs and what is running**: the board's one-off area + the rows in each case's E ledger whose status is running / awaiting acceptance.

## 3. Discipline
- Report only numbers that are on the board. Where a case has no number yet, say **"no measurement yet"** — **never guess, and never quote a stale status out of a transcript**.
- Board and case disagree → report both sides and mark it "needs reconciling"; do not quietly side with one of them.
- The first answer must not run past one screen; read deeper only when the user names a case or an item.
- Stop when the report is done, do not append a list of suggestions (the user will ask if they want them).
