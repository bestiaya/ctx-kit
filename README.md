# ctx-kit

**Who it's for:** work that **doesn't fit in one session** — it runs across days, fattens the session, or there's more than one job in flight. Work that ships inside one session doesn't need this.

Session lifecycle toolkit for claude CLI (Claude Code): 5 skills, a PreCompact reminder hook, a cache-audit script, a `digest` subagent, a CLAUDE.md rule block. One rule: **state lives on disk; the session — and the agent running it — is disposable.**

**[中文版 / Chinese](README.zh-CN.md)** · Skill prompts and the four deep-dive docs are Chinese-only for now; this README covers install and evaluation.

## Sound familiar?

**"My Claude subscription ran out mid-project — how do I keep going with a different agent?"**

Its everyday version: *"I opened a new session and want to pick up where the last one left off."* Same problem either way — the state lives in a session that is about to die. New sessions have amnesia, so you re-explain everything; the alternative, keeping the old fat session alive, costs more every time you return. Measured: taking over in a fresh session cost **7-8% of one cold re-entry** into the old one (~125k / ~101k equivalent units vs 1.62M / 1.38M). An 830k-watermark session fit in a **~14KB case file**, and the 3+1 spot-check passed **4/4** (one is a negative control for fabrication).

`/ctx-takeover C-07` reads only the case file, never the old transcript, then recites the state back for you to spot-check first.

And the case file is plain markdown with nothing Claude-specific in it, so the successor doesn't have to be Claude: a different coding agent after your subscription lapses, another machine (close-out commits and pushes, so state travels with the repo), or a teammate — same file, recital and spot-check done by hand. Smoke-tested once — Codex took over a live case and passed the spot-check, negative control included. The cost numbers above are Claude-to-Claude.

**"This session has burned through half its context, now what?"**

Long sessions cost more the longer you keep them, and the money leaks where you can't see it. In two audited long-lived sessions, **56-57% of spend** went to re-writing the same content into cache, the same passage **9-13 times**, while the in-session cache hit rate was already **>99%**. No knob to turn. Cost is the measured half; on quality, the vendor's own docs acknowledge context rot — accuracy and recall degrade as tokens grow — but give no percentage, and neither do we: the 150k/200k lines in this kit are set by cost. `compact` isn't the fix either: it keeps the context and drops the detail (one measured auto-compact **lost 98.8%** of it). What you want preserved is *state*.

`/ctx-handoff` distills the session into a case file someone can take over, persists what hasn't reached disk, then retires the session.

**"I want one place that tracks everything I'm working on."**

Several jobs in flight, no ledger, no answering "where do things stand?" without digging. In the two close-out pilots, **7 and 14 items** had been discussed but never written down; one pilot also self-reported 3 bookkeeping errors and 2 irreproducible numbers.

`/ctx-kickoff` triages (case / one-off / quick fix) and opens the file on the spot. `/ctx-status` reads the board and the case files and reports in plain language.

**"I want to hand a job off to the next session."**

Subagents don't keep the parent warm: across 119 transcripts, **0** subagent requests landed on the parent's bill, and the parent still pays watermark × 2 when you return. Don't dispatch subagents from a high-watermark session.

`/ctx-kickoff` ends with one question, discuss here or dispatch it. Answer "dispatch" and it writes the self-contained brief for a fresh session to pick up.

## Do you need it? Three questions

The three questions are one question: **is the work bigger than one session?**

1. **Will this session get fat?** — tens of thousands of tokens, kept alive across days.
2. **Does the work outlive the session?** — you'll continue tomorrow, in another session, another agent, or another machine.
3. **More than one job in flight?** — you need one place that answers "where do things stand".

**Work that looks like this is "bigger than one session":**

- **A bug hunt in its third day** — hypothesis, test, rule out, repeat; every morning you re-explain what's been tried → the case file is the lab notebook; a fresh session reads it and picks up the hunt.
- **Research and tech selection** — gather, compare, verify, decide; conclusions scattered across a dozen sessions → decisions land in one place with their "why"; no archaeology six months later.
- **A large refactor / migration** — hundreds of files in batches, several sessions in parallel → a ledger plus per-wave spot checks; the orchestrating session dispatches and never edits.
- **Several jobs in flight** — projects, clients, side projects → one board; ask "where do things stand" and get an answer.

Three no's — a quick, low-exploration job that ships inside one session (a PRD, user stories, a chunk of code) — **you don't need ctx-kit. Don't install it.** Each "yes" switches on one layer: (1) the economics rules, (2) the case file, (3) the board. Which workloads use which layers: 02-METHOD ch. 5 and the playbooks in 04.

