# Handing a task to a fresh agent session: six cases, 93,073 characters down to 53,339

Context windows end before tasks do. If you run multi-day work inside a coding agent you know the shape of it: the session gets long, every request gets more expensive, and eventually the context fills up. What happens then is usually compaction: the agent squeezes the transcript into a summary and carries on. The summary preserves the ability to keep talking, which is what it is for. It is also lossy, and silent about what it dropped. You find out two hours later, when the agent cheerfully proposes the approach you ruled out on day one.

The file most of us reach for does not fix this. A project instruction file (CLAUDE.md and its equivalents) is onboarding: how to build the project, what the conventions are, which directories matter. It is not state for a task. It does not know that you tried three approaches to a bug, that the second is a dead end for a reason you cannot rederive from the code, and that the third is half finished and waiting on a decision you have not made. Onboarding is stable and shared by every job in the repo; task state changes hourly and belongs to one job. Merging the two is how instruction files grow until they are billed on every request of every session.

This is an agent harness problem rather than a model problem. The loop, the context management, the tool orchestration, the subagents and the guardrails all sit outside the model, and that is the layer where a job's state either survives a change of session or does not.

## What I do instead

Two moves, boring on purpose.

**Close-out.** Before a session is discarded, the discussion is distilled into a case file: one markdown file per job. It carries a header line (status, pen holder, last updated) and nine lettered sections: A goal, B current plan, C decisions, D open items, E experiment ledger, F chronicle, G archive pointers, H unsaved artifacts, I inbox. The letters never change, which is the only reason the next move can be mechanical.

**Takeover.** A fresh session picks the job up from that file and nothing else. Old transcripts are off limits. It does not read the whole case file either: it reads the header, A through D, the inbox, and from the experiment ledger only the rows that are still active plus the verdict of the most recent finished row. (This describes the loader as it stood on 2026-09-05, which is what produced every number below. It has since been narrowed further: the inbox now arrives as the rows still waiting on you, in full, plus the last three settled ones — so a takeover run today reads less than the figures here.) For the chronicle, the archive pointers and the unsaved list it loads the section names and their line counts, then fetches from them on target only when a question actually needs the evidence.

That asymmetry is the whole trick. A long job accumulates ledger rows and chronicle entries without limit, and whoever picks it up next does not need the accumulation. They need the goal, the plan, the decisions already made, what is still open, and what is in flight.

The reading is done by a small deterministic Python block inside the takeover skill. It prints one line at the end: `characters loaded this time: N`. That number is what the rest of this article measures. The skill treats it as a budget in three bands: 10,000 characters or under is green; above 10,000 and up to 15,000 is yellow, and the case gets slimmed at its next close-out; above 15,000 the case must be slimmed before it changes hands.

The skill layer is Claude Code specific; the case file is plain markdown and the loader is plain Python, so the measurement is not.

## What it cost, measured 2026-09-04

The first measurement, taking over one case:

- Slice loaded by the takeover: **10,816 characters**. Exact; it is what the loader printed.
- Net context added: **roughly 9,700 to 9,800 tokens**. The request reported 10,437 tokens of cache creation, and that figure includes the loader block's own text, about 600 to 700 tokens on that day's estimate. The thread I posted on 09-04 rounded this down to about 9,600, the conservative side. The subtraction is approximate and so is the result; 10,437 is the number to hold on to.
- The same case read end to end that day: **18,997 characters**, roughly 16k tokens on the same estimate.
- A second, older case read end to end that day: **28,920 characters**, roughly 25k tokens.

### About that 2.5x

When I first posted this I led with a ratio of about 2.5x. That number is 28,920 divided by 10,816: the full read of the *older* case over the slice of a *different* case. Both readings are real, and the ratio is not like for like. The like-for-like number from the same day is the same case measured both ways: 18,997 over 10,816, which is **1.76x**.

I am spelling this out because 1.76x is the number that transfers, and a ratio assembled from two different files should not be something a reader has to catch for me.

## The re-run: six cases, 2026-09-05

So I re-ran it properly: six live cases from one project, all opened between 09-01 and 09-04, measured on 09-05 at around 18:00 local time. Method: the canonical loader block from the takeover skill for the loaded figure, and Python's `len()` on the file's decoded text for the full figure. Characters, not bytes.

