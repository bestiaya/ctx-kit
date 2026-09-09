# A rule block to copy: context and workflow

Paste the whole code block below into your project `CLAUDE.md`, or into the user-level `~/.claude/CLAUDE.md` (put it at user level if you want every project to run under this discipline).

The rules only say *what* to do; *how* lives in the six skills — **a skill's body enters the context only when it is invoked, whereas the rule block is resident**, so the shorter the rules the better. Do not copy skill content into them.

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
  Say in the brief how long the reply may be: **a subagent replies in ≤1,500 characters, in three parts** — one line
  per pre-registered criterion, three key readings, and a pointer to the report. Detail stays in the report file; the
  one limit that matters most ("this reading shows X, not Y") is never the thing cut to save characters.
- Cross-case / cross-session delivery — looking the address up and sending are **one indivisible sequence**:
  (1) any address read earlier is **void**, however few minutes ago, and anything coming in between means you
  look it up again; (2) read the **target case file's** header Pen-holder cell now — the session named in an
  inbox row is the signature, not the address; (3) **immediately before sending**, check that session with
  get_session / list_sessions — and in the same list ask whether the cell is merely out of date: filter to
  titles under this project's working directory matching `^(?:✕\s*)?(\d+)-C0N` (the case number with its
  hyphen out), drop `✕` and archived, and if a **larger** number is live then the cell names an earlier
  stint — send to the largest one and say so in a line. That redirects the address; it is not a fourth
  refusal condition; (4) **refuse to send if any one of these holds**: the title starts with `✕`
  (the retirement mark); `isArchived` is set; or the case header's Pen-holder cell names nobody live (awaiting
  takeover / closing / predecessor retired) — a retired session is not necessarily unreachable, so this check
  has to come before the send; (5) where you refused, **append** a row to the target file's **inbox** (append
  only, never touch the body, so two pens never write over each other) and tell the owner in one line that the
  case has no live pen-holder, asking whether to open a session for it; (6) only once all of it passes, send.
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
  same band says nothing more. A successor opens by reading the case file only, and never reads old session
  transcripts (ctx-takeover).
  A discussion / lead session is never compacted; compact is first aid for an exec session nearing the top of the
  window, and nothing else.
- When asked "where do things stand": read the board + the cases and report in plain language, so the owner never
  has to open a file.
- The owner has only three moves: name a job / ask where things stand / decide — plus two housekeeping calls,
  close out and the weekly check. Everything else you do without asking, and report once it is done.
```

## Three self-checks after installing

**Run all three in an interactive session you open yourself; a headless `claude -p` reading is not one of these three.** On record: this project ran the three headless on 2026-09-09 and got FAIL on 1 (300 lines written without triaging), FAIL on 2 (31,093 characters read without dispatching) and PASS on 3. Nobody has run them interactively, so those readings say what happens headless and nothing about what happens in front of you.

1. In a fresh session, say "I want to do X" and see whether it **triages before acting** (rather than starting work or firing back a string of questions). **Pass** = the first thing back names which of the three routes this is and why — case / one-off / quick fix.
2. Give it a read of more than 30,000 characters (`LC_ALL=en_US.UTF-8 wc -m`, not `wc -c`) and see whether it **dispatches the digest subagent** instead of reading it all itself. **Pass** = a digest subagent call is visible in the session; a reply claiming it summarised the file is not the reading, the call is.
3. Drop **both** `CTXKIT_WATERMARK_YELLOW` and `CTXKIT_WATERMARK_RED` below the current watermark for a moment and take two turns — the first has no reading to go on yet. It should quote its watermark, **offer to close out**, and then **stay quiet inside that band**. **Pass** = the second turn carries the reading and the offer, and the turn after that is quiet. Drop both, not just yellow: past yellow alone a discussion / lead session waits for a batch boundary, so its silence is correct and would read as a failure. No offer at all means the rules were not taken in — check that `CLAUDE.md` is being loaded; an offer repeated every turn means the once-per-band half was not.

## Trimming it per project

- A differently named case directory: add one line of its own to this `CLAUDE.md` — `ctx-kit case library: docs/cases`, the path relative to the project root — which is what all six skills read; the rules above need no editing.
- No "owner" role (you are working alone): delete the last rule and keep the rest.
- Team settings: add a name convention to the "pen-holder" cell (`name @<first 8 of the session id>`, say — the `sessionId` the session tools hand back, never the name of the transcript file, which is a different id) so two people never take the same case at once.
