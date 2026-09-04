# A rule block to copy: context and workflow

Paste the whole code block below into your project `CLAUDE.md`, or into the user-level `~/.claude/CLAUDE.md` (put it at user level if you want every project to run under this discipline).

The rules only say *what* to do; *how* lives in the six skills — **a skill's body enters the context only when it is invoked, whereas the rule block is resident**, so the shorter the rules the better. Do not copy skill content into them.

```markdown
## Context and workflow
- State lives on disk, sessions are disposable: write a conclusion down as it happens (a decision → the case's
  section C, a change of plan → the case's section B); do not wait for close-out to write it.
- Every job is goal-directed: line the goal chain up first (top-level goal → track / case → this action, read the
  board header), then act; a job that hangs off no milestone is listed separately for review.
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
- Cross-track / cross-session delivery: check the address before sending — if the target track or case has
  **no live pen-holder** (awaiting takeover / closing / predecessor retired), **do not send**; append a row to the
  target file's **inbox** instead (append only, never touch the body, so two pens never write over each other),
  and for something urgent tell the owner to open a session. Send directly only when there is a live pen-holder
  that has been active within the hour. To get at what a dead session knows, **read its archive, do not wake it**
  (reading the archive costs only the reader; waking it costs watermark × 2).
  Do not chase progress after dispatching: subscribe to notify_when_idle on the exec session (a zero-token idle
  bell, CLI ≥2.1.236) and read only the deliverable when the notification arrives; a high-watermark discussion
  session can set crossSessionInbound to hold so an incoming message does not wake it and start billing.
- Read-once material over 30k characters (`LC_ALL=en_US.UTF-8 wc -m`) goes to the digest subagent, and you take back a ≤5k-character
  summary only; the working set (the deliverables this batch chews on repeatedly) is not subject to this.
- An exec session calls set_session_title first thing, naming itself as it appears on the board; delivery = a
  two-layer deliverable (machine-readable + written for people) + writing back the case's E row; an exec writes
  only its own E row and never reads the whole case.
- Past 150-200k, or at a batch boundary: **only remind that it is time to close out** (with the current watermark
  reading), the owner decides whether to do it, never act unasked (ctx-handoff); a successor opens by reading the
  case file only, and never reads old session transcripts (ctx-takeover).
  A discussion / lead session is never compacted; compact is first aid for an exec session nearing the top of the
  window, and nothing else.
- When asked "where do things stand": read the board + the cases and report in plain language, so the owner never
  has to open a file.
- The owner has only three moves: name a job / ask where things stand / decide. Everything else you do without
  asking, and report once it is done.
```

## Three self-checks after installing

1. In a fresh session, say "I want to do X" and see whether it **triages before acting** (rather than starting work or firing back a string of questions).
2. Give it a >30k-character read (`LC_ALL=en_US.UTF-8 wc -m`, not `wc -c`) and see whether it **dispatches the digest subagent** instead of reading it all itself.
3. Grow a session past 150k and see whether it **offers to close out** when it crosses the line (if it does not, the rules were not taken in — check that `CLAUDE.md` is being loaded).

## Trimming it per project

- A differently named case directory: add one line of its own to this `CLAUDE.md` — `ctx-kit case library: docs/cases`, the path relative to the project root — which is what all six skills read; the rules above need no editing.
- No "owner" role (you are working alone): delete the last rule and keep the rest.
- Team settings: add a name convention to the "pen-holder" cell (`name @first-8-of-UUID`, say) so two people never take the same case at once.
