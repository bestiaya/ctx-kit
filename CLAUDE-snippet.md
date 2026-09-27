# Rule blocks to copy: context and workflow, and output for the owner

Paste the whole of the first code block below into your project `CLAUDE.md`, or into the user-level `~/.claude/CLAUDE.md` (put it at user level if you want every project to run under this discipline).

The rules only say *what* to do; *how* lives in the seven skills — **a skill's body enters the context only when it is invoked, whereas the rule block is resident**, so the shorter the rules the better. Do not copy skill content into them.

```markdown
## Context and workflow
- State lives on disk, sessions are disposable: write a conclusion down as it happens (a decision → the case's
  section C, a change of plan → the case's section B); do not wait for close-out to write it.
- Every job is goal-directed: line the goal chain up first (top-level goal → milestone / case → this action, read
  the board header), then act; a job that hangs off no milestone is listed separately for review.
- On hearing "do X", triage first: needs discussion or several rounds of experiment → open a case (ctx-kickoff;
  case directory = the `ctx-kit case library:` line in this file if there is one, else `_ops/CASES/`, else
  `cases/`); one pass of execution → one row on the board (hung off a goal milestone) + dispatch a new session;
  a quick small change → just do it.
- Dispatch criteria (the core variable is **directional uncertainty**, not duration): ① a fork in direction
  (design / exploration, the owner may have to steer mid-way) → its own session + a self-contained task brief that
  explicitly marks the "owner stop-and-wait point"; ② a deterministic experiment (pre-registered, closed, nothing
  awaiting decision + read-only or writing only to the experiment area + simple and one-shot) → an inline subagent
  in this session, reporting the result only; ③ an N-arm comparison → one throwaway thin orchestration session;
  ④ heavy but certain (long mechanical volume) → its own session, no stop-and-wait point, delivery pulled rather
  than pushed. A subagent cannot talk to anybody mid-run, so any job that might need the owner must never be inline.
  **A high-watermark session is nobody's parent** (the cold tax of waiting on a subagent = the dispatcher's watermark × 2).
  Three lengths, because all three land whole in somebody's context: **the dispatch prompt is ≤800 characters**
  (brief path + a pointer to the rules + one line of reply contract, and never a retelling of the brief — a retelling
  is the brief paid twice); **a subagent replies in ≤1,500 characters, in three parts** — one line per pre-registered
  criterion, three key readings, and a pointer to the report; **a cross-session message is ≤1,500 characters** plus a
  file pointer. Detail stays in the file; the one limit that matters most ("this reading shows X, not Y") is never
  the thing cut to save characters.
  Writing is split by size and by whether it needs a source read, never by being writing: **anything under 1,000
  characters that needs no read you write yourself** (one dispatch costs more in fixed overhead than it saves), a
  brief over 3,000 characters or anything needing the sources read goes out — and **the wording of pre-registered
  criteria and of decisions is always yours**, with a subagent expanding scaffolding and format around it.
- Cross-case / cross-session delivery — looking the address up and sending are **one indivisible sequence**:
  (1) any address read earlier is **void**, however few minutes ago, and anything coming in between means you
  look it up again; (2) read the **target case file's** header Pen-holder cell now — the session named in an
  inbox row is the signature, not the address; (3) **immediately before sending**, check that session with
  get_session / list_sessions — and in the same list ask whether the cell is merely out of date: filter to
  titles under this project's working directory matching `^(?:✕\s*)?(?:(\d+)-CNN|CNN-(\d+))` (`CNN` = the case
  number with its hyphen out, `C-07`→`C07`; the second form is only for a project that renamed its own
  convention part way), drop `✕` and archived, and if the **latest** live one is not that cell's session then
  the cell names an earlier stint — send to the latest and say so in a line (where both forms are in use a
  `CNN-NN` title is later than any `NN-CNN` one; inside one form the larger number is later). That
  redirects the address; it is not a fourth refusal condition; (4) **refuse to send if any one of these holds**: the title starts with `✕`
  (the retirement mark); `isArchived` is set; or the case header's Pen-holder cell names nobody live (awaiting
  takeover / closing / predecessor retired) — a retired session is not necessarily unreachable, so this check
  has to come before the send. **All three are asked of the address (3) left you**: where the redirect found a
  live session of this project titled for this case, somebody live does hold it and you send there; (5) where
  you refused, **append** a row to the target file's **inbox** (append
  only, never touch the body, so two pens never write over each other) and tell the owner in one line that the
  case has no live pen-holder, asking whether to open a session for it — **and where you did send, no inbox row
  is written**: the letterbox is for a case nobody can receive on, not a copy of every delivery; (6) only once all of it passes, send,
  addressing by title plus working directory (the session id is the signature and the tie-breaker, not the address).
  Those three are the whole of the refusal list — **whether the pen-holder has been active within the hour is
  a cost reading, not a fourth condition**: a session that has gone cold is billed at its watermark × 2 on the
  next request, worth weighing before you ring anybody, and never a reason to hold a delivery back from a live
  pen-holder. A `✕` noticed only afterwards, on a reply that comes back, means the message has already gone
  astray: the symptom of having skipped (3) and (4), never a substitute for them.
  To get at what a dead session knows, **read its archive, do not wake it**
  (reading the archive costs only the reader; waking it costs watermark × 2).
  Do not chase progress after dispatching: subscribe to notify_when_idle on the exec session (a zero-token idle
  bell, CLI ≥2.1.236) and read only the deliverable when the notification arrives; a high-watermark discussion
  session can set crossSessionInbound to hold so an incoming message does not wake it and start billing.
- Read-once material of **more than 30,000 characters** (`LC_ALL=en_US.UTF-8 wc -m`; 30,000 exactly is under the line, so
  it stays here) goes to the digest subagent, and you take back a ≤5,000-character summary only; the working set (the
  deliverables this batch chews on repeatedly) is not subject to this.
- An exec session calls set_session_title first thing, naming itself as it appears on the board; delivery = a
  two-layer deliverable (machine-readable + written for people) + writing back the case's E row; an exec writes
  only its own E row and never reads the whole case.
- Watermark — the reading on the line starting `[ctx-kit watermark]`; yellow 400k, red 500k by default, both
  yours to move. An exec session past yellow books the next natural breakpoint to close out and past red is
  reminded this turn; a discussion / lead session is reminded only when it is **both** at a batch boundary
  **and** past yellow, or the moment it is past red. The hook knows nothing about session types — it prints
  whenever the number is past a line, so **the printed line is a reading, not an order**: an exec session
  passes it to the owner that turn, a discussion / lead session only at a batch boundary (yellow) or that same
  turn (red), and otherwise keeps the reading to itself. **Only remind that it is time to close out** — pass
  the reading to the owner in one sentence and suggest closing out; the owner decides, never act unasked
  (ctx-handoff). Say it once per band: before passing a reading on, look back over your own earlier replies in
  this session — if you have already given the owner a reading for this same band, say nothing about it this
  turn; say it again only when the band changes (yellow → red). **A band once reported stays reported for this
  session**: a reading that drops back below the line does not re-arm that band, and climbing back into the
  same band says nothing more. A second reading rides on the same hook and answers to no line: a line starting
  `[ctx-kit update]` says this session opened before the ctx-kit files it is running were last written — pass
  it on once in one sentence and act on nothing, since whatever changed reaches new sessions and not this one.
  **The hook keeps nothing between turns**: it recomputes every turn and re-prints whatever still holds, so
  saying a reading once is the session's own job — and a compact leaves no earlier replies to look back over,
  so after one it gets said again. A successor opens by reading the case file only, and never reads old session
  transcripts (ctx-takeover).
  A discussion / lead session is never compacted; compact is first aid for an exec session nearing the top of the
  window, and nothing else.
- When asked "where do things stand": read the board + the cases and report in plain language, so the owner never
  has to open a file.
- The owner has only three moves: name a job / ask where things stand / decide — plus two housekeeping calls,
  close out and the weekly check. Everything else you do without asking, and report once it is done.
```

