---
name: ctx-checkup
description: Weekly cache audit — use on "weekly checkup", "where did the tokens go", "audit session costs", or /ctx-checkup; runs cache-audit, flags sessions over the pre-registered lines, backfills archive pointers in case files. Also triggers on Chinese — 用户说"周检""查一下会话花费""哪些会话该收口了""跑一下缓存审计""这周 token 都花哪了"，或显式 /ctx-checkup 时用。
---

# Weekly checkup: audit → read the numbers → backfill

> **Speak in the user's language, and write the case files / board / inbox rows in the user's language.** Status words and section letters are fixed bilingual, so a case written in either language must be readable by this skill. Section letters A~I never change. Status words used here: **delivered** (已交货) / **awaiting decision** (候拍); header-line fields `status` (状态) / `pen-holder` (持笔) / `updated` (更新); roles `lead` (导师) / `exec` (执行); the placeholder in section G is `(to be backfilled)` / `(待回填)`.

**Two things before you start; miss either and you will be wrong** (both have gone wrong in practice): ① run `date` for the real clock — **never infer the date from file timestamps or from the bill**, because a wrong inference stamps the whole batch of records with the wrong date; ② pull the live session list again — **whether a session is alive or dead is settled by the pen-holder cell on the case's header line, or by the carrier cell of a one-off row on the board**; the session register is only a projection and may be stale, and judging from it will treat retired sessions as live.

## 1. Run the audit

```bash
S="${CLAUDE_PLUGIN_ROOT:+$CLAUDE_PLUGIN_ROOT/scripts/cache-audit.py}"; [ -f "$S" ] || S="$HOME/.claude/scripts/cache-audit.py"
if [ -f "$S" ]; then python3 "$S" --all; else echo "cache-audit.py is in neither place ctx-checkup looks (plugin root, then ~/.claude/scripts/) — nothing was audited. Manual install: copy scripts/cache-audit.py out of the ctx-kit repository into ~/.claude/scripts/, as the README manual-install step says (repository: github.com/bestiaya/ctx-kit)."; fi
```

**To keep the run as an artifact (§6), add `--out <path>` to that command**; without it the script writes nothing, and the file it writes is the same text the terminal got, unchanged. A directory on that path that is not there yet is created for you, so a project's first checkup can point straight at its `CHECKUP/`.
The script is pure standard library, zero dependencies. An error mentioning `xcodebuild` or similar means the interpreter resolved somewhere else (the macOS Xcode shim, for instance) — run it again with a real python3; the script is not broken.
**Two places, in this order: the plugin root, then `~/.claude/scripts/`.** `${CLAUDE_PLUGIN_ROOT}` is set only under a plugin install; on a manual install it is empty and the script sits where the README's manual-install step puts it, `~/.claude/scripts/cache-audit.py` — the block above tries both, so never type a plugin path by hand. If it prints that the script is in neither place, **say exactly that — nothing was audited** — and pass on the one fix it prints: copy `scripts/cache-audit.py` out of the ctx-kit repository you installed from into `~/.claude/scripts/`, which is the README's manual-install step (a manual install leaves no README on disk, so point at the repo, not at a local file). Do not guess at a plugin directory that is not there, do not go hunting through backups, and never report an audit you did not run.
The script derives the project archive directory from cwd; if the directory does not match, add `--project <directory>`. It also prints the case library it resolved on the `# case library:` line — the same directory §3 and §4 sweep, and `--cases <directory>` overrides it.
**A table with zero rows is not a pass.** When nothing comes back but the header (the script says `(no sessions found under <directory>)`), report it in those words — **"no session logs found for this project directory — nothing to judge"** — and never dress it up as a clean checkup: a checkup with nothing to read has checked nothing. Before concluding, confirm the directory on the script's first line is the project you meant (`--project <directory>`). **The 2MB floor no longer needs handling by hand**: the script says how many logs it found and how many the floor hid, and when the floor hides every one of them it drops the floor and re-runs itself (same as `--all 0`), saying so on a `#` line — so read those lines instead of re-running, and `(no sessions found under <directory>)` now means the directory really is empty.

## 2. Reading the numbers (pre-registered criteria; a fail is reported as a fail)

| Session type | Criterion | What crossing the line means |
|---|---|---|
| Discussion / lead | rewrite share **<10%** and p50 watermark **<400k** | the money is leaking into re-reading the same thing |
| Exec | compact count **= 0** and peak watermark **<500k** | what should have gone to disk did not |

