# ctx-kit

中文 / Chinese: [README.zh-CN.md](README.zh-CN.md) · The six skill prompts are English (a frozen Chinese reference copy, `SKILL.zh-CN.md`, sits beside each — a snapshot that lags the English original, and its first line says which release it was frozen at); docs 01–06 are in Chinese for now.

**ctx-kit is for work that doesn't fit in one session. If your work ships inside one session, you don't need it.**

## TL;DR

**In one line**: a session lifecycle toolkit for claude CLI — it makes "state lives on disk, the session is disposable" the default action, so the work outlives the session. (claude CLI is the agent you talk to: it runs the model, carries the tools, keeps the session. The model can be swapped; your session lives in that layer.)

**Where it works**: built for claude CLI (Claude Code) — the six commands are its skills, and the hook and the audit script read its session logs. Case files are plain markdown, so another agent can read them: Codex took over a live case once. The command layer for Codex doesn't exist, though; that would be a separate build.

**Who it's for**: people who use an agent for work bigger than one session — writing code, product design, research, writing. Work like that gets more expensive the longer a session runs, has to survive a change of session, of agent, even of machine, and rarely arrives one job at a time. Quick work that ships inside a single session — a PRD, a set of user stories, a chunk of code — doesn't need any of this.

**Three problems it solves**:

