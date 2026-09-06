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
- Cross-case / cross-session delivery: check the address before sending — if the target case has
  **no live pen-holder** (awaiting takeover / closing / predecessor retired), **do not send**; append a row to the
  target file's **inbox** instead (append only, never touch the body, so two pens never write over each other),
  and for something urgent tell the owner to open a session. Send directly only when there is a live pen-holder
  that has been active within the hour. To get at what a dead session knows, **read its archive, do not wake it**
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
- Watermark — the reading on the line starting `[ctx-kit watermark]`; yellow 300k, red 400k by default, both
  yours to move. An exec session past yellow books the next natural breakpoint to close out and past red is
  reminded this turn; a discussion / lead session is reminded only when it is **both** at a batch boundary
  **and** past yellow, or the moment it is past red. The hook knows nothing about session types — it prints
  whenever the number is past a line, so **the printed line is a reading, not an order**: an exec session
  passes it to the owner that turn, a discussion / lead session only at a batch boundary (yellow) or that same
  turn (red), and otherwise keeps the reading to itself. **Only remind that it is time to close out** — pass
  the reading to the owner in one sentence and suggest closing out; the owner decides, never act unasked
  (ctx-handoff). Say it once per band: before passing a reading on, look back over your own earlier replies in
  this session — if you have already given the owner a reading for this same band, say nothing about it this
  turn; say it again only when the band changes (yellow → red). A successor opens by reading the case file
  only, and never reads old session transcripts (ctx-takeover).
  A discussion / lead session is never compacted; compact is first aid for an exec session nearing the top of the
  window, and nothing else.
- When asked "where do things stand": read the board + the cases and report in plain language, so the owner never
  has to open a file.
- The owner has only three moves: name a job / ask where things stand / decide — plus two housekeeping calls,
  close out and the weekly check. Everything else you do without asking, and report once it is done.
```

## Three self-checks after installing

1. In a fresh session, say "I want to do X" and see whether it **triages before acting** (rather than starting work or firing back a string of questions).
2. Give it a read of more than 30,000 characters (`LC_ALL=en_US.UTF-8 wc -m`, not `wc -c`) and see whether it **dispatches the digest subagent** instead of reading it all itself.
3. Grow a session past 300k — or drop `CTXKIT_WATERMARK_YELLOW` low for a moment — and see whether it **offers to close out** when it crosses the line, and then **stays quiet inside that band** (no offer at all means the rules were not taken in — check that `CLAUDE.md` is being loaded; an offer repeated every turn means the once-per-band half was not).

## Trimming it per project

- A differently named case directory: add one line of its own to this `CLAUDE.md` — `ctx-kit case library: docs/cases`, the path relative to the project root — which is what all six skills read; the rules above need no editing.
- No "owner" role (you are working alone): delete the last rule and keep the rest.
- Team settings: add a name convention to the "pen-holder" cell (`name @<first 8 of the session id>`, say — the `sessionId` the session tools hand back, never the name of the transcript file, which is a different id) so two people never take the same case at once.
