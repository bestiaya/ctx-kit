---
name: ctx-handoff
description: Close out and hand off — use on "close out", "wrap this up", "this session is too full", or /ctx-handoff; distills the discussion into a takeover-ready case file, persists unsaved artifacts, then retires this session. Also triggers on Chinese — 用户说"收口""关案""这个案完了""交接一下""这会话太贵了""这会话太肥了""换个新会话继续""退役这个会话"，或显式 /ctx-handoff 时用。
---

# Close-out: settle it into a case → retire

> **Speak in the user's language, and write the case file / board / inbox rows in the user's language.** Status words and section letters are fixed bilingual, so a case written in either language must be readable by every skill here. Section letters A~I never change. Status words used here: **closing (do not take)** (收口中(勿接)) / **awaiting takeover** (候接手) / **closed** (已收口) / **predecessor retired** (前任已退役) / **in discussion** (讨论中) / **running** (在跑) / **awaiting acceptance** (待验收) / **awaiting decision** (候拍) / **queued** (排队) / **to dispatch** (待派) / **delivered** (已交货) / **done** (已完); header-line fields `status` (状态) / `pen-holder` (持笔) / `updated` (更新).

> **Trigger line**: this skill runs **only when the owner triggers it, or after the owner has explicitly agreed**. A session over the line (high watermark, batch boundary) gets **a reminder only, never a forced close-out** — report the current watermark reading in one line, ask in one line whether to close out, and **do not close out on your own initiative**. Closing out changes the header line, writes the row back on the board, sets the retirement mark, commits and pushes; close out a session that is still in use and the user pays for a takeover all over again.

## 1. Claim first: which case do I hold?
Check in order: ① this session's title (the name set through `set_session_title`); ② whether the "pen-holder" cell in any case's header line in the case library carries this session's name or the first 8 of its **session id** — the `sessionId` that `get_session` / `list_sessions` hand back (form `local_<uuid>`; on the desktop app, `get_session` on `self`), **never the name of the transcript file**, which is a second id for the same session and is not what anything here addresses. **The case library is only ever looked for inside the current project root** (project root = the git root if there is a `.git`, otherwise cwd; the library is **resolved in this order: the path on the line `ctx-kit case library: <path relative to the project root>` in the project root's `CLAUDE.md` if there is one, otherwise an existing `_ops/CASES/`, otherwise `cases/`**) — **never claim a case out of another project's library, and never write files across into one**.

- A hit → **update mode** (2A); no hit → **first-build mode** (2B).
- **A case file that plainly covers this stint's work but whose pen-holder cell names nobody** — blank, `(TBD)`, or `(successor to fill in; predecessor … retired)` — **is update mode as well, not a missing case.** That is the ordinary state a case sits in once its predecessor has retired, so write your own name into the pen-holder cell and go on with 2A; **never build a second case for work that already has one** (a duplicate splits the books, and merging them back costs far more than asking). Say in one line which case you claimed and what made you sure, so the owner can stop you if it was the wrong one. Go to 2B only when nothing in the library covers this work at all.
- **The first move in both modes**: change the header line to 『status: closing (do not take)』 and keep the pen-holder (you are still writing, and one pen per case still holds); in first-build mode write the header line with that status from the start.

## 2A Update mode (the case already exists)
- **Rewrite section B whole** into the current end state (the old version it replaces rolls into one line of F); do not patch it incrementally.
- **C / E / F are append-only**; never edit historical rows — rejected decisions stay too. **Date every line of F off the ground** — `git log` for what was committed, the file timestamp for what was written — never off memory: the chronicle is what the next session checks the books against.
- **Re-sort D**: move what has been decided into C, **delete the rows that are done** (leave a line in F if it is worth remembering — the same rule `ctx-kickoff` §2 states for D), add the new open items, each with a recommendation. **Look at the ground before you clear a row or leave one standing** — the artifact on disk, `git log`, the delivery path on the E row — not at what you remember doing. Measured three times in this project's own books: a row left standing in D that the disk said was finished days earlier.
- **Re-list H** (not append): drop whatever from the previous H has since gone to disk, and keep only what is still unsaved right now.

