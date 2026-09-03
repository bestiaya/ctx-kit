---
name: ctx-handoff
description: Close out and hand off — use on "close out", "wrap this up", "this session is too full", or /ctx-handoff; distills the discussion into a takeover-ready case file, persists unsaved artifacts, then retires this session. Also triggers on Chinese — 用户说"收口""关案""这个案完了""交接一下""这会话太肥了""换个新会话继续""退役这个会话"，或显式 /ctx-handoff 时用。
---

# Close-out: settle it into a case → retire

> **Speak in the user's language, and write the case file / board / inbox rows in the user's language.** Status words and section letters are fixed bilingual, so a case written in either language must be readable by every skill here. Section letters A~I never change. Status words used here: **closing (do not take)** (收口中(勿接)) / **awaiting takeover** (候接手) / **closed** (已收口) / **predecessor retired** (前任已退役) / **running** (在跑) / **awaiting acceptance** (待验收) / **queued** (排队) / **to dispatch** (待派) / **delivered** (已交货); header-line fields `status` (状态) / `pen-holder` (持笔) / `updated` (更新).

> **Trigger line**: this skill runs **only when the owner triggers it, or after the owner has explicitly agreed**. A session over the line (high watermark, batch boundary) gets **a reminder only, never a forced close-out** — report the current watermark reading in one line, ask in one line whether to close out, and **do not close out on your own initiative**. Closing out changes the header line, clears the track-owner slot, sets the retirement mark, commits and pushes; close out a session that is still in use and the user pays for a takeover all over again.

## 1. Claim first: which case do I hold?
Check in order: ① this session's title (the name set through `set_session_title`); ② whether the "pen-holder" cell in any case's header line in the case library carries this session's name or the first 8 of its UUID. **The case library is only ever looked for inside the current project root** (project root = the git root if there is a `.git`, otherwise cwd; the library is `_ops/CASES/` for preference, otherwise `cases/`) — **never claim a case out of another project's library, and never write files across into one**.

- A hit → **update mode** (2A); no hit → **first-build mode** (2B).
- **The first move in both modes**: change the header line to 『status: closing (do not take)』 and keep the pen-holder (you are still writing, and one pen per case still holds); in first-build mode write the header line with that status from the start.

## 2A Update mode (the case already exists)
- **Rewrite section B whole** into the current end state (the old version it replaces rolls into one line of F); do not patch it incrementally.
- **C / E / F are append-only**; never edit historical rows — rejected decisions stay too.
- **Re-sort D**: move what has been decided into C, add the new open items, each with a recommendation.
- **Re-list H** (not append): drop whatever from the previous H has since gone to disk, and keep only what is still unsaved right now.

## 2B First-build mode (no case file)
Propose `<prefix>-NN_case-name.md`: the prefix is per project (the main project keeps its existing letter, another project takes the initials of the project name), and **NN increments inside this project's case library — never carry on from another project's numbering** (measured, and it went wrong: a throwaway project's session carried on from the main project's numbers, and its files landed in the main project too). **Say the target absolute path aloud together with the name before creating it**; one confirmation is enough. Build all nine sections A~I (A Goal (目标) / B Current plan snapshot (当前方案快照) / C Decisions (已拍决策) / D Open items & pending decisions (未决与候拍) / E Experiment ledger (实验台账) / F Chronicle (编年志) / G Archive pointers (档案指针; reference only) / H Unsaved items (未落盘清单) / I Inbox (收件位) — I may be dropped when this track already has a track file, in which case incoming messages go to the track file).

## 2C Closing a case (the end state of a close-out, not a second procedure)
**Closing a case is one kind of close-out**: write B~H the normal way per 2A / 2B, then do these four extra steps.

**Trigger**: the owner says "close the case" or "this case is finished"; or, at close-out, you judge that the case's **section A goal has been met** — **in the second case ask first, and close only once the owner nods**; never close a case on your own initiative.

1. **Header line**: `status: closed   pen-holder: (closed <today>)   updated: <today>` — this does not use the "awaiting takeover / predecessor retired" pattern; once it is closed there is no successor.
2. **Hand the decisions up**: when the track this case belongs to **has a track file**, append **every row of table C verbatim** into that track file's 「decision archive」 section (or into that track's separate decision-archive file, if it has one), with nothing deleted or altered; **table C stays in the case exactly as it is** — handing up is copying, not moving. **With no track file, do nothing** and the decisions stay in the case.
3. **The board**: change this case's row in the 「cases on the books」 table to status `closed` and **move the whole row to the end of the table**. **Never create a new section such as "closed cases"** — the downstream skills read the board by section name, and one extra section makes them miss things.
4. Add one line to the **F chronicle**: `<date> case closed: <one sentence on why — goal met / dropped / merged into another case>`.

Stop there: **closing a case means only this, that nobody takes it over again** — do not delete the file, do not move the directory; the history stays where it can be looked up.

## 3. Hard rules
- **What a takeover actually loads: ≤10,000 characters is green, >15,000 must be slimmed** — the measure is "how much has to be read in to take it over once", not "up to E": run the extraction command in `ctx-takeover` §2 and read the number it reports on its last line. First choice for slimming = **hand the old rows of table C up to this track's decision archive as a block** (moved verbatim, with only the current batch + a pointer left in the case); then rolling old E rows into an archive (next rule), clearing settled items out of D, compressing the chronicle in F; if that is still not enough, promote the plan body into its own numbered document and leave only the top-level diagram + a pointer in section B.
- **Rolling E into an archive**: once E passes 5,000 characters or 30 rows, move the rows whose status is delivered and whose "what it changes in the plan" has already been written into B / C **verbatim** into `<case file name without .md>_experiment-archive_<date>.md` (same format as the decision appendix, headed "moved verbatim, nothing deleted or altered, stub kept in the case"), leaving one stub row each in the case: `ID | question | verdict in one sentence (≤80 characters) | archive pointer`. **Rows at running / awaiting acceptance / queued / to dispatch always stay in the case**, and so do delivered rows whose impact has not been written back into B / C — that account is still owed.
- **E row length check (report, do not fix)**: the verdict cell and the "what it changes in the plan" cell are each ≤200 characters, and the detail belongs only in the results section of the deliverable. Run it once before closing out; slim an over-long row on the spot if you wrote it, and report without touching it if somebody else did:

