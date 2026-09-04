---
name: ctx-takeover
description: Take over a case in a fresh session — use on "take over C-07", "continue that case", or /ctx-takeover C-NN; reads only the case file (old transcripts off-limits), signs as pen-holder, recites goal, case, progress and next step for your spot-check. Also triggers on Chinese — 开新会话继任时用：用户说"接手 C-07""继续那个案""你来接这个案""接着上个会话的活"，或显式 /ctx-takeover C-NN。
---

# Takeover: read the case only → sign → recite

> **Speak in the user's language, and write the case file / board / inbox rows in the user's language.** Status words and section letters are fixed bilingual, so a case written in either language must be readable by this skill and by the loader below. Section letters A~I never change. Status words used here: **awaiting takeover** (候接手) / **in discussion** (讨论中) / **awaiting decision** (候拍) / **closing (do not take)** (收口中(勿接)) / **closed** (已收口) / **running** (在跑) / **awaiting acceptance** (待验收) / **queued** (排队) / **to dispatch** (待派) / **delivered** (已交货) / **done** (已完); header-line fields `status` (状态) / `pen-holder` (持笔) / `updated` (更新), and `predecessor retired` (前任已退役); roles `lead` (导师) / `exec` (执行).

The argument = a case number (`C-07`, say) or a case file path.