| case | ledger rows (E) | full chars | loaded chars | full / loaded |
|---|---|---|---|---|
| 1 | 28 | 29,715 | 13,348 | 2.23x |
| 2 | 1 | 5,146 | 3,573 | 1.44x |
| 3 | 5 | 18,477 | 9,816 | 1.88x |
| 4 | 6 | 23,644 | 16,278 | 1.45x |
| 5 | 7 | 13,053 | 7,522 | 1.74x |
| 6 | 2 | 3,038 | 2,802 | 1.08x |
| **all six** | | **93,073** | **53,339** | **1.74x** |

What I read out of it, and nothing beyond it.

**The ratio tracks ledger length.** The case with 28 ledger rows saves the most, at 2.23x. The two cases with one and two rows save the least, at 1.44x and 1.08x. That is the mechanism doing what it says: the ledger is most of what the slice skips, so a case with almost no ledger has almost nothing to skip.

**The saving compounds with the age of the case.** The slice is bounded by construction: A through D and the inbox get rewritten rather than appended to, while the file itself only grows. At one week old these cases save between 1.1x and 2.2x. I have not measured a month-old case, so I will not tell you where the curve goes.

**Two of the six are over budget, and the rule says what to do.** Case 1 loads 13,348 characters, inside the yellow band, so it gets slimmed at its next close-out. Case 4 loads 16,278, past the 15,000 line, so it has to be slimmed before it changes hands. That is the point of printing the number: the budget is enforced by a reading rather than by a feeling.

**The two days agree.** Same-case ratios land between 1.1x and 2.2x on both. The 2.5x was cross-case and it does not reappear.

One detail: case 3 is the same case that read 18,997 / 10,816 on 09-04. It was slimmed at a close-out in between, and today it reads 18,477 / 9,816, back under the green line. The ratio did not fall; it rose a little, which is what slimming should do: it takes material out of the sections that get loaded and parks it where the loader does not look.

## Why the numbers drift: characters, tokens, bytes, language

Three units get mixed up here and the gaps between them are large enough to change a decision.

**Characters are exact.** They come out of the loader and out of `len()`; every character figure here is one of those two.

**Tokens are estimated.** For these files I have been using 0.85 to 0.9 tokens per character, taken from three readings that ranged 0.8 to 0.95. Three readings is not a statistical result and I am not presenting it as one.

**Bytes overstate, sometimes wildly.** The 28,920-character file was 55 KB on disk, because UTF-8 Chinese is three bytes per character. KB on disk is not the cost. And `wc -m` is not a safe shortcut: under the C locale it counts bytes, which is how I mismeasured my own files on 09-05 while preparing this. Python's `len()` does not depend on the environment, so that is what I use.

**Language moves the constant, not the ratio.** These case files are Chinese-heavy, so tokens per character run high. An English case file would have roughly a quarter as many tokens per character, and the absolute token saving would scale down with it. The slice-to-full ratio is the part that transfers, because it is a property of what the loader skips rather than of the alphabet.

## What this does not show

- One project, six cases, none older than about a week. That is a sample, not a study.
- It measures cost, not outcome quality. I have not shown that a session taking over from a slice does the work as well as one that read everything, and I have not run that comparison.
- Character counts are exact; every token figure is an estimate, including the 9,700 to 9,800 here and the 9,600 in the thread.
- The ratio depends on how disciplined the close-out is. A case file allowed to sprawl through sections A to D will load more, and the loader will say so on its last line.
- I have not compared this with any other way of solving the same problem. If you already keep a handoff note by hand, nothing here says yours is worse.

## Reproduce it

The repository: https://github.com/bestiaya/ctx-kit

1. Clone it.
2. Take any case file written with ctx-kit, or your own state file using the same section letters.
3. Run the loader block from `skills/ctx-takeover/SKILL.md` against it. It prints the loaded character count on its last line.
4. Compare against the full size:

```bash
python3 -c "import sys;print(len(open(sys.argv[1],encoding='utf-8').read()))" path/to/case.md
```

For exact tokens, run your model provider's token counting endpoint over the loader's output, or read the usage fields your CLI reports for the request that did the reading.

The loader is reproduced below verbatim.

## Appendix: the loader block

This is the block as it stood on 2026-09-05 — kept verbatim so the numbers above stay reproducible, not as the current version. The one in `ctx-takeover` has moved on since.

```bash
F=path/to/case.md; python3 - "$F" <<'PY'
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

Nothing in it is clever. It splits on the `## <letter>` headings, keeps A through D and the inbox, filters the ledger by its status column (located by header text, because the column order varies), swaps the remaining sections for their line counts, and prints the length of what it built.