## 2B First-build mode (no case file)
Propose `<prefix>-NN_case-name.md`: the prefix is per project (the main project keeps its existing letter, another project takes the initials of the project name), and **NN increments inside this project's case library — never carry on from another project's numbering** (measured, and it went wrong: a throwaway project's session carried on from the main project's numbers, and its files landed in the main project too). **Say the target absolute path aloud together with the name before creating it**; one confirmation is enough. Build all nine sections A~I (A Goal (目标) / B Current plan snapshot (当前方案快照) / C Decisions (已拍决策) / D Open items & pending decisions (未决与候拍) / E Experiment ledger (实验台账) / F Chronicle (编年志) / G Archive pointers (档案指针; reference only) / H Unsaved items (未落盘清单) / I Inbox (收件位) — I is this case's own address, the only route other cases have to it, so write it whenever anything may need to reach this case).

## 2C Closing a case (the end state of a close-out, not a second procedure)
**Closing a case is one kind of close-out**: write B~H the normal way per 2A / 2B, then do these three extra steps.

**Trigger**: the owner says "close the case" or "this case is finished"; or, at close-out, you judge that the case's **section A goal has been met** — **in the second case ask first, and close only once the owner nods**; never close a case on your own initiative.

1. **Header line**: `status: closed   pen-holder: (closed <today>)   updated: <today>`, the `stint` (任期) field left as it stands — this does not use the "awaiting takeover / predecessor retired" pattern; once it is closed there is no successor to take a number.
2. **The board**: change this case's row in the 「cases on the books」 table to status `closed` and **move the whole row to the end of the table** — the row keeps all **seven** columns, and it is split on unescaped pipes only (§4 step 2). **Never create a new section such as "closed cases"** — the downstream skills read the board by section name, and one extra section makes them miss things.
3. Add one line to the **F chronicle**: `<date> case closed: <one sentence on why — goal met / dropped / merged into another case>`.

Stop there: **closing a case means only this, that nobody takes it over again** — do not delete the file, do not move the directory; the history stays where it can be looked up.

## 3. Hard rules
- **What a takeover actually loads, in three bands: ≤10,000 characters is green; >10,000 and ≤15,000 is yellow — slim it at the next close-out; >15,000 must be slimmed before the case changes hands** — the measure is "how much has to be read in to take it over once", not "up to E": run the extraction command in `ctx-takeover` §2 and read the number it reports on its last line. **That number is characters**, not bytes and not file size: Chinese text is three bytes per character in UTF-8 (this project's mixed-language cases measured about two bytes per character on 2026-09-04), so a size on disk says little about the load — measure characters (`LC_ALL=en_US.UTF-8 wc -m`), never bytes. **Take the reading last, once everything else is written, and record it in F** — the reading counts A~D and I, so a number written into any of those moves the number it is reporting (measured: four measure-and-edit rounds chasing its own tail, and a case that crept back over the line afterwards because two more lines went into the inbox). **The slimming is the pen-holder's own job, done in the stint that crosses the line, not left for the successor** — whoever wrote those rows is the only one who can tell in a glance what is safe to move, and a case handed over above the line makes the successor pay to read the very rows the predecessor could have moved in five minutes (the five steps in `ctx-takeover` §2 are the same five, written out for a session that finds itself over the line mid-stint). First choice for slimming = **move the old rows of table C out into this case's decision appendix as a block** — `<case file name without .md>_decision-archive_<date>.md` (中文 `<案文件名去 .md>_决策附录_<日期>.md` — **name it in the language the case is written in**, as with the other two archives) — (moved verbatim, with only the current batch + a pointer left in the case); then rolling old E rows into an archive (next rule), clearing settled items out of D, compressing the chronicle in F; if that is still not enough, promote the plan body into its own numbered document and leave only the top-level diagram + a pointer in section B.
- **Rolling E into an archive**: once E passes 5,000 characters or 30 rows, move the rows whose status is delivered and whose "what it changes in the plan" has already been written into B / C **verbatim** into `<case file name without .md>_experiment-archive_<date>.md` (中文 `<案文件名去 .md>_实验档案_<日期>.md` — **name it in the language the case is written in**, so one library does not end up half and half) (same format as the decision appendix, headed "moved verbatim, nothing deleted or altered, stub kept in the case"), leaving one stub row each in the case: `ID | question | verdict in one sentence (≤80 characters) | archive pointer`. **Rows at running / awaiting acceptance / queued / to dispatch always stay in the case**, and so do delivered rows whose impact has not been written back into B / C — that account is still owed.
- **E row length check (report, do not fix)**: the Verdict cell and the Impact-on-plan cell are each ≤200 characters — **checked on the rows a takeover actually reads and on no others**: the rows at running / awaiting acceptance / queued / to dispatch, plus the single most recent delivered row — **most recent by ID (`E-10b-2` sorts before `E-11`), never by the order the rows sit in the table, and a row marked done counts as delivered here** — whose verdict is the only one the loader in `ctx-takeover` §2 carries across. **The cap is there because that loader cuts every cell it carries off at 200 characters**: what a cell says past the cut no successor ever sees, so the verdict has to be said inside those 200 and the account left in the deliverable. An older delivered row never enters a successor's slice, so its length costs the successor nothing and the check leaves it alone. **A cell over the cap: put one sentence of verdict in it (≤200 characters) and the path to the deliverable beside it, and leave the account itself in the deliverable** — the ledger is an index, not a report. Run it once before closing out; slim an over-long row on the spot if you wrote it, and report without touching it if somebody else did (the same block, run over a whole library instead of one case, is what `ctx-checkup` §4 uses):

**Run it with a real python3**: an error mentioning `xcodebuild` or similar means the interpreter resolved somewhere else (the macOS Xcode shim, for instance) — run it again with a real python3; the block is not broken.

```bash
python3 - <path to this case file> <<'PY'
import sys,re
W=re.compile(r'(?<!\\)\|')  # split on unescaped pipes only: a \| inside a cell is content, not a separator (§4 step 2). Four places carry this same split and must agree — the loader in ctx-takeover §2, this block, the same block over the whole library in ctx-checkup §4, and split_cells in scripts/case-lint.py
def z(r):  # the cells of one markdown row
    p=[c.strip() for c in W.split(r.strip())]
    if p and not p[0]: p=p[1:]
    if p and not p[-1]: p=p[:-1]
    return p
A=re.compile(r'^\W*(在跑|待验收|排队|待派|running|awaiting acceptance|queued|to dispatch)',re.I)  # live
B=re.compile(r'^\W*(已交货|已完|delivered|done)',re.I)                                            # finished
w=[]
for p in sys.argv[1:]:
    L=open(p,encoding='utf-8').read().split('\n')
    P=[i for i,l in enumerate(L) if re.match(r'^##\s+[A-Z]\.?(\s|$)',l)]+[len(L)]
    for n,i in enumerate(P[:-1]):
        if L[i].split()[1].rstrip('.')!='E': continue
        R=[(k+1,l) for k,l in enumerate(L[i:P[n+1]],i) if l.lstrip().startswith('|')]
        h=z(R[0][1]) if R else []
        C=[x for x,c in enumerate(h) if re.search(r'判定|verdict|影响|impact|plan',c,re.I)]
        j=next((x for x,c in enumerate(h) if re.search(r'状态|status',c,re.I)),-1)  # a column by its header text, never by number
        g=lambda c,x:(c+['']*9)[x]
        D=[(ln,z(l)) for ln,l in R[2:]]
        # Only the rows a takeover reads in: every live row, plus the one most recent finished
        # row whose verdict the loader carries across (ctx-takeover §2 picks it exactly this
        # way — newest by ID, never by table order). An older delivered row never enters a
        # successor's slice, so its length costs nobody anything and is not measured here.
        u=[t for t in D if j>=0 and A.match(g(t[1],j))]
        v=[t for t in D if j>=0 and B.match(g(t[1],j))]
        y=lambda t:[(1,int(s)) if s.isdigit() else (0,s) for s in re.findall(r'\d+|[a-z]+',g(t[1],1 if j==0 else 0))]
        S=u+([max(v,key=y) if any(y(t) for t in v) else v[-1]] if v else [])
        if not S: S=D[-3:]  # no status column, or not one word the loader knows: it falls back to the last three rows, so those are what gets read
        for ln,c in S:
            w+=[(len(c[x]),f'{p}:{ln} [{h[x]}] {len(c[x])} chars') for x in C if x<len(c) and len(c[x])>200]
for n,s in sorted(w,reverse=True): print(s)
print(f'--- {len(w)} cells over 200 characters (reported, not fixed — the author slims their own) ---')
PY
```

- **Splitting F**: once section F alone passes 10,000 characters, cut it at a natural boundary (a release, the end of a batch) — everything before that boundary moves **verbatim** into `<case file name without .md>_chronicle-archive_<date>.md` (中文 `<案文件名去 .md>_编年志档案_<日期>.md`), and the case keeps the entries since that boundary plus one pointer line. F is not part of the takeover load, but an unbounded chronicle makes every close-out that re-reads it dearer. **A decision a later decision has overturned moves into the decision appendix** as well (the old row goes across verbatim; the row in C that overturned it stays) — the same move as taking the old rows of C out, one row at a time instead of a block.
- **Sweep the inbox before you retire**: section I keeps only the rows that are **not yet disposed** plus the rows that came in during this stint; every other disposed row is swept out into F, one line each (date / who it came from / what came of it), so the account survives the sweep. **Disposed** = the disposition cell is non-empty **and opens with** `done` (已办) / `dropped` (不办) / `moved to <where>` (已转 <去处>); an empty cell, or one worded any other way, is not disposed and stays where the successor will see it. **Write every disposition starting with one of those three** — the rule reads the opening, not the rest of the cell, so a row worded otherwise never sweeps out and never leaves the successor's slice. **Escape every pipe inside an inbox cell as `\|`**, in a row you send into another case as much as in a disposition you write back: an unescaped one splits the row into the wrong number of cells, and a takeover reads that row as malformed. Measured: 3,400 characters of inbox sitting inside a 12,100-character takeover slice, most of its rows long since dealt with.
- **Put unsaved artifacts on disk first** (drafts, scripts, tables, half-finished sums), and write the paths into E or H.
- **A running experiment must carry a liveness check (required)**: if any experiment is at status running / awaiting acceptance when you retire, **spell out the liveness command and where the artifacts land, both on the E row and in section H** (e.g. `check all six dispatch json files landed + pgrep -f <batch script> returns 0`). The successor checks the real state that way before reporting, instead of copying the status off the case. It has gone wrong once in practice: six sessions dispatched at 20:38, retirement at 20:51, and the case honestly said "running"; at 09:20 the next morning the successor reported "running, no readings" off the case, when in fact all of it had finished that same night — twelve hours wasted.
- **Write this session's jsonl path in section G as `(to be backfilled)`** — never use `ls -t` to look yourself up, which has been measured pointing at the wrong file. Whoever accepts the work pairs it up later **on the session name the transcripts carry**, checking the moment as a second opinion (`ctx-checkup` §3) — **not on a billing signature**, which shows up only where a session had gone cold before its last request and so pairs nothing off on its own. List the other known archives and artifact directories as usual, marked "reference only, do not read in full".
- **Section H must be written into the case file itself**, not left only in the reply (close the window and it is gone). One line each, with the path to the detail; list them honestly and never drop one silently — **including what you did not finish, what you got wrong, and numbers that will not reproduce**.

## 4. The last four moves (only after B~H are written)
1. Change the header line: `status: awaiting takeover | pen-holder: (successor to fill in; predecessor <this session's name @<first 8 of the session id>> retired) | updated: <today>` — the session id as §1 defines it, and the title alone if you cannot get it. **Leave the `stint` (任期) field exactly as it stands**: it records the stint now retiring, and the successor adds 1 to it when it signs (`ctx-takeover` §3), so a close-out that bumps it hands out the same number twice. **Never do it in the other order** — clearing the pen first hands the successor a half-closed case.
2. **Write your row back on the board**: the case index row carries **seven columns, in this order** — case number / name / milestone / status / pen-holder / where it is / next step — so update status, pen-holder (the same `(successor to fill in; predecessor … retired)` you just wrote on the header line), where it is, and next step, and **touch no other row and not the board header**. **Split the row on unescaped pipes only**: a `\|` inside a cell is content, not a separator. Measured once: a close-out cut the line at every `|` it saw, wrote it back on the old six-column shape, squeezed the new column out and tore a `\|` in half.
3. **Mark yourself retired**: `set_session_title` this session's title to `✕ <original title>` (a prefix, not a suffix — a suffix gets truncated out of sight in the list). This is the only naked-eye signal that a session is dead, and the first gate a delivery from another case hits when it checks the address. If the tool is unavailable, say plainly in the reply that the mark was not set.
4. **Commit, and push your own branch**: **you must commit, and you must push what you committed** — and what you push is **the branch this session is on, carrying its own records and its own changes**, never a branch somebody else holds the pen on. Measured: 15 days away from the machine, and a batch of commits sat on the local disk for 3 days, so **fixing only the commit does not fix it**. **Where a project runs its releases as a routine, the release branch is not a close-out's to push**: merging changes into it, tagging and rewriting history all belong to that routine's pen-holder — push your own branch, say in the reply what is waiting to be merged, and leave the merge to them.
   Run `git status` first: **another session may be open and editing other files, and `git add -A` will commit their half-written work along with yours** (this rule was hit the very first time it ran — two running sessions each had a half-edited case file). **`git add` only the paths you touched this round**, then `commit && push`.
   **Write the message as a public artefact**: say what changed and what the readings were, and keep case numbers, experiment IDs, wave numbers and session names out of it — the commit log is published, and those names mean nothing to a reader outside the project. Measured: a day of 12 commits written this way, and a scan of that history for leaked internal names found none.
   A non-git project, or a failed push (no remote / no permission / a conflict): **write "not pushed + why" plainly in the reply**; never skip it silently.
   **A case library that git ignores or has never tracked is a legitimate shape, not a failure**: the case files stay on disk and out of the repository, so commit and push only whatever else this round touched — and if that leaves nothing to commit, nothing is wrong. Say so in one line in the reply — the case file is saved on disk but is not in git, so taking it over on another machine means syncing that directory yourself — and **never report that as a failed push**.

## 5. Reply: five sections for people first, then four items

**The five sections for people first** — one or two lines each, written for the owner:

- ① **Position and reason**: how far this case has pushed the top-level goal, and what this stint did;
- ② **What was verified, how it was tested, what counts as a pass**;
- ③ **Result**: the verdict first, expected vs actual;
- ④ **Conclusion**: what it means for the goal, which premise was confirmed or refuted, what is still unproven;
- ⑤ **The next step, derived from the conclusion** (every item awaiting decision carries a recommendation).

Item numbers, station ids and reading codes stay out of the sections written for people — the codes, not the readings: a measurement with its baseline is exactly what those sections are for. If you must hand something to the execution layer, put it on one line at the end.

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
