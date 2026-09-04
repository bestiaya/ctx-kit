---
name: ctx-kickoff
description: Triage and open a case — use on "I want to do X", "plan this", "start a new job", "note this down", "save this for later", or /ctx-kickoff; routes to case / one-off / quick-fix, creates the case file on the spot, parks to-dos where they belong, then asks one question — discuss here or dispatch. Also triggers on Chinese — 用户说"我要做 X""帮我规划 X""开个新活""这事怎么搞"，说"记一下""先存着""保存这个任务""回头再做"要存待办，或显式 /ctx-kickoff 时用。
---

# A new job: triage → open a case → pick the carrier

> **Speak in the user's language, and write the case file / board / inbox rows in the user's language.** Status words and section letters are fixed bilingual, so a case written in either language must be readable by every skill here. Header-line fields: `status` (状态) / `pen-holder` (持笔) / `updated` (更新). Status words used here: **in discussion** (讨论中) / **queued** (排队) / **running** (在跑) / **awaiting acceptance** (待验收). Section letters A~I never change; the section names are bilingual and given in §2.

## 0. The case library (fix the project root first, then the library)
**Project root** = the repository root the current working directory sits in (the git root if there is a `.git`, otherwise cwd). **The case library is only ever looked for inside the project root**, and it is **resolved in this order: the path on the line `ctx-kit case library: <path relative to the project root>` in the project root's `CLAUDE.md` if there is one, otherwise an existing `_ops/CASES/`, otherwise `cases/`** (create it if absent). Every skill here resolves it the same way, so a project that keeps its cases somewhere else says so once, in that one line, instead of being told the path session by session. The board = `TASKBOARD.md` inside the case library (create it if absent: header = product top-level goal + global plan + one line per track, followed by the case index and the one-off area).

**Hard rule: a case file must never be written into a different project** — read the target **absolute path** back to the user before writing. Measured, and it went wrong once: a session in a throwaway project wrote three personal-admin files into the main project's case library, numbered them off the main project's sequence, and rode along into the main project's git.

**Case number = `<prefix>-NN`**: the prefix is per project (the main project keeps its existing letter; another project takes the initials of the project name, and only has to avoid clashing with an existing prefix), and **NN increments independently inside this project's case library, never looking at another project's numbers**.

## 1. Triage (decide it yourself, do not ask the user)
| Signal | Route |
|---|---|
| Needs discussion, needs several rounds of experiment, needs a ruling | **Open a case** (step 2) |
| Executable in one pass, criteria are clear | **One-off**: no case; one row on the board (**"serves which milestone" is required** = which milestone of the goal chain it hangs off; if it hangs off nothing → list it separately for review and do not start it), plus a self-contained task brief |
| A quick fix (change a setting, change one line, answer a question) | **Just do it**, no case and no task brief |

When in doubt, open a case: opening one costs about two minutes, whereas the cost of not opening one is state rotting inside the session.

**All three routes owe one line of triage result** — decide and move on, but leave a hatch for correction: opening a case returns the three-line summary from step 2; a **one-off** returns "I triaged this as a one-off, because <one sentence>; it is on the board at row N, serving milestone <X>; say so if that is wrong"; a **quick fix** returns "I triaged this as a quick fix, because <one sentence>; doing it now; say so if that is wrong". Silently dispatching as a quick fix something that deserved a case leaves the user no chance to stop it.