## What it is, what it isn't

Conclusions get written to a file as they are made, so any session can be closed and reopened at will. **The principles work without the tooling**: by hand it works identically, and the skills only remove "remembering to do it" and "remembering how".

It is **not** a cache-tuning tool (in-session hit rate is already >99%, nothing to tune), and it doesn't change how you write code. It governs when a session opens, when it closes, and where the state lives.

## Install

Three steps — two commands, one paste:

```bash
claude plugin marketplace add bestiaya/ctx-kit
claude plugin install ctx-kit@ctx-kit
```

Third step (manual, required): paste the code block from [CLAUDE-snippet.md](CLAUDE-snippet.md) into your project `CLAUDE.md` (or `~/.claude/CLAUDE.md`). The plugin ships the skills, the hook, the audit script and the `digest` subagent — but resident rules can't ship in a plugin, and the kit's proactive behaviors (triage first, auto-dispatch big reads, offer to close out past 150k) live in that snippet.

<details>
<summary>Manual install (no plugin)</summary>

```bash
KIT=path/to/ctx-kit
mkdir -p .claude/skills .claude/agents
cp -R "$KIT"/skills/ctx-* .claude/skills/
cp    "$KIT"/agents/digest.md .claude/agents/
```

Then merge the `hooks` object from `hooks/hooks.json` into `.claude/settings.json` (macOS notification, stderr fallback elsewhere), paste the snippet as above, and run the audit script from wherever it lives: `python3 <path>/cache-audit.py --all`.

</details>

Three self-checks afterwards:

1. In a fresh session say "I want to do X". Does it triage before acting?
2. Hand it a >30k read. Does it dispatch the `digest` subagent instead of reading inline?
3. Grow a session past 150k. Does it offer to close out? If not, `CLAUDE.md` isn't loaded.

Case files live in `_ops/CASES/` if it exists, otherwise `cases/`.

## The five skills

| Skill | Triggers on | What it does |
|---|---|---|
| **ctx-kickoff** | "I want to do X" | Triage, open the case file, then one question: discuss here or dispatch it |
| **ctx-handoff** | "close out", "this session is too full" | Case file someone can take over plus an un-persisted list, persist artifacts, retire the session |
| **ctx-takeover** | "take over C-07" | Case file only, transcript off-limits; sign as pen-holder, four-layer recital, your spot-check |
| **ctx-status** | "what's the status", "show the board" | Reads board and case files: goal chain, case states, open decisions, one-offs |
| **ctx-checkup** | "weekly checkup" | Runs the cache audit, flags sessions over the line (repeated-rewrite share **<10%** passes), backfills archive pointers |

## Docs

All four are **in Chinese**.

- **01-BACKGROUND.md**: the measurements, five paired comparisons; measured findings and untested rules of thumb kept strictly apart.
- **02-METHOD.md**: context and cache principles, the artifact system, goal chains, principle-to-skill map, scope.
- **04-HANDBOOK.md**: operations, one section per question above, plus workload playbooks (research / feature dev / batch / ops / multi-session messaging), the 3+1 spot-check recipe, and troubleshooting.
- **05-FAQ.md**: objections one at a time, including why the "50-60% and it gets dumber" figure is not used here.

## Uninstall

Plugin install: remove ctx-kit in `/plugin`, then delete the snippet block from your `CLAUDE.md`. Manual install: `rm -rf .claude/skills/ctx-* .claude/agents/digest.md`, plus the blocks you pasted into `CLAUDE.md` and `.claude/settings.json`. Nothing else is left behind.

## Glossary

Fuller version in 02-METHOD (Chinese).

- **case file**: one markdown file holding everything needed to take a piece of work over.
- **close out**: write a session's state to disk, then retire the session.
- **take over / session succession**: retire the fat session; a fresh one continues from the case file alone.
- **context watermark**: how much of the context window a session is using.
- **cold-restart cost**: the first request after cache expiry costs watermark × 2, whatever the gap.
- **compact**: the client's built-in session summarisation. Its own cost isn't logged and is locally unmeasurable.
- **equivalent units**: the billing unit here, input×1 + cache_read×0.1 + cache_write×2 + output×5.
- **context rot**: the vendor's name for accuracy and recall degrading as token count grows; no percentage threshold is given. The 150k/200k lines here are set by cost, not quality.

---

<sub>Measured 2026-08-18 on claude CLI · 1M context window · Opus/Fable tier. Sample: two long-lived sessions, 704 raw request log lines. Change model or client and re-measure: run `scripts/cache-audit.py --all` on your own logs, check TTL bucket duration, write-price multiplier, shared-header byte count.</sub>