The script flags every row over the line with ⚠️ — the flag fires on any of those four lines: rewrite share >=10%, p50 watermark >=400k, peak watermark >=500k, or compacts >0. **The script cannot tell a discussion session from an exec one, so the flag is the union of both rows of the table above: read a flagged row against that session's own type** — a discussion session that crossed only an exec line (peak watermark >=500k, say, while rewrite share and p50 stayed inside their lines) is flagged but is **not** a fail. Then **do not just recite the table** — give an action for each one:
- High rewrite share + high watermark → **"time for ctx-handoff"**; while you are there, estimate the buy-out price `watermark×(2+0.1×(N−1))+output×5` and set it against "one more cold re-entry costs watermark×2", so the user can decide at a glance.
- An exec session with compact >0 → point out that it should have written to disk and started fresh instead of compacting.
- An already closed old session with **0 new requests** this period → the retirement check passes; >0 and you name it: "retirement not honoured".

### Echo totals (a reading, not a gate)

The table's `echo` column is the characters a session's tool results put into a context — its own and its subagents' — and `bash%` is the Bash share of that. Under the table the script prints two more numbers: the total across the rows shown, and **how many of those sessions echo more than 30,000 characters in total while no single tool result ever reaches it**. Those are the sessions a read gate that fires on one result at a time cannot see. **Report both and attach no action**: nothing here passes or fails on them, and 30,000 is the read gate's existing number reused as the boundary of a count, not a new line.

Two readings to set the count against, both taken on 2026-09-09, and **both counted per context** — one transcript is one context and a subagent counts as its own, which is *not* the unit the table uses, because the table folds a subagent's echo into the session that dispatched it and so counts fewer, larger sessions: **167 of the 217 contexts that carried any tool echo** in this kit's own project, and **34 of the 106 contexts that carried any Read** in a second project on the same machine — a Read-only count, ignores Bash, not comparable in size with the first. Bash is where the bulk of it sits and is also where a per-call gate is structurally blind: **60% of all echo characters in the first project, with none of its 6,890 Bash results reaching 30,000 characters; 82% in the second, with none of its 7,705 reaching it either**. What those readings say is that a gate reading one result at a time does not see this material. They do **not** say the material was waste, and nothing measured here says what a cumulative gate would save — so do not propose one off the back of this number.

### The resident floor (a reading; no line is set on it)

**What it is**: what a session pays before anybody has said anything — the rules and the memory index the runtime loads at the top of every fresh session. It is outside the four lines at the top of this section; a project measures it so that adding a rule block, or a line to a memory index, is a change with a number against it instead of a guess.

**How to measure it**: a brand-new headless session, one turn, with no tool called — **use the flags in the command block below, verbatim**, rather than composing your own. Take the first assistant record's `input_tokens + cache_creation_input_tokens + cache_read_input_tokens`; output tokens are no part of it, which is the same three-term sum the `p50 ctx` column and the watermark doorbell use. The block reads the `usage` totals that `--output-format json` prints for the whole run instead, which on a one-turn run that called nothing is that same first record. **Measure each state twice** — the pair is the reading, and how far its two halves sit apart is what says whether a difference is real; comparing a before against an after therefore takes four readings, two of each. Same machine, same project directory, same day, one thing changed between the pairs. **Keep the prompt fixed**: the prompt is inside the reading, so a reworded prompt is a different measurement, not a change in the floor.

**What to report**: the two readings and the spread between them; the make-up in characters (the user-level `CLAUDE.md`, the project `CLAUDE.md`, the memory index); and **the difference from last time — not a verdict**. The same total can arrive by different routes, because the first session of a day writes the cache and later ones read it, so a change in how the three terms split is a change in cache hits and says nothing about what was loaded. **No line is set here, deliberately.** Where a project has never measured this before, say so in those words — there is no baseline yet, so there is nothing to set a line from; report the difference and let the owner decide, after two of them, whether a line is worth having. How much jitter to expect is itself a reading rather than an assumption: one project measured 72, 89 and about ±150 between repeats and warned that a few hundred is not an effect, while another read the same number twice in a row on every pair it took. Call something a change only when the pair before and the pair after each agree with themselves.

```bash
# Two readings of the resident floor. Same prompt every time — the prompt is inside the number.
# `< /dev/null` is not optional: left off, the command waits on stdin and reads 335 tokens
# higher (28,230 against 27,895, measured back to back on 2026-09-09). Both are this
# project's own floor after its rule block went in — an example of the shape of the number,
# not a target: a project with different resident files reads a different one.
for n in 1 2; do
  claude -p "Do not call any tool. Answer with one word: ok." --output-format json --max-turns 1 < /dev/null \
  | python3 -c 'import json,sys; u=(json.load(sys.stdin).get("usage") or {}); print("floor", u.get("input_tokens",0)+u.get("cache_creation_input_tokens",0)+u.get("cache_read_input_tokens",0))'
done
# What it is made of, in characters
M="$HOME/.claude/projects/$(printf %s "$PWD" | sed 's/[^A-Za-z0-9]/-/g')/memory/MEMORY.md"
LC_ALL=en_US.UTF-8 wc -m "$HOME/.claude/CLAUDE.md" CLAUDE.md "$M" 2>/dev/null
```