```bash
python3 - <path to this case file> <<'PY'
import sys,re
w=[]
for p in sys.argv[1:]:
    L=open(p,encoding='utf-8').read().split('\n')
    P=[i for i,l in enumerate(L) if re.match(r'^##\s+[A-Z]\.?(\s|$)',l)]+[len(L)]
    for n,i in enumerate(P[:-1]):
        if L[i].split()[1].rstrip('.')!='E': continue
        R=[(k+1,l) for k,l in enumerate(L[i:P[n+1]],i) if l.lstrip().startswith('|')]
        h=[c.strip() for c in R[0][1].strip().strip('|').split('|')] if R else []
        C=[x for x,c in enumerate(h) if re.search(r'判定|verdict|影响|impact',c,re.I)]
        for ln,l in R[2:]:
            c=[x.strip() for x in l.strip().strip('|').split('|')]
            w+=[(len(c[x]),f'{p}:{ln} [{h[x]}] {len(c[x])} chars') for x in C if x<len(c) and len(c[x])>200]
for n,s in sorted(w,reverse=True): print(s)
print(f'--- {len(w)} cells over 200 characters (reported, not fixed — the author slims their own) ---')
PY
```

- **Put unsaved artifacts on disk first** (drafts, scripts, tables, half-finished sums), and write the paths into E or H.
- **A running experiment must carry a liveness check (required)**: if any experiment is at status running / awaiting acceptance when you retire, **spell out the liveness command and where the artifacts land, both on the E row and in section H** (e.g. `check all six dispatch json files landed + pgrep -f <batch script> returns 0`). The successor checks the real state that way before reporting, instead of copying the status off the case. It has gone wrong once in practice: six sessions dispatched at 20:38, retirement at 20:51, and the case honestly said "running"; at 09:20 the next morning the successor reported "running, no readings" off the case, when in fact all of it had finished that same night — twelve hours wasted.
- **Write this session's jsonl path in section G as `(to be backfilled)`** — never use `ls -t` to look yourself up, which has been measured pointing at the wrong file (whoever accepts the work pairs it by billing timestamp and backfills it). List the other known archives and artifact directories as usual, marked "reference only, do not read in full".
- **Section H must be written into the case file itself**, not left only in the reply (close the window and it is gone). One line each, with the path to the detail; list them honestly and never drop one silently — **including what you did not finish, what you got wrong, and numbers that will not reproduce**.

## 4. The last four moves (only after B~H are written)
1. Change the header line: `status: awaiting takeover | pen-holder: (successor to fill in; predecessor <this session's name @first-8-of-UUID> retired) | updated: <today>`. **Never do it in the other order** — clearing the pen first hands the successor a half-closed case.
2. **Clear the track-owner slot**: if the track this case belongs to has a track file and the "track owner" cell is this session, change it to `(successor to fill in; predecessor <this session's name> retired)`. Leave it and a cross-track delivery finds a dead name on its first check, hollowing out the routing.
3. **Mark yourself retired**: `set_session_title` this session's title to `✕ <original title>` (a prefix, not a suffix — a suffix gets truncated out of sight in the list). This is the only naked-eye signal that a session is dead, and the first gate a cross-track delivery hits when it checks the address. If the tool is unavailable, say plainly in the reply that the mark was not set.
4. **Commit and push**: **you must commit and you must push** — measured: 15 days away from the machine, and a batch of commits sat on the local disk for 3 days, so **fixing only the commit does not fix it**.
   Run `git status` first: **another session may be open and editing other files, and `git add -A` will commit their half-written work along with yours** (this rule was hit the very first time it ran — two running sessions each had a half-edited case file). **`git add` only the paths you touched this round**, then `commit && push`.
   A non-git project, or a failed push (no remote / no permission / a conflict): **write "not pushed + why" plainly in the reply**; never skip it silently.

## 5. Reply: five sections for people first, then four items

**The five sections for people first** — one or two lines each, written for the owner:

- ① **Position and reason**: how far this case has pushed the top-level goal, and what this stint did;
- ② **What was verified, how it was tested, what counts as a pass**;
- ③ **Result**: the verdict first, expected vs actual;
- ④ **Conclusion**: what it means for the goal, which premise was confirmed or refuted, what is still unproven;
- ⑤ **The next step, derived from the conclusion** (every item awaiting decision carries a recommendation).

Numbers, station ids and reading codes stay out of the sections written for people; if you must hand something to the execution layer, put it on one line at the end.

**Then four items** (for the successor to take over with):

1. the case file path;
2. how many items are in section H + the most important one among them;
3. the status in one sentence;
4. **the successor's opening prompt** — its own code block, copyable whole into a new session:
```
/ctx-takeover C-NN
```
(In a bare environment with no skills installed, paste the successor's opening paragraph from the case template instead.)

Do not attach the full plan to the close-out reply — that is exactly what the case file is for.

## 6. Declare the retirement
Write it plainly at the end: **this session has retired; open a new session and take over C-NN with ctx-takeover.**

This session takes no new work after that. If the user keeps asking questions here, remind them to switch sessions first — carrying on inside this expensive context means paying again the money you just saved.