## 1. Locate
Given a path, use the path; given a case number, glob `<case number>*.md` in the case library **inside the current project root** (project root = the git root if there is a `.git`, otherwise cwd; the library is **resolved in this order: the path on the line `ctx-kit case library: <path relative to the project root>` in the project root's `CLAUDE.md` if there is one, otherwise an existing `_ops/CASES/`, otherwise `cases/`**) — **never go looking in another project's case library**. **Resolve it yourself before asking**: the user should not have to type the library path, and a project that keeps its cases somewhere else has already said so in that one line.
- 0 hits: list every case in the directory and ask the user to point at one, **do not guess**.
- more than one hit: list the candidates and ask the user to choose.

## 2. Read the case file only, and only the sections you should
**Never read any old session transcript (jsonl)**, including the paths listed in section G — G is "reference only", and you fetch from it once, on target, only when the question in front of you plainly needs the evidence.

**How to read it: the header line + all of A~D + all of the inbox (§I, or the section of the same name in this track's track file); from E take only the table header + the rows whose status is running / awaiting acceptance / queued / to dispatch + the verdict of the most recent delivered row; for F / G / H look only at the section names and the line counts. Never `cat` the whole case file** — the E ledger has no length limit and old rows are often written as paragraphs, so reading a long-running case in full spends the great majority of its characters on old E rows nobody will look at.

Fill in the path and run the whole block; it locates the "status / verdict" columns by their header text (the column order differs from case to case, so a hard-coded column number must be wrong) and reports the number of characters loaded at the end:

```bash
F=<case file path>; python3 - "$F" <<'PY'
import sys,re
L=open(sys.argv[1],encoding='utf-8').read().split('\n')
P=[i for i,l in enumerate(L) if re.match(r'^##\s+[A-Z]\.?(\s|$)',l)]+[len(L)]
S={L[i].split()[1].rstrip('.'):(i,P[n+1]) for n,i in enumerate(P[:-1])}
z=lambda r:[c.strip() for c in r.strip().strip('|').split('|')]
o=L[:P[0]]
for k in 'ABCD':
    if k in S: o+=L[S[k][0]:S[k][1]]
if 'E' in S:
    a,b=S['E']; R=[l for l in L[a:b] if l.lstrip().startswith('|')]; D=R[2:]
    h=z(R[0]) if R else []; q=lambda w:next((i for i,x in enumerate(h) if re.search(w,x,re.I)),-1)
    j,v=q('状态|status'),q('判定|verdict'); g=lambda r,i:(z(r)+['']*9)[i]
    m=lambda p:[r for r in D if re.search(p,g(r,j),re.I)]
    A=m('在跑|待验收|排队|待派|running|awaiting acceptance|queued|to dispatch')
    F=m('已交货|已完|^完|达成|delivered|done')
    o+=[L[a],'']+R[:2]+['|'+'|'.join(c[:200] for c in z(r))+'|' for r in A]
    if F:
        y=lambda r:[(1,int(t)) if t.isdigit() else (0,t) for t in re.findall(r'\d+|[a-z]+',g(r,1 if j==0 else 0))]
        N=max(F,key=y) if any(y(r) for r in F) else F[-1]  # newest by ID (E-10b-2 < E-11), never by table order: newest-first and oldest-first both work
        o+=[f'latest delivered {g(N,1 if j==0 else 0)[:80]} | verdict {(g(N,v) if v>=0 else "see that row in the case")[:200]}']
    if not A+F: o+=D[-3:]+['<!-- status column did not match (column missing, or wording outside the vocabulary); last 3 rows kept, scan E by hand -->']
    o+=[f'<!-- E {len(D)} rows: all {len(A)} active rows + 1 latest verdict; the rest, and anything past 200 chars, stay in the case - fetch on target -->']
for k in 'FGH':
    if k in S: o+=['',f'{L[S[k][0]]}  <- not loaded ({S[k][1]-S[k][0]-1} lines), fetch on target']
if 'I' in S: o+=['']+L[S['I'][0]:S['I'][1]]
t='\n'.join(o);print(t);print(f'\n=== characters loaded this time: {len(t)} ===')
PY
```

**The inbox must be read, never skipped** — cross-track messages and the to-dos your predecessor left you both live there, and anything with an empty disposition cell is waiting on you. Skipping it has gone wrong once in practice: the predecessor wrote in 6 items (3 of them starred), the successor followed an older rule and never read the inbox, and the lot was lost on the spot. **Do not read deliverables end to end for the sake of being "more thorough"** — fetch them on target when you need them; reading transcripts is both expensive and liable to drag back dead branches that were already rejected.

**Size limit**: the character count on the last line = the entry tax base, in three bands — **≤10,000 is green; >10,000 and ≤15,000 is yellow, and the case gets slimmed at the next close-out; >15,000 must be slimmed before the case changes hands** (how to slim: see ctx-handoff). It is a count of characters, not bytes and not the file size on disk.

## 3. Sign (the only signal that the handover is complete)
- If the header-line status is **『closed』** (the end state of a closed case): **do not sign, do not recite**; reply "this case is closed; to reopen it say 'reopen C-NN'". **Reopening** = set the header-line status back to `awaiting takeover`, add one line to the F chronicle — "reopened: <why>" — then take over normally as below.
- If the header-line status is **『closing (do not take)』**: do not sign, do not recite; reply "this case is being closed out, take it later". Only when its 『updated』 timestamp is stale (>1 day), or the user confirms the closing session is dead, may you force the takeover — a forced takeover must state "what I am taking is a half-closed case", and must sweep B~H for gaps before reciting.
- Look at the header line's "pen-holder" first: **a name already there that is not this session → warn before anything else**: "the pen-holder of this case is X, another session may be taking it over, and two takers will tear the books apart"; change it only once the user confirms (a status already at "awaiting takeover" with the pen-holder marked "predecessor retired" is not a double takeover — sign straight away).
- Title: if the current title was set by hand by the owner (rather than the system's auto-generated summary form) → **keep the current name** and sign with it; otherwise `set_session_title` to **`NN-<compact case number>-what-this-stint-does[-track]-role`** (e.g. `07-C07-async-vs-streaming-decision-lead`): **NN increments inside this project and doubles as the time order** — sorting the sidebar by number gives this project's workflow in sequence, and it also prevents same-case name clashes for free, so there is no need for a separate "nth successor" (the session list is every project mixed together, so filter it down to this project by working directory first, then take the largest and add 1; if you cannot get it, leave it out — on a collision the later session renames); **compact case number** = the case number with the hyphen removed (`C-07`→`C07`), so a session is visibly filed to its case, and **a one-off has no case number, so the middle segment stays empty**; **the third segment says what this stint is doing, not the case name** — the case number already stands for the case, so the case name is a repeat, and one case spans several stints that are not doing the same thing; the track short name is written only when the job name does not reveal the track, and it is the short name of the track file, not a code; role = `lead` | `exec`; **no project prefix by default**, add a short one only on a genuine cross-project collision (`ck-04-C07-…`). If the tool does not exist or the call fails, skip it, say "the UI title is not in sync" in the reply, and change the pen-holder anyway.
- Change the header line's "pen-holder" to that name (write `name @first-8-of-UUID` if you can get the UUID), and "updated" to today.
- **The track-owner slot**: if the track this case belongs to has a track file, look at its "track owner" cell — **if it is empty or marked retired, sign yourself in while you are there** (the first thing a cross-track delivery checks is this slot, and a dead name in it hollows out the routing); **if a different live session already holds the slot, leave it alone** — one owner per track, one pen per case.

## 4. Recite in four chapters (proof that you caught it, and that the goal chain is in hand)

**Four chapters, one layer to a section, three to five lines each**; the criterion = the person involved recognises it from memory at a glance.

1. **The top-level goal and where this case sits**: the product top-level goal in one sentence / the pain in the scenario and the assets it needs / which milestone it hangs off, and the track goal in one sentence / what pulls it from upstream — read the overview (the board header); with no overview, use the R field of the case's section A and suggest building one. **The last sentence must answer this: which link of the top-level goal the work in this case is pushing forward right now, and whether it is still aligned.**
2. **This case's goal and route**: why it was opened → what it is answering now / the directions the owner has already decided / a **route step table**: step · what it does · which goal it serves · status.
3. **Current progress**: for the ledger's 「**running / awaiting acceptance**」 rows, **check the real state on the ground before reporting** — dispatch records, processes, artifact timestamps (run the liveness command and artifact locations your predecessor left on the E row / in section H at close-out); **never copy the point-in-time status straight off the case file**. It has gone wrong once in practice: the predecessor dispatched six sessions at 20:38 and retired at 20:51, and the case honestly said "running"; the successor reported "running, no readings" off the case file at 09:20 the next morning, and only checked when the owner pressed — all six had finished that same night, twelve hours earlier.
   **The same check covers section D**: an open item whose answer is already on the ground — the artifact written, the commit in `git log` — is settled whatever the case says, so report it as "done on the ground, not yet cleared from the case" rather than reciting it as open, and clear the row once the owner confirms. Measured three times in this project's own books.
   **One table for the most recent experiment — only if there is one**: write it when this case has delivered an experiment, or the predecessor's last stint ended on one; if the case is not experimental in nature or has no experiment yet, **leave the whole table out** — no empty table, no row saying "none / not run". Columns: what question it answers / how it is tested / what counts as a pass / expected vs actual and the verdict / **conclusion: what it means for the goal** ("budget and gate" may stay as an optional column).
   Then a **one-line ledger reading** (how many active E rows and in what statuses + the verdict of the most recent delivered row, or the current value of the M metric; report the number where there is one, say so plainly where there is none) + **one line for the inbox**.
4. **Next step (derived from the conclusion)**: an **ordered table** — order · what to do · **which conclusion it rests on** · which goal it serves · who it waits on; items awaiting decision or on hold are listed separately.

Do not recite the whole case, and **do not raise improvement suggestions at this step**.

**If the inbox has undisposed rows**: that line in chapter 3 must report them — N items outstanding, and what the most pressing one is. Where there are any you must report them; where there are none, say "nothing outstanding in the inbox".

## 5. Wait for the spot-check
One last sentence: **I am waiting for your spot-check questions; once I pass, I will carry on with this case.**

How to answer under spot-check:
- The answer is in the case → answer directly, naming the section it came from.
- Not in the case → **say "it is not in the case" first**, then fetch once, on target, following the pointers in G / H, naming the source.
- Cannot fetch it → say you cannot. **Never invent, never fill it in from imagination, never patch the gap with common sense** — one of the spot-check questions is a negative control aimed at exactly this.

## 6. The first moves after taking over
Pick "write to disk as you discuss" back up: write section C the moment a decision is made, rewrite section B the moment the plan changes; when dispatching, pick the carrier by the dispatch criteria; once this session passes 150k or reaches a batch boundary, **only remind** the owner (with the current watermark reading) — whether to close out is the owner's call, and **never run ctx-handoff on your own initiative**.