Run it with a real python3, the same as §1. A floor reading is a **project** reading, not a session one: it belongs in the artifact (§6) beside the table, and it is the one number in this checkup that a second project can be compared against, because none of it depends on how anybody worked this week.

## 3. Backfill section G
Sweep the case library — **resolved in this order: the path on the line `ctx-kit case library: <path relative to the project root>` in the project root's `CLAUDE.md` if there is one, otherwise an existing `_ops/CASES/`, otherwise `cases/`** (the block in §4 resolves it in one line; the audit script prints the same answer under `# case library:`) — for cases whose section G says `(to be backfilled)` / `(待回填)`, and pair them up one at a time:
1. take the close-out moment from the case file's "updated" date and the file mtime;
2. in the project archive directory find the session around that moment carrying the **billing signature of a close-out round** — a single `cache_creation` ≈ that session's watermark, with no request after it;
3. once paired, write the jsonl path into section G, marked "reference only, do not read in full".

Two rules:
- **jsonl timestamps are UTC** — convert to the local timezone before comparing them with the local clock (one timezone out and you pair the wrong session).
- **If it does not pair, leave `(to be backfilled)` in place and say so.** Better empty than a path that merely "looks right" — using `ls -t` to point at yourself has been measured pointing at a file two weeks old.

## 4. Case size check
The measure = **what a takeover actually loads** (header line + A~D + E's active rows and latest verdict + I's header, its undisposed rows in full and the last three disposed ones), not "how big the file is", and not the old measure of "count up to E". Run the extraction command from `ctx-takeover` §2 on each case (swap `F=` for each case path) and `| tail -1` to take only the character count on the last line — **do not read the extracted body into context**; the checkup only needs the number. Skip decision appendices, experiment archives and TASKBOARD.

Criterion (relaxed by the owner on 2026-08-24, previously 7,000), in three bands: **≤10,000 characters per case is green**; **>10,000 and ≤15,000 is yellow** — name it and say it gets slimmed at that case's next close-out, it is not over the line; **>15,000 must be slimmed before the case changes hands**. The reading is characters, not bytes and not file size (a case written in Chinese runs about twice its character count in bytes). For every case over the line, report the number and name the pen-holding session to do the slimming — **and where the pen-holder cell names nobody** (blank, `(TBD)`, or `predecessor … retired`, which is the ordinary state after a predecessor retires) **there is no session to name: report it to the owner instead**, as a case over the line waiting for a successor, and never appoint one yourself. The slimming itself: move the old rows of table C out into that case's decision appendix / roll the old delivered rows of E into an archive (see `ctx-handoff`) / clear the settled items out of D / compress the chronicle in F; historical detail belongs in the transcript and the archives, not in the case.

**E row length check (report, do not fix)**: the Verdict cell and the Impact-on-plan cell are each ≤200 characters — **checked on the rows a takeover actually reads and on no others**: the rows at running / awaiting acceptance / queued / to dispatch, plus the single most recent delivered row — **most recent by ID (`E-10b-2` sorts before `E-11`), never by the order the rows sit in the table, and a row marked done counts as delivered here** — whose verdict is the only one the loader in `ctx-takeover` §2 carries across. An older delivered row never enters a successor's slice, so its length costs the successor nothing and the check leaves it alone. **A cell over the cap: put one sentence of verdict in it (≤200 characters) and the path to the deliverable beside it, and leave the account itself in the deliverable** — the ledger is an index, not a report. It is the same block `ctx-handoff` §3 runs on one case, pointed at the whole library instead. List the over-long rows in descending order of length (case file / row number / which cell / character count), reporting them to that case's pen-holding session to slim down themselves — **the checkup never edits somebody else's case**:

**Run it with a real python3**, the same as §1: an error mentioning `xcodebuild` or similar means the interpreter resolved somewhere else (the macOS Xcode shim, for instance) — run it again with a real python3; the block is not broken.

