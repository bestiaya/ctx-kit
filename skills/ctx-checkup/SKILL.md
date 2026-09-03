---
name: ctx-checkup
description: Weekly cache audit — use on "weekly checkup", "where did the tokens go", "audit session costs", or /ctx-checkup; runs cache-audit, flags sessions over the pre-registered lines, backfills archive pointers in case files. Also triggers on Chinese — 用户说"周检""查一下会话花费""哪些会话该收口了""跑一下缓存审计""这周 token 都花哪了"，或显式 /ctx-checkup 时用。
---

# Weekly checkup: audit → read the numbers → backfill

> **Speak in the user's language, and write the case files / board / inbox rows in the user's language.** Status words and section letters are fixed bilingual, so a case written in either language must be readable by this skill. Section letters A~I never change. Status words used here: **delivered** (已交货) / **awaiting decision** (候拍); header-line fields `status` (状态) / `pen-holder` (持笔) / `updated` (更新); roles `lead` (导师) / `exec` (执行); the placeholder in section G is `(to be backfilled)` / `(待回填)`.

**Two things before you start; miss either and you will be wrong** (both have gone wrong in practice): ① run `date` for the real clock — **never infer the date from file timestamps or from the bill**, because a wrong inference stamps the whole batch of records with the wrong date; ② pull the live session list again — **whether a session is alive or dead is settled by the header line of the case / track file**; the register is only a projection and may be stale, and judging from it will treat retired sessions as live.

## 1. Run the audit

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/cache-audit.py" --all
```

The script is pure standard library, zero dependencies. An error mentioning `xcodebuild` or similar means the interpreter resolved somewhere else (the macOS Xcode shim, for instance) — run it again with a real python3; the script is not broken.
**`${CLAUDE_PLUGIN_ROOT}` is set only under a plugin install.** On a manual install it is empty, the command above resolves to `/scripts/cache-audit.py`, and you get "no such file" — **use the path you copied the script to instead** (`python3 ~/.claude/scripts/cache-audit.py --all`, say). Do not guess at a plugin directory that is not there.
The script derives the project archive directory from cwd; if the directory does not match, add `--project <directory>`.
**A table with zero rows is not a pass.** When nothing comes back but the header (the script says `(no sessions found under <directory>)`), report it in those words — **"no session logs found for this project directory — nothing to judge"** — and never dress it up as a clean checkup: a checkup with nothing to read has checked nothing. Before concluding, confirm the directory on the script's first line is the project you meant (`--project <directory>`) and re-run with `--all 0` to drop the 2MB floor, in case the logs are simply small.

## 2. Reading the numbers (pre-registered criteria; a fail is reported as a fail)

| Session type | Criterion | What crossing the line means |
|---|---|---|
| Discussion / lead | rewrite share **<10%** and p50 watermark **<150k** | the money is leaking into re-reading the same thing |
| Exec | compact count **= 0** and peak watermark **<200k** | what should have gone to disk did not |

The script flags every row over the line with ⚠️, but **do not just recite the table** — give an action for each one:
- High rewrite share + high watermark → **"time for ctx-handoff"**; while you are there, estimate the buy-out price `watermark×(2+0.1×(N−1))+output×5` and set it against "one more cold re-entry costs watermark×2", so the user can decide at a glance.
- An exec session with compact >0 → point out that it should have written to disk and started fresh instead of compacting.
- An already closed old session with **0 new requests** this period → the retirement check passes; >0 and you name it: "retirement not honoured".

## 3. Backfill section G
Sweep the case directory (`_ops/CASES/` for preference, otherwise `cases/`) for cases whose section G says `(to be backfilled)` / `(待回填)`, and pair them up one at a time:
1. take the close-out moment from the case file's "updated" date and the file mtime;
2. in the project archive directory find the session around that moment carrying the **billing signature of a close-out round** — a single `cache_creation` ≈ that session's watermark, with no request after it;
3. once paired, write the jsonl path into section G, marked "reference only, do not read in full".

Two rules:
- **jsonl timestamps are UTC** — convert to the local timezone before comparing them with the local clock (one timezone out and you pair the wrong session).
- **If it does not pair, leave `(to be backfilled)` in place and say so.** Better empty than a path that merely "looks right" — using `ls -t` to point at yourself has been measured pointing at a file two weeks old.

## 4. Case size check
The measure = **what a takeover actually loads** (header line + A~D + E's active rows and latest verdict + I), not "how big the file is", and not the old measure of "count up to E". Run the extraction command from `ctx-takeover` §2 on each case (swap `F=` for each case path) and `| tail -1` to take only the character count on the last line — **do not read the extracted body into context**; the checkup only needs the number. Skip decision appendices, experiment archives and TASKBOARD.

Criterion (relaxed by the owner on 2026-08-24, previously 7,000): **≤10,000 per case is green**, **>15,000 must be slimmed**. For every case over the line, report the number and name the pen-holding session to do the slimming: hand the old rows of table C up to the track-level decision archive / roll the old delivered rows of E into an archive (see `ctx-handoff`) / clear the settled items out of D / compress the chronicle in F; historical detail belongs in the transcript and the archives, not in the case.

**E row length check (report, do not fix)**: the verdict cell and the "what it changes in the plan" cell are each ≤200 characters. Run it over the whole case library and list the over-long rows in descending order of length (case file / row number / which cell / character count), reporting them to that case's pen-holding session to slim down themselves — **the checkup never edits somebody else's case**:

```bash
D=_ops/CASES; [ -d "$D" ] || D=cases; python3 - "$D"/*.md <<'PY'
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

**Split-the-case hint (a hint only, never a fail)**: if a case has >30 E rows, or >50 C decision rows added in the last 30 days, say one line — "consider splitting this case". **Both thresholds are rules of thumb and have not been verified**, so treat them only as a conversation opener; they are not criteria and they never count towards pass or fail.

## 5. Retirement-mark sweep
A session that marks itself at close-out carries the `✕` prefix. **A session that crashed or was abandoned never marks itself**, so this step catches up:
- list every session that is **neither the track owner of any track, nor the pen-holder of any case, nor the carrier of any one-off**, has not moved for >1 day, and has no `✕` prefix in its title;
- `set_session_title` each of them to `✕ <original title>`. **Leave the doubtful ones alone** — better to miss one than to mark a live session dead. If the title tool is unavailable (a bare terminal), skip this step and say so in the reply.
- Report the numbers: N newly marked this period, M skipped as doubtful (named).

## 6. Reply
One table (session / criterion / actual reading / pass or fail / recommended action) + one line of overall account: how many over the line this period, how many recommended for close-out, how many cases over the size limit, section G backfilled x/y, how many retirement checks passed.