## 2. Open the case (create the file on the spot, do not ask first and create later)
**Section heading format — `## A Goal`**: a capital letter, one space, then the section name (`## A Goal (目标)`, `## E Experiment ledger (实验台账)`). **Do not put a period after the letter** (`## A. Goal`), do not renumber and do not rename the letters — every skill here locates a section by that letter alone, so the letter is the only part of the heading that is load-bearing.
- Header line: `status: in discussion   pen-holder: (TBD)   updated: <today>`
- **A Goal (目标)**: write the five SMART elements (specific / measurable / achievable / relevant / time-bound) down hard, from your current understanding of the context, wording them as "my reading"; **do not leave it blank for the user to fill in**. Write relevance as two sentences: which product top-level goal it serves (pointing at the goal-chain milestone in the board header) + where it sits in the global plan.
- **B Current plan snapshot (当前方案快照)**: if you have an idea, describe the end state; if not, write "to be discussed".
- **C Decisions (已拍决策)**: empty. **D Open items & pending decisions (未决与候拍)**: hang up whatever you judge the user has to decide, each with a recommendation.
- **E Experiment ledger (实验台账)**: hang up the experiments you can already foresee (status = queued). **F Chronicle (编年志), G Archive pointers (档案指针; reference only), H Unsaved items (未落盘清单)**: create them empty (use exactly these section names, do not invent your own; **I Inbox (收件位)** is optional, create it only for cross-track collaboration).
- **The headers of tables D / E / I are fixed — copy them character for character**, all of them in one language and never mixed: every skill here finds a column by its header text, so a renamed or dropped column reads downstream as a missing column. Measured: one small case built by feel twice came out with a six-column ledger and an eight-column one.
  - **D**: `| # | Open item / decision needed | Note / recommendation |` (中文 `| # | 待办/待拍 | 说明 / 建议 |`)
  - **E**: `| ID | Question it answers | Task brief path | Carrier | Status | Delivery path | Verdict | Impact on plan |` (中文 `| ID | 要回答的问题 | 任务书路径 | 载体 | 状态 | 交货路径 | 判定 | 对方案的影响 |`)
  - **I**: `| Date | From | Message | Disposition |` (中文 `| 日期 | 来自 | 来话 | 处置 |`)
  - **E is an index, not a report**: the pre-registered criteria (reading before / expected reading / what counts as a fail) live in the task brief that the Task-brief-path cell points at, **not** in a column of E; with no brief written yet, that cell says `to be written`.
  - **An existing library whose older cases are shaped differently**: use the fixed headers for the case you are opening, **leave the older cases alone** (they belong to whoever holds their pen), and say so in one line, so the difference is on the record instead of a surprise for the next reader.
  - **D holds open items only**: a decision once made moves into C and its D row goes with it; an item once done has its row deleted (leave a line in F if it is worth remembering). **Do not strike rows through** — every row standing in D is open, and that is exactly what `ctx-status` reports to the owner as awaiting decision.
  - **The Disposition cell of I** decides whether a message is still waiting on somebody: empty = not disposed; **disposed** = the cell is non-empty and says what came of it, in whatever words the writer used (a cell that only says the work is in hand is not disposed). When you write one yourself, start it with `done` (已办) / `dropped` (不办) / `moved to <where>` (已转 <去处>) so the next reader can tell at a glance.
- **Register it on the board (the case is not open until this row exists)**: append one row to the 「Cases on the books」 (在册案) table of `<case library>/TASKBOARD.md` — case number / name / status / pen-holder / where it is / next step, e.g. `| C-07 | async vs streaming | in discussion | (TBD) | just opened, goal written | user to correct A and D |`. A freshly built board carries a `(None yet. Open the first one with ctx-kickoff.)` line under that table — delete that line when you add the first row. **Touch your own row and nothing else**: not the board header, not anybody else's row. A case that is not on the board is invisible to `ctx-status`, and its session shows up as an orphan in the retirement sweep at checkup.

Once it is built, reply with a **three-line summary**: the goal in one sentence / the key open item as you judge it in one sentence / the case file path. Ask the user to correct you — what the user changes is A and D, not the format.

## 3. Ask one question
> **Discuss it here, or dispatch it?**

Ask nothing else (do not ask whether to open a case, do not ask about naming, do not ask about priority).