```bash
D=$(sed -n 's/^[^A-Za-z]*ctx-kit case library:[[:space:]]*//p' CLAUDE.md 2>/dev/null | head -1 | sed 's/[`[:space:]]*$//')
[ -n "$D" ] || { D=_ops/CASES; [ -d "$D" ] || D=cases; }
echo "# case library: $D"; python3 - "$D"/*.md <<'PY'
import sys,re,os
W=re.compile(r'(?<!\\)\|')  # split on unescaped pipes only: a \| inside a cell is content, not a separator (ctx-handoff §4 step 2). Four places carry this same split and must agree — the loader in ctx-takeover §2, the length block in ctx-handoff §3, this block, and split_cells in scripts/case-lint.py
def z(r):  # the cells of one markdown row
    p=[c.strip() for c in W.split(r.strip())]
    if p and not p[0]: p=p[1:]
    if p and not p[-1]: p=p[:-1]
    return p
A=re.compile(r'^\W*(在跑|待验收|排队|待派|running|awaiting acceptance|queued|to dispatch)',re.I)  # live
B=re.compile(r'^\W*(已交货|已完|delivered|done)',re.I)                                            # finished
w=[];F=[p for p in sys.argv[1:] if os.path.isfile(p)]
for p in F:
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
print(f'--- {len(F)} file(s) read from the case library; {len(w)} cells over 200 characters (reported, not fixed — the author slims their own) ---')
PY
```

If that last line reports **0 files read**, the library is not where the rule pointed: say so and stop — an empty sweep is not a clean sweep. Check the `# case library:` line above it against the `ctx-kit case library:` line in the project's `CLAUDE.md` (`_ops/CASES/` and `cases/` are only the fallbacks), and never report a case check you did not run.

**Split-the-case hint (a hint only, never a fail)**: if a case has >30 E rows, or >50 C decision rows added in the last 30 days, say one line — "consider splitting this case". **Both thresholds are rules of thumb and have not been verified**, so treat them only as a conversation opener; they are not criteria and they never count towards pass or fail.

## 5. Retirement-mark sweep
A session that marks itself at close-out carries the `✕` prefix. **A session that crashed or was abandoned never marks itself**, so this step catches up:
- list the sessions **whose working directory sits inside this project** — what the tool hands back is every project on this machine mixed together, and another project's session is never yours to mark, however dead it looks — and from those take the ones that are **neither the pen-holder of any case nor the carrier of any one-off**, have not moved for >1 day, and have no `✕` prefix in the title;
- `set_session_title` each of them to `✕ <original title>`. **Leave the doubtful ones alone** — better to miss one than to mark a live session dead, and a session you cannot place inside this project is doubtful by definition. If the title tool is unavailable (a bare terminal), or it cannot tell you a session's working directory, skip this step and say so in the reply.
- Report the numbers: N newly marked this period, M skipped as doubtful (named).

## 6. The artifact
**Write the run down, or it did not happen.** A checkup whose findings only ever appear in one reply is a checkup nobody can compare against next week — measured: a project that had had this script on disk since August had produced no file at all, so no reading it ever took outlived the turn it was printed in.

Where: **`CHECKUP/<YYYY-MM-DD>.md`, beside the case library** (case library `_ops/CASES/` → `_ops/CHECKUP/`), the date being the one `date` gave you at the top of this skill — `--out` creates that directory, so it does not have to be there first. Five parts, in this order:

1. **A head line**: the date, who ran it (the session's name), and **the command as it was actually typed** — the interpreter path spelled out, and any `--project` or `--cases` that was needed, so the next run repeats it instead of reconstructing it.
2. **The script's output, unchanged.** Use `--out <that file>` on the audit in §1 to write it and then build the rest around it, or paste the block whole; **do not restate the numbers in your own words and do not round them** — the artifact is the evidence, the reply is the summary.
3. **A disposition table for the flagged rows**: `session | which line | reading | baseline | what was done`. The baseline cell is what makes the file worth keeping: where there is no earlier reading to name, write **"no earlier reading"** rather than leaving it blank. Rows flagged for the same reason may be merged into one row saying how many, provided the merged row names the reason.
4. **The section G backfill result**: how many paired, how many stayed `(to be backfilled)` / `(待回填)`, and why each of the latter did not pair.
5. **The floor reading from §2**: the pair, the make-up in characters, and the difference from the last artifact's. It is a project reading rather than a session one, so it sits under the table instead of in it — and keeping it here is the whole reason next week's difference is knowable at all.

Then **point the board at it**: the `Last / next` cell of this routine's row in the board's routine table takes today's date and the artifact's path, which is where `ctx-status` reads it from. Say in the reply where the file went and how many characters it runs to.

## 7. Reply
One table (session / criterion / actual reading / pass or fail / recommended action) + one line of overall account: how many over the line this period, how many recommended for close-out, how many cases over the size limit, section G backfilled x/y, how many retirement checks passed, and where the artifact was written.