## A second rule block: output for the owner

This one is about what the session writes to the owner in the conversation — plain language by default, with five rules always on — and about which files have to come with a version written for a person to read. It is written in Chinese, in the owner's own words: the channel paragraph and the five numbered rules are kept verbatim; the heading's source note, an internal reference, is left out, and the Why paragraph is cut to one sentence. Paste it into `~/.claude/CLAUDE.md` if you want every project to report to you this way; otherwise into the project `CLAUDE.md`.

```markdown
## 给负责人的输出（2026-09-27 第三版，整节替换 09-15 版）

对话里写给负责人的字**默认就是人话**，下面五条常开；文件默认给 agent，有格有框随意，例外只有标明"给人看"的文件。要负责人**亲手执行、批准或审核**的内容（命令、授权范围、改动影响）一律写在人读段，不得只说"贴到哪"；要负责人审的文件必须有"给人看"版，没有就不算交付。对话里混有给 agent 的内容（发车 prompt、任务书、给别案的信、命令串）时**分两段**：先"给你看的"，再"给 agent 的"整块代码块，两段不混写。

1. 首段是判断，先答他问的那一层。
2. 用他的词；编号只进括号或"案里叫"一列；发前遮住编号自读一遍。
3. 关键读数带口径与局限（跟什么比、证什么不证什么）；他只问数就只答数；没有基线写"未测"；估时标"估计"。
4. 状态与结论都标来源：验了什么、谁验、还等谁；实验证实的写读数，负责人拍的写"拍"，不混。
5. 要他做的、要他拍的，每件带为什么、做完能看到什么；讨论先给方向（判定、选项、建议、要拍什么）让他拍，拍了再深挖。

精简删的是重复与套话，不删影响判断的失败、未知与证据边界。"总结一下 / 到哪了"没有触发词，答法与接手复述同一形状：判断 → 到哪 → 下一步 → 要他做什么，十行以内。人话词表在项目 `_ops/人话词表.md`（没有就建，agent 提名、负责人认名）；负责人说过的目标或场景原话逐字记进案，一行，没说过不编。
负责人问"我们讨论过 X 吗 / X 定了什么"：先查 `~/.claude/TOPICS.md`（议题索引），再按它指的路径读；讨论出结论时持笔在该索引追加一行。

**Why**：09-15 版八条外加一个汇报 skill 仍失守，病根是规矩长到只能靠 skill 点名加载、接手模板更具体赢了原则；本版 2026-09-27。
```