### Branch A: discuss it here
1. `set_session_title` to `NN-<compact case number>-what-this-stint-does[-track]-role` (e.g. `07-C07-async-vs-streaming-decision-lead`): **NN increments inside this project and doubles as the time order** — sorting the sidebar by number gives this project's workflow in sequence, and it also prevents same-case name clashes for free, so there is no need for a separate "nth successor" (the session list you pull back is **every project mixed together**, so filter it down to this project by working directory first, then take the largest and add 1; if you cannot get it, leave it out — on a collision the later session renames); **compact case number** = the case number with the hyphen removed (`C-07`→`C07`), so a session is visibly filed to its case, and **a one-off has no case number, so the middle segment stays empty**; **the third segment says what this stint is doing, not the case name** — the case number already stands for the case, so the case name is a repeat, and one case spans several stints that are not doing the same thing; **the track short name is written only when the job name does not reveal the track**, and it is the short name of the track file, not a code; role = `lead` | `exec`; **no project prefix by default**, add a short one only on a genuine cross-project collision (`ck-04-C07-…`); after retirement close-out adds the `✕ ` prefix. If the tool is unavailable, skip this and say so;
2. put that name in the header line's "pen-holder"; **if the title tool was unavailable**, write the role and the reason instead — `lead (title tool unavailable)`, or `exec (title tool unavailable)` — and **never write a title you did not actually set**: whoever comes next checks the pen-holder against the live session list, and an invented name reads there as a live pen-holder nobody can find;
3. start talking, and hold to this: **write section C the moment a decision is made, rewrite section B the moment the plan changes** — do not wait for close-out.

### Branch B: dispatch it
Write a self-contained task brief (the case's A in one sentence + the relevant paragraphs of B **copied in** + pre-registered criteria: reading before / expected reading / what counts as a fail + the delivery path), put it on disk and hang it on an E row (status = queued). Then give the user an opening prompt they can copy straight across:

```
Read <task brief path> — read only that, and never read any old session transcript.
First action on starting: set_session_title to "<parent number>.<child index>-<compact case number>-<what this stint does>-exec" (e.g. `07.1-C07-load-test-batch-exec`; a one-off has no case number, so the middle segment stays empty; the child index increments inside the dispatcher — take the largest `<parent number>.x` already in the session list and add 1; if the board already names the dispatch, use that name). **Second action on starting: write that name back into the 「carrier」 cell of that job's row on the board (one-off row) or the carrier column of the case's E row** — fill in only your own cell. Leave it out and the board cannot tell whose you are; you appear in the register as an "orphan", and the retirement sweep at checkup may mark you dead while you are still working (one measured near-miss, survived only because that session happened to be warm).
**A dispatched session always uses the parent number plus a child index, never a fresh global number** — only the dispatcher hands out its own child numbers, so a collision is structurally impossible; the old "global max + 1" collides whenever two leads dispatch at the same time (it has collided twice in practice).
And change your row in the E table of <case file path> to status "running".
Execute against the pre-registered criteria in the task brief, writing to disk as you go; report a fail as a fail, do not dress it up.
Delivery = a machine-readable ledger + a summary for people, written into <delivery path> as both layers;
write back the E row (Status = awaiting acceptance / Delivery path / Verdict / one sentence in Impact on plan) — **the Verdict cell and the Impact-on-plan cell are each ≤200 characters**; E is an index, not a report, and detail belongs only in the results section of the deliverable. Stop when done, do not open a new topic.
```

Once dispatched, do not wait (anything over 15 minutes goes async). **Do not dispatch a subagent from here once this session is expensive (>150k)** — the cold tax of waiting = this session's watermark × 2.

## 4. Park a to-do (the other entry point)
**Trigger**: the user says "note this down", "save this for later", "save this task", "come back to it"; or you raised a to-do yourself and the user said "save it".

Do not open a case, do not start work, do not chase priority — **decide where it belongs first, then write it down, and there are only these four landing spots**:

| What the to-do is | Where it lands |
|---|---|
| ① A to-do belonging to the case you hold the pen on (something to decide, something to think through) | one row added to that case's **section D**, with **one sentence of your recommendation** |
| ② Belongs to the current case, and is something to execute | an **E row** of that case, status = `queued`, task brief path = `to be written` |
| ③ A standalone small job outside this case | a **one-off row on the board** (**"serves which milestone" is required** = which milestone of the goal chain it hangs off; if it hangs off nothing → list it separately for review and do not start it) |
| ④ Belongs to another case | **that case's inbox (section I)**, **append only**, never touch their body text; leave the Disposition cell empty — an empty disposition is what marks the row as still waiting on them |

If you cannot tell where it belongs, ask one question (this is the only follow-up allowed); do not stuff it somewhere yourself.

Once it has landed, **reply with one line saying where it went**: file path + which section / which row number (e.g. `_ops/CASES/C-07_xx.md:42 (section D)`). **Replying "noted" is not writing it down** — if the user cannot find it later, it was never noted.