1. Context overload in long sessions: the money goes into re-writing what has already been said back into cache; let the session go cold, come back, and you pay for the whole thing again; auto-compact keeps the thread and drops the detail.
2. The information cliff when you change session, model or machine, or get auto-compacted — and have to tell the whole story again.
3. Recording, tracking and resuming several jobs at once, and passing word between them (this is the cross-session messaging built into claude CLI — SendMessage / ListAgents since v2.1.224 (2026-08-07), idle subscription notify_when_idle since v2.1.236 (2026-08-19)) — no secret sauce, all of it ships with the agent (how to arrange several sessions and pass word between them: [recipe 5](06-RECIPES.md#配方-5多会话并行--跨会话通讯) and [sample B](06-RECIPES.md#样例-ba-会话定标准b-会话执行a-有新想法怎么告诉-b) in 06).

**The data** (four measurements; each link opens the source and the sample):

- A fresh session picking the work up spends **7-8%** of what one cold re-entry into the old session costs ([01 §3.4](01-BACKGROUND.md#34-对照-2继续养着老会话--收口换生))
- **56-57%** of a long session's total spend buys one thing: saying again what was already said ([01 §3.3](01-BACKGROUND.md#33-对照-5调缓存参数--改生命周期纪律))
- One auto-compact dropped **98.8%** of the detail ([01 §3.6](01-BACKGROUND.md#36-auto-compact-实录与-compact-的账面盲区))
- A session grown to 830k tokens: everything needed to take it over fit in **one ~14KB file** ([01 §3.4](01-BACKGROUND.md#34-对照-2继续养着老会话--收口换生))

---

## Sound familiar?

### "Now I have to explain it all over again"

**What it solves**: you hit a usage limit, it died mid-task, the context filled up and got auto-compacted, you moved to another machine, another model, another agent — after any of those the work continues, without you re-telling the story.

**In their words** (typical phrasing from a three-source sampling of public discussion; users' own words, nothing tied to a person):

> - It "forgets everything between sessions" — I told it that yesterday.
> - It's like "babysitting an intern with amnesia".
> - It "died mid-task"; I "hit the limit" and the job stopped halfway.
> - "Every session starts cold", so I keep my own note about "where I left off".
> - Move to another machine and it can't pick up — the memory is written into a local directory, and the transcript itself goes stale.

**The data**: a fresh session picking the work up spends 7-8% of one cold re-entry into the old one; a session grown to 830k tokens fit its entire takeover-ready state into one ~14KB file (both readings from 01 §3.4, Claude taking over from Claude).

**How it goes**:

1. While you work, it writes each conclusion straight into a **case file** — one md file holding the whole state of this job: the goal, what has been settled, the dead ends, the next step.
2. When the session should be thrown away, say "close out" (`/ctx-handoff`): anything that hasn't reached the file goes in now, and the session retires.
3. Open a fresh session and say "take over C-07" (`/ctx-takeover C-NN`): it reads that file and nothing else — old transcripts are off-limits — then recites the goal and the state back for you to spot-check.
4. Moving to another machine or another agent is the same move; the file is plain markdown, and Codex took over a live case once. If you want a different model, don't switch inside the old session: measured once, not a single cached token came back (01 §3.8).
5. If you'd rather hand the job off, tell it first (`/ctx-kickoff`): it asks you exactly one question — discuss it here, or write it up as a brief and dispatch it to a fresh session.

### "The longer I keep this session alive, the more it costs"

**What it solves**: three kinds of wasted money — let a session go cold and coming back re-bills the whole context; keep a long session alive and most of the money buys a re-copy of what was already said; let auto-compact take over and the detail goes with it. One move removes all three: close out in time, take over in a fresh session. Being able to see the bill is a side benefit.

**In their words** (same sampling):

> - A long session gets more expensive the longer you keep it; the money buys nothing new, it buys a re-copy of what was already said.
> - You come back after a break and the whole context is billed again ("the prompt cache has expired").
> - "Auto compact is the worst" — the summary lands and the detail is gone ("the summary is lossy").
> - You hit a limit and still can't see where the tokens went ("Real cost, no visibility").
> - "Spending more time managing the AI" than doing the actual work.

**The data**: leave a session for an hour or so, come back, and the whole context is paid for again — that one re-entry costs your watermark × 2 (01 §3.2). Audit two long-lived sessions and 56-57% of the total spend went into re-writing the same content into cache (01 §3.3). Compact preserves "we can keep talking" and drops the detail — one measured run lost 98.8% (01 §3.6). Close out and take over instead, and the successor's opening round costs 7-8% of one cold re-entry (01 §3.4). That is what those three leaks look like once they are plugged.

**How it goes**:

1. When a session gets expensive it asks whether you want to close out — it only closes when you say "close out" (`/ctx-handoff`); then a fresh session takes over and carries on. **That one move is where the money is saved**, and the earlier you make it the more you keep.
2. Don't lean on compact. It preserves "we can keep talking"; what you need preserved is the conclusions and the state. Close a session when it's done instead of putting it on life support.
3. Don't dispatch subagents from an expensive session — the moment one comes back, the whole context is billed again at whatever it weighs by then.
4. Check the bill once a week: say "weekly checkup" (`/ctx-checkup`) and it lists where the tokens went and which sessions should be closed, so you can confirm the money went where you wanted it to go.

### "Several sessions in flight — which one is waiting on me, and how far did it get?"

**What it solves**: when several jobs are moving at once, one place answers "where do things stand" — what is waiting on your decision, what is finished, what got discussed and never landed.

**In their words** (same sampling):

> - Two sessions running and "no idea what the other session just changed" unless I go and look.
> - One session refactors the helpers while the other writes tests for them, and merging the two is a mess.
> - Several sessions open, and working out which one needs a decision means "cmd-tabbing between terminal tabs".
> - The project grows, the next step slips, and you end up "not knowing how much is actually finished".
> - What you discussed is scattered across sessions, and a to-do said out loud is a to-do lost.

**The data**: in one pilot, closing out turned up a whole list of things that had been discussed but never written into any file (01 §3.4), and a few bookkeeping errors got self-reported along with it. Without that sweep, all of it leaves with the session.

**How it goes**:

1. At the start of a project, say "new project" (`/ctx-init`): it reads your own docs first, proposes what the project is for, which milestones it has and which routines keep running, on a single screen with a source cited per cell, and writes nothing until you nod.
2. After that you just say what you want (`/ctx-kickoff`): it triages by itself — whatever needs following up gets a file on the spot, whatever one session can finish gets a line.
3. Park a to-do with "note this down"; it files it where it belongs and tells you where it went.
4. To find out where things stand, ask (`/ctx-status`): it reads everything on record and reports back in plain language.
5. When a job is done, "close out" also means closing the case: marked closed, with a last sweep for anything discussed but never written down.

These three weren't invented at a desk. They were grouped out of what users themselves complain about on X, GitHub and Reddit; how the grouping was done and how big the sample was is the last row of the evidence table below.

---

## Do you need it? Three questions

The three questions are one question: **is the work bigger than one session?**

1. Will this session get more expensive the longer it lives? — you talk to it until you can't bear to close it, and you're back tomorrow.
2. Does the work outlive the session? — you'll continue tomorrow, possibly in another session, another agent, even another machine.
3. Is more than one job in flight? — you need one place that answers "where do things stand".

This is what work that doesn't fit looks like:

- A bug hunt in its third day: hypothesis, experiment, rule out, repeat. The case file is the lab notebook; a fresh session reads it and picks the hunt up.
- Research and technology selection: the decisions land in one place together with their "why", so nobody has to do archaeology six months later.
- A large refactor or migration: hundreds of files in batches, several sessions in parallel, with the ledger and the per-wave spot checks in the files.
- Several things moving at once: a project, a client and a side project all in flight together, with one board to answer "where do things stand".

Three no's — say, a quick job that ships inside one session — and **you don't need ctx-kit; don't install it**. Whichever question is a "yes" switches on that layer: (1) the cost discipline, (2) the case file, (3) the board. Which kind of work needs which layers is in 02-METHOD ch. 5.

Three objections come up often, so here are my answers. ① "Just copy-paste and ask it to summarise" — I have not run a controlled comparison between summary handoff and case files, so I don't claim a winner; that boundary is written down in 05-FAQ Q22. ② "A handoff file depends on discipline, and a few hours later you get lazy" — true, which is why closing out is one command and the spot-check is a required step: the discipline lives in the skill, not in your memory. ③ "I've never had these problems" — most likely true. Your work hasn't outgrown one session yet, and three no's means don't install it.

## What it is, what it stands on, what it isn't

One rule: **state lives on disk, the session is disposable** — conclusions get written into the file as they are made, so any session can be closed and a new one opened at will. That rule wasn't reasoned out — I ran into it, the day a subscription expired mid-flight and a pile of unfinished work sat locked inside a dying session (the story is in 05-FAQ Q23).

It believes five things:

- **A session is a consumable; the work is the thing** — for work to outlive a session, its state has to live in a file outside it.
- **Two roots, one direction** — cost says "keep the watermark low, work in one stretch, then throw it away"; continuity says "the state has to be on disk". Both point at the same move.
- **Discipline before tooling** — every practice here holds without installing anything, and by hand it works just as well; the kit only removes "remembering to do it" and "remembering how".
- **Verifiable beats describable** — numbers carry a source, the wording stays within what the evidence supports, and a handoff has to survive a spot-check.
- **You do three things only** — say what you want, ask where things stand, make the calls; the model judges the rest. And it says up front when you don't need it.

The concept model is one sentence: state lives in three things — the board, the case, the artifact — and the session can be thrown away at any time (each of those words is explained in the glossary at the end).

The board is one file per project, and you keep it by hand: the overall goal, a **milestone** table (one line each — what is true once it lands, plus its status), a **routine** table (rhythm, health reading, last / next), an index of the cases, and the one-offs that aren't worth a case. Milestones are labels, not a layer above the cases: a case or a one-off carries one or more of them, and work that fits none of them is written down as a "candidate milestone" for you to decide on — add a milestone to the plan, or drop the work. `/ctx-init` proposes the header and you confirm it; after that each case edits its own row. Generating the board from a script is optional, and nothing here depends on it.

Along the way you get planning and task management that is good enough — the third scenario above is exactly that. It doesn't schedule dates, doesn't allocate people, doesn't keep a risk register; one case is one markdown file, and there is no system.

What it doesn't solve: it isn't a cache-tuning tool (inside a session the cache hits almost every time, so there is nothing left to tune), and it doesn't change how you write code. It governs when a session opens, when it closes and where the state lives. It also isn't a cross-agent tool: the commands and the hook exist only inside claude CLI, and moving to another agent means taking the files with you (Codex took over a live case once) and building that command layer again over there.

One honest boundary: the yellow and red watermark lines **are set by cost, not by quality**. On the quality side there is only the vendor's qualitative acknowledgement — more tokens, worse accuracy and recall (context rot; no official percentage anywhere). This kit has measured none of that locally and doesn't use it as the basis for any threshold (see column two of 01).

## Why believe it: the paired comparisons

Eight comparisons; click a row and you land on that subsection of 01, with its readings and its sample.

| Comparison | One side | The other | Verdict |
|---|---|---|---|
| [1 warm re-entry \| cold re-entry](01-BACKGROUND.md#32-对照-1热回访--冷回访) | back within 15 minutes: all warm | after an hour away: 147 of 160 cold | the tax is on the watermark, not on how long you were gone |
| [2 keeping the old session \| closing out into a new one](01-BACKGROUND.md#34-对照-2继续养着老会话--收口换生) | one cold re-entry into the old session: 1.38M / 1.62M equivalent units | the successor's opening round: 101k / 125k | taking over costs 7-8% of going back once |
| [3 no compact \| compact and keep going](01-BACKGROUND.md#35-对照-34压缩到底划不划算) | six requests, ~478k equivalent units | ~283k after compacting | it pays back on the 2nd request |
| [4 compact then leave \| compact then keep going](01-BACKGROUND.md#35-对照-34压缩到底划不划算) | a rebuild paid for and never used | see the row above | compacting then leaving is a pure loss; close out and take over instead |
| [5 tuning cache settings \| changing the lifecycle discipline](01-BACKGROUND.md#33-对照-5调缓存参数--改生命周期纪律) | in-session hit rate already above 99% | repeated re-writes are 56-57% of total spend | all the leverage is on the discipline side |
| [6 same model \| switching model mid-session](01-BACKGROUND.md#38-对照-6同模型接续--换模型接续切模型缓存实测) | same model, the cache is still read | switch and not one cached token comes back | caches are model-scoped; switching means paying for the whole context again |
| [7 reading the whole case file \| progressive loading](01-BACKGROUND.md#39-对照-7整读案文件--渐进加载) | whole file: most of the characters go to old experiment rows | header, first four sections and the active rows only | takeover reports how much it loaded; trim when that gets large |
| [8 the author's own scenarios \| users' own words (three-source sampling)](01-BACKGROUND.md#310-对照-8作者自述场景--用户自述痛点三路取样) | an earlier draft: four scenarios written by the author | 220 items sampled from three streams of public discussion: session about to die 74 / long sessions expensive 55 / one place for all the work 30 / dispatch a job 22 / other 39 (18 of those dissenting) | the first two are real pain; the last two are quiet, and "dispatch" folded into "take over" |

Every number comes from 01, which also defines "equivalent units" — the one billing unit that puts writes, cache reads and output on the same scale. The first seven comparisons can each be recomputed with a script; the eighth is a sample count, and its method and limits are written up in 01 §3.10.

## What gets installed

What goes in: six skills, one CLAUDE.md rule block, one reminder hook, one audit script and one `digest` subagent.

**Check your version first** — `claude --version`. What each layer needs (versions from the [claude CLI changelog](https://github.com/anthropics/claude-code/blob/main/CHANGELOG.md)):

| What it powers | Minimum version | If yours is older |
|---|---|---|
| Skills — the six commands themselves | v2.0.20 ("Added support for Claude Skills") | Nothing here runs; `claude update` first |
| Installing as a plugin (`claude plugin …`) | v2.0.12, when the plugin system shipped — the changelog doesn't date the `claude plugin` command-line form itself | Use `/plugin` inside a session, or install by hand (below) |
| Cross-session messaging — `SendMessage` / `ListAgents` | v2.1.224 on macOS and Linux; native Windows v2.1.239 (the changelog entry "Windows: cross-session messaging is now available") | Only the several-sessions-at-once recipe is affected; everything else runs |
| Idle notice — `notify_when_idle` | v2.1.236, macOS and Linux | You go and ask "done yet?" instead of being told |
| Session titles in the UI | No version line — the Desktop app has the title tool, a plain terminal doesn't | Titles are skipped and it says so; the pen-holder line in the case file is the real handoff signal |

Three steps — two commands and one paste:

```bash
claude plugin marketplace add bestiaya/ctx-kit
claude plugin install ctx-kit@ctx-kit
```

Third step (manual, required): paste the whole code block from [CLAUDE-snippet.md](CLAUDE-snippet.md) into your project `CLAUDE.md` (or `~/.claude/CLAUDE.md`). A plugin can ship skills, a hook, a script and a subagent — it **cannot ship a resident rule block**, and the proactive behaviour — triage before acting, hand big reads to a subagent, offer to close out past the line — depends on those rules being resident.

**One side effect to know before you install**: closing out (`/ctx-handoff`) doesn't only write files — it `git add`s the files this session edited, commits them and **pushes** to the current branch's upstream. On a protected or shared branch, decide where you want that to land before you start. If it can't push (no remote, no permission, a conflict, not a git project at all) it says "not pushed + why" in the reply rather than going quiet. And if your case library sits in a git-ignored directory — this repository's own does — the case files are written to disk and never committed: close-out reports that too, it is a legitimate setup rather than a failure, and syncing that directory to another machine is then your job.

<details><summary>Manual install (no plugin)</summary>

Copy `skills/ctx-*` into `.claude/skills/`, `agents/digest.md` into `.claude/agents/` and `scripts/cache-audit.py` into `~/.claude/scripts/` (create the directory if it is not there — with no plugin root, that is the one place `ctx-checkup` looks for the script), then merge the `hooks` object from `hooks/hooks.json` into `.claude/settings.json` (macOS shows a notification; elsewhere it falls back to stderr). Paste the rule block as above.

After every `git pull`, `scripts/sync-installed.sh --check` lists where the installed copies have drifted from the repository, and `--apply` copies the repository over them — backing up whatever it overwrites into `~/.claude/ctx-kit-backup-<timestamp>/` first, and never deleting anything. (For maintainers, `scripts/release-check.py` checks that the version number, the skill count and the skill names agree across the plugin manifest, both READMEs and the docs before a release.)
</details>

Three self-checks afterwards:

1. In a fresh session, say "I want to do X" and watch whether it triages before it starts working.
2. Hand it a >30k-character read (`LC_ALL=en_US.UTF-8 wc -m`) and watch whether it dispatches the `digest` subagent instead of reading it inline.
3. Grow a session past the yellow line and watch whether it offers to close out — if it doesn't, the rule block isn't loaded.

**Upgrading from an earlier version**: this one renames the board's second section from "Global plan" to a **milestone** table plus a **routine** table. An existing board does not have to be rebuilt — run `/ctx-init` again and its review mode proposes the rename, keeping the rows you already have. The manual steps — where the rows of the old "track" layer go, how the case index gains its seventh column — are [recipe 7](06-RECIPES.md#配方-7老板面迁到新板里程碑--例行) in 06.

**Uninstall**: remove ctx-kit in `/plugin`, or for a manual install `rm -rf .claude/skills/ctx-* .claude/agents/digest.md ~/.claude/scripts/cache-audit.py ~/.claude/ctx-kit-backup-*` (the last one is the backups the sync script keeps). Then delete the blocks you pasted into `CLAUDE.md` and `.claude/settings.json` — that is everything the kit puts on your machine. What stays behind is yours, not the kit's: the board and the case library `/ctx-init` created, and the commits and remote history `/ctx-handoff` pushed. Nothing deletes those for you; keep them or clear them yourself.

## The six commands

Six skills, six commands. Saying it in plain words and typing the command are the same thing.

| When | Say | What it does |
|---|---|---|
| Starting a project | "new project", or `/ctx-init` | Reads your own docs first, proposes the goal, the milestones and the routines with a source cited per cell, writes nothing until you confirm |
| Something new to do, or a to-do to park | "I want to do X" / "note this down", or `/ctx-kickoff` | Routes it to case / one-off / quick fix, creates the case file on the spot, then asks one question — discuss here or dispatch |
| This session is getting expensive, or a batch of work is done | "close out", or `/ctx-handoff` | Distils the discussion into a takeover-ready case file, persists whatever hasn't been saved, **commits and pushes the files it touched this round**, then retires the session |
| A fresh session continuing the last one | "take over C-07", or `/ctx-takeover C-NN` | Reads the case file only, old transcripts off-limits; signs as pen-holder, recites goal, case, progress and next step for your spot-check |
| You want to know where things stand | "what's the status", or `/ctx-status` | Reads the board and the case files, reports the goal chain with its milestones and routines, where each case stands, pending decisions and one-offs in plain language |
| Once a week, checking the bill | "weekly checkup", or `/ctx-checkup` | Runs the cache audit, flags the sessions over the pre-registered lines, backfills archive pointers in the case files |

Case files live in `_ops/CASES/` when that directory already exists, otherwise in `cases/` — or anywhere you like: put one line, `ctx-kit case library: docs/cases`, in your project `CLAUDE.md` and all six skills read it from there.

## Reading order

1. [README.md](README.md) (this file) — whether to use it, and how to start.
2. [04-HANDBOOK.md](04-HANDBOOK.md), the quick guide — step by step: how to use it and what it can do.
3. [06-RECIPES.md](06-RECIPES.md), best practice and worked samples — recipes per kind of work, making the use cases concrete.
4. [02-METHOD.md](02-METHOD.md), the method — why it is designed this way, with the criteria and the thresholds.
5. [01-BACKGROUND.md](01-BACKGROUND.md), background and measurements — the single source of every number here, with measured and un-measured kept strictly apart.
6. [05-FAQ.md](05-FAQ.md), answers — one real question at a time, including "where did this come from" and "does ordinary development need it", plus whether a few popular claims hold up.
7. [03-PLAYBOOK.md](03-PLAYBOOK.md), the tool-definition template — how this tool got defined, written for people building tools; users can skip it.

Docs 01, 02, 04, 05 and 06 are in Chinese for now.

## Words used here

- **board** — one per project, kept by hand: the overall goal, a milestone table, a routine table, an index of the cases, and the one-offs; one line each.
- **milestone** — one line in the board's milestone table: what is true once it lands, plus its status. It is a label a case or a one-off carries, not a layer above them; work that fits none of them is written down as a "candidate milestone" for you to decide on.
- **routine** — one line in the board's routine table: something you keep doing to a rhythm, with a health reading and last / next. No finish line and no ledger; when a routine turns up a problem worth converging on, that problem gets a case.
- **case / case file** — one problem area worth converging on, one md file each: goal, plan, decisions made, decisions waiting on you, the experiment list, handoff notes.
- **one-off** — a job not worth a case: one line on the board and one deliverable; it carries a milestone like a case does.
- **artifact** — an attachment to a case or a one-off: task briefs, raw data, deliverables, drafts; one file each, append-only.
- **experiment row** — one line in a case's experiment list: what it asks, how far it got, the verdict, what it changed in the plan.
- **session** — one conversation between you and claude CLI; a temporary carrier, not a ledger.
- **close out** — settle a session's state onto disk; the session retires immediately after.
- **take over** — a fresh session picks a case up from the case file alone: signs for it, recites it, waits for your spot-check.
- **dispatch** — hand a well-defined job off as a self-contained brief, and only look at what comes back.
- **compact** — the client's built-in move that squeezes a long session into a summary: it keeps "we can keep talking" and drops the detail.
- **subagent** — a temporary session the main one sends out for a small job; it returns the result and nothing else.
- **watermark** — how much context a session has used (in tokens); a "high watermark" session is one past the line.
- **agent** — the layer of software that runs the model, carries the tools and keeps the session; claude CLI (Claude Code) is one of them. The model can be swapped; your session lives in this layer.

---

<sub>Data source: measured 2026-08-18 (claude CLI · 1M context window · Opus/Fable models). Before you change model or client, run `scripts/cache-audit.py --all` over your own logs and re-measure three numbers: TTL bucket duration, write-price multiplier, shared-header byte count.</sub>