In English, for readers who do not read Chinese — **what you paste is the Chinese block above; the English here is only a paraphrase.** What the session writes to the owner in the conversation is plain language by default, with the five rules below always on; files are for agents by default, tables and boxes as you please, the one exception being a file marked for-human (给人看). Anything the owner has to run, approve or review personally (commands, the scope of an authorisation, what a change affects) is written in the part meant for people, never left as a line saying where to paste it; a file the owner is to review must have a for-human version, or it does not count as delivered. Where the conversation carries something for an agent as well (a dispatch prompt, a task brief, a letter to another case, a string of commands), it comes in two parts: first "for you", then "for the agent" as one whole code block, the two never mixed.

1. The first paragraph is the judgement, answering first the layer the owner asked about.
2. Use the owner's words; IDs go only in brackets or in a "called … in the case" column; before sending, cover the IDs and read it through yourself.
3. Key readings carry their basis and their limits (compared with what; what they prove and what they do not); asked only for a number, give only the number; with no baseline, write "not measured"; a time estimate is marked "estimate".
4. Statuses and conclusions both name their source: what was checked, who checked it, who is still awaited; what an experiment confirmed is written as its reading, what the owner decided is written as "decided", and the two are never mixed.
5. Whatever the owner has to do or decide comes with why, and with what they will see once it is done; a discussion first gives the direction (judgement, options, recommendation, what needs deciding) for the owner to decide, and goes deeper only once it is decided.

## Three self-checks after installing

**Run all three in an interactive session you open yourself; a headless `claude -p` reading is not one of these three.** On record: this project ran the three headless on 2026-09-09 and got FAIL on 1 (about 300 lines written without triaging), FAIL on 2 (31,093 characters read without dispatching) and PASS on 3. Nobody has run them interactively, so those readings say what happens headless and nothing about what happens in front of you.

1. In a fresh session, say "I want to do X" and see whether it **triages before acting** (rather than starting work or firing back a string of questions). **Pass** = the first thing back names which of the three routes this is and why — case / one-off / quick fix.
2. Give it a read of more than 30,000 characters (`LC_ALL=en_US.UTF-8 wc -m`, not `wc -c`) and see whether it **dispatches the digest subagent** instead of reading it all itself. **Pass** = a digest subagent call is visible in the session; a reply claiming it summarised the file is not the reading, the call is.
3. Drop **both** `CTXKIT_WATERMARK_YELLOW` and `CTXKIT_WATERMARK_RED` below the current watermark for a moment and take three turns — the first has no reading to go on yet. It should quote its watermark, **offer to close out**, and then **stay quiet inside that band**. **Pass** = the second turn carries the reading and the offer, and the turn after that is quiet; silence on the first turn is correct. Drop both, not just yellow: past yellow alone a discussion / lead session waits for a batch boundary, so its silence is correct and would read as a failure. No reading at all means the hook is not installed; a reading with no offer means the rules were not taken in — check that `CLAUDE.md` is being loaded; an offer repeated every turn means the once-per-band half was not.

## Trimming it per project

- A differently named case directory: add one line of its own to this `CLAUDE.md` — `ctx-kit case library: docs/cases`, the path relative to the project root — which is what all seven skills read; the rules above need no editing.
- No "owner" role (you are working alone): delete the last rule and keep the rest.
- Team settings: add a name convention to the "pen-holder" cell (`name @<first 8 of the session id>`, say — the `sessionId` the session tools hand back, never the name of the transcript file, which is a different id) so two people never take the same case at once.
