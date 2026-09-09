#!/usr/bin/env python3
"""cache-audit.py — weekly cache checkup for claude CLI sessions (ships with ctx-kit)

Pre-registered criteria (the checkup measure; a fail is reported as a fail):
  - discussion / lead session: rewrite share <10% and p50 watermark <400k
  - exec session: compact count = 0 and peak watermark <500k
  - a row is flagged with a trailing warning sign when it crosses any of those four lines:
    rewrite share >=10%, p50 watermark >=400k, peak watermark >=500k, or compacts >0.
    The script cannot tell a discussion session from an exec one, so the flag is the union of
    both rows of the table — read a flagged row against that session's own type.

Measures:
  - equivalent = input x1 + cache_read x0.1 + cache_write x2 + output x5
    (writes priced at the measured 2x for the 1h bucket)
  - echo = the characters this session's tool results put into a context, its own and its
    subagents' (a subagent's transcript sits in <session id>/subagents/). bash% is the Bash
    share of that. Both are readings and carry no line: no criterion here passes or fails on
    them. The reading they exist for is the count printed under the table -- sessions whose
    echo adds up past 30,000 characters while no single tool result ever reached it, which is
    the read-gate's blind spot, measured at 167 of 217 contexts in this kit's own project on
    2026-09-09, every tool counted, and at 34 of the 106 contexts that carried any Read in a
    second project -- a Read-only count, ignores Bash, not comparable in size with the first.
    30,000 is the existing read-gate number,
    reused here as the boundary of a count; nothing acts on it
  - self = the characters this session wrote into its own tool calls: a Bash command and its
    heredoc, the body of a Write or an Edit, the prompt a dispatched subagent was handed, a
    cross-session message it sent. reports = what came back from elsewhere into this session's
    own thread: a subagent's task-notification, a message from another session. Both are
    readings and carry no line. Unlike echo, both count **this session's own transcript only**
    -- a subagent's own Bash heredoc was written inside the subagent's context and never
    entered this one, so folding it in here would answer a different question from the one
    these two columns are for. The line printed under the table splits those same
    own-transcript characters five ways -- self / echo / reports / replies / other -- so a
    session can see by which route it filled up. The fixed part (the system prompt and the tool
    definitions) is never written into a jsonl and is paid again every turn, so it sits outside
    that split rather than being counted as zero
  - a rewrite event = not the first request, a single cache_write >150k, and the read collapsing
    to under half the existing context (a read still close to the existing context is "a big new
    block entering for the first time", not a cold rewrite of the whole thing, and does not count).
    That 150k is this detector's own threshold, not one of the watermark lines above: the rewrite
    shares this kit publishes were measured with it, so it stays put when those lines move.
  - known blind spot: the compact summary request is not billed into the jsonl, so its cost is
    absent from this table
  - jsonl timestamps are UTC; convert to the local timezone before comparing with a local clock
  - newest first, ordered by the last timestamp inside each log — not by the file's mtime, which
    a copy, a restore or a sync resets on every file at once and then orders the table by an
    accident of the filesystem. mtime is kept only as the fallback for a log whose own
    timestamps will not parse, and the header line says when that happened

Usage:
  python3 cache-audit.py <jsonl path...>            # named sessions
  python3 cache-audit.py --all [min MB]             # sweep the current project (default floor 2MB)
  python3 cache-audit.py --project <dir> --all      # a named project directory
  python3 cache-audit.py --cases <dir> --all        # a named case library (skips the rule below)
  python3 cache-audit.py --out <file> --all         # also write this run's output to a file
  python3 cache-audit.py --help                     # this text
The project directory is derived from cwd by default: ~/.claude/projects/ + cwd with every
non-alphanumeric character replaced by '-'.

The case library is printed under `# case library:` so the checkup sweeps the same directory
this script resolved, and it is resolved by the rule the six ctx-kit skills use, in this
order: the path on the line `ctx-kit case library: <path relative to the project root>` in
the project root's CLAUDE.md if there is one, otherwise an existing _ops/CASES/, otherwise
cases/ (project root = the git root above cwd if there is one, otherwise cwd). Nothing in
the case library is read or written here — the line only says where it is.

The MB floor only hides small logs; it never means there are none. When the floor filters
every log away, the sweep says how many it found and re-runs itself with no floor, so an
empty table is reported as "no sessions found" only when the directory really holds none.

--out writes the same text that goes to the terminal, unchanged, into a file, and is off
unless asked for: the weekly checkup keeps its artifact this way (ctx-checkup section
"The artifact"). A directory in the path that is not there yet is created, so the first
checkup of a project can point --out straight at its CHECKUP/ without making it by hand.
Usage errors go to stderr and are not written to it.

Exit codes:
  0  the audit ran. A zero-row table still exits 0 — read the line printed under the table;
     zero rows is not a pass.
  2  usage error: unknown flag, --project or --cases with no directory, --cases pointing at
     a directory that is not there, a non-numeric MB floor, a jsonl path that is not there,
     --out with no path, or an --out path that cannot be written.
"""
import json, sys, glob, os, re, datetime, statistics

PROJ = (
    os.path.expanduser("~/.claude/projects/")
    + re.sub(r'[^A-Za-z0-9]', '-', os.getcwd())
    + "/"
)

# The one line a project writes in its CLAUDE.md to move its case library, e.g.
#   ctx-kit case library: docs/cases
# Tolerates a leading list marker or backtick and a wrapping pair of backticks.
CASE_LINE = re.compile(r'^[^A-Za-z]*ctx-kit case library:\s*`?\s*([^`\s].*?)\s*`?\s*$')


def project_root(start=None):
    """The git root above `start`, otherwise `start` itself (the skills' definition)."""
    start = os.path.abspath(start or os.getcwd())
    d = start
    while True:
        if os.path.isdir(os.path.join(d, ".git")) or os.path.isfile(os.path.join(d, ".git")):
            return d
        parent = os.path.dirname(d)
        if parent == d:
            return start
        d = parent


def resolve_cases(root=None):
    """The case library, by the same three-step rule the six ctx-kit skills use."""
    root = root or project_root()
    claude_md = os.path.join(root, "CLAUDE.md")
    if os.path.isfile(claude_md):
        try:
            with open(claude_md, encoding="utf-8", errors="replace") as f:
                for line in f:
                    m = CASE_LINE.match(line.rstrip("\n"))
                    if m:
                        return os.path.join(root, os.path.expanduser(m.group(1)))
        except OSError:
            pass
    preferred = os.path.join(root, "_ops", "CASES")
    return preferred if os.path.isdir(preferred) else os.path.join(root, "cases")


def pt(ts):
    return datetime.datetime.fromisoformat(ts.replace("Z", "+00:00"))


# The read gate's own number, reused here as the boundary of a count. It is not a criterion
# line and nothing in this script passes or fails on it: the count under the table is a
# reading, and the checkup reports it without attaching an action.
ECHO_GATE = 30_000


# The five routes characters take into one session's own context, plus one sub-count: how much
# of `self` is prompts written for a subagent, which is the route with an obvious cheaper form
# (write the brief to a file, hand over the path). `dispatch` is a part of `self`, not a sixth
# route, and is not added in anywhere.
MAKEUP = ("self", "echo", "reports", "replies", "other")

# Tool names that hand a job to a subagent. Two spellings because the same call has gone by
# both; a name this does not know still counts into `self`, only not into the sub-count.
DISPATCH = ("Agent", "Task")


def is_report(text):
    """Did this plain-text user record come back from somewhere else, rather than from the owner?

    Two markers, both written by the client at the very start of the message: a subagent that
    finished arrives as `<task-notification>`, and another session's message arrives wrapped in
    `<cross-session-message`. Only the opening of the record is looked at — a message that
    merely quotes one of those words further down is somebody talking about them, not one
    arriving.
    """
    head = text.lstrip()[:400]
    return head.startswith("<task-notification>") or "<cross-session-message" in head


def input_chars(value):
    """How many characters one tool call's input puts into a context.

    The values, not the JSON scaffolding around them: what is being counted is what somebody
    wrote, and `{"command": ...}` is the client's wrapper rather than anybody's writing. A
    number or a boolean counts as what it prints as; None counts zero.
    """
    if isinstance(value, str):
        return len(value)
    if isinstance(value, dict):
        return sum(input_chars(v) for v in value.values())
    if isinstance(value, list):
        return sum(input_chars(v) for v in value)
    if value is None:
        return 0
    return len(str(value))


def echo_chars(block):
    """How many characters one tool_result block puts into the context.

    content given as a string counts whole; content given as a list counts only its text
    parts. An image part or a tool_reference part enters the context as something that is not
    characters, so it counts zero here and the total is an undercount by exactly those parts.
    """
    c = block.get("content")
    if isinstance(c, str):
        return len(c)
    n = 0
    if isinstance(c, list):
        for item in c:
            if isinstance(item, dict) and item.get("type") == "text":
                n += len(item.get("text") or "")
    return n


def echo(fp, per, make=None):
    """Add one transcript's tool echo to `per`, a tool name -> characters counter.

    One pass. Assistant tool_use blocks give id -> tool name; every tool_result block in a
    user message is charged to the name of the id it answers. A result whose id has not been
    seen yet is held back and matched at the end, because a resumed or forked log can write
    the two in the other order. A tool_use_id already counted in this file is not counted
    again — the same result written twice is one arrival in one context. Sidechain records
    are counted: a subagent's echo is echo, and this is what the subagent transcript holds.

    This is the same count that produced the readings quoted at the top of this file, so the
    two can be set side by side rather than argued about.

    Pass a `make` counter and the same pass also splits this file's characters five ways (the
    MAKEUP routes above). It is handed in only for a session's own transcript, never for a
    subagent's, which is what keeps `self` and `reports` answering "what filled this context"
    while `echo` goes on answering "what this whole dispatched job read".
    """
    seen, id2name, pending, biggest = set(), {}, [], 0
    with open(fp, errors="replace") as f:
        for line in f:
            try:
                o = json.loads(line)
            except Exception:
                continue
            m = o.get("message")
            if not isinstance(m, dict):
                continue
            content = m.get("content")
            if make is not None and isinstance(content, str):
                # A user record carrying plain text: either something that arrived from
                # elsewhere, or the owner typing.
                make["reports" if is_report(content) else "other"] += len(content)
            if not isinstance(content, list):
                continue
            if m.get("role") == "assistant":
                for item in content:
                    if not isinstance(item, dict):
                        continue
                    kind = item.get("type")
                    if kind == "tool_use" and item.get("id"):
                        id2name[item["id"]] = item.get("name") or "?"
                    if make is None:
                        continue
                    if kind == "tool_use":
                        n = input_chars(item.get("input"))
                        make["self"] += n
                        if (item.get("name") or "") in DISPATCH:
                            make["dispatch"] += n
                    elif kind == "text":
                        make["replies"] += len(item.get("text") or "")
                    elif kind == "thinking":
                        # Reasoning is neither something read in nor something said to the
                        # owner; it goes to the remainder rather than inflating either.
                        make["other"] += len(item.get("thinking") or "")
            elif m.get("role") == "user":
                for item in content:
                    if not isinstance(item, dict):
                        continue
                    if item.get("type") != "tool_result":
                        if make is not None and item.get("type") == "text":
                            # A skill body, a system reminder, an owner prompt written as a
                            # block: not this session's writing and not a tool result.
                            make["other"] += len(item.get("text") or "")
                        continue
                    tid = item.get("tool_use_id")
                    if tid in seen:
                        continue
                    seen.add(tid)
                    n = echo_chars(item)
                    biggest = max(biggest, n)
                    if make is not None:
                        make["echo"] += n
                    if tid in id2name:
                        per[id2name[tid]] = per.get(id2name[tid], 0) + n
                    else:
                        pending.append((tid, n))
    for tid, n in pending:
        name = id2name.get(tid, "?")
        per[name] = per.get(name, 0) + n
    return biggest


def session_echo(fp):
    """The echo of a session: its own transcript plus every subagent transcript under it, and
    the make-up of the session's own transcript alone.

    A subagent's results are read in that subagent's context, not in its parent's, so this
    is not a bill the parent paid twice — it is what the whole of one dispatched job put in
    front of a model. The subagents of `<id>.jsonl` live in `<id>/subagents/`; a workflow
    journal in there carries no messages and is skipped. The rule is the same inside a
    subagent transcript as in the session's own: a result is charged to the call it answers,
    joined to it by tool_use_id.
    """
    per, biggest = {}, 0
    make = dict.fromkeys(MAKEUP + ("dispatch",), 0)
    biggest = max(biggest, echo(fp, per, make))
    stem = os.path.basename(fp)[: -len(".jsonl")]
    subdir = os.path.join(os.path.dirname(fp), stem, "subagents")
    for here, _dirs, names in os.walk(subdir):
        for name in sorted(names):
            if not name.endswith(".jsonl") or name == "journal.jsonl":
                continue
            try:
                # No `make` here on purpose: a subagent's echo is this session's echo, but a
                # subagent's writing was never in this session's context.
                biggest = max(biggest, echo(os.path.join(here, name), per))
            except OSError:
                continue
    total = sum(per.values())
    return total, per.get("Bash", 0), biggest, make


def make_up(fp):
    """The make-up of one transcript on its own: the five routes, plus the dispatch sub-count.

    Its own function so that the watermark doorbell in this same kit can quote this split
    rather than growing a second one of its own that would drift from this one. `per` is
    thrown away here — the caller wants the make-up, not the per-tool echo.
    """
    make = dict.fromkeys(MAKEUP + ("dispatch",), 0)
    echo(fp, {}, make)
    return make


def audit(fp):
    main, compacts = {}, 0
    with open(fp, errors="replace") as f:
        for line in f:
            try:
                o = json.loads(line)
            except Exception:
                continue
            if o.get("type") == "system" and o.get("subtype") == "compact_boundary":
                compacts += 1
            if o.get("type") != "assistant" or o.get("isSidechain"):
                continue
            m = o.get("message") or {}
            u = m.get("usage") or {}
            mid = m.get("id")
            if not mid or not o.get("timestamp"):
                continue
            rec = dict(
                ts=o["timestamp"],
                it=u.get("input_tokens", 0) or 0,
                cr=u.get("cache_read_input_tokens", 0) or 0,
                cc=u.get("cache_creation_input_tokens", 0) or 0,
                ot=u.get("output_tokens", 0) or 0,
            )
            if mid not in main or rec["ot"] > main[mid]["ot"]:
                main[mid] = rec
    rows = sorted(main.values(), key=lambda r: r["ts"])
    if not rows:
        return None
    try:
        days, last = (pt(rows[-1]["ts"]) - pt(rows[0]["ts"])).days, rows[-1]["ts"]
    except Exception:
        # A timestamp this script cannot read used to end the whole sweep in a traceback, so one
        # malformed line in one log meant no audit at all. Report the session with no dating
        # instead: `last=None` sends the ordering below to the file's mtime and says so.
        days, last = 0, None
    ctx = [r["it"] + r["cr"] + r["cc"] for r in rows]
    # A rewrite = a large write with the read collapsing to under half the existing context
    # (only the shared header is left). A read still close to the existing context is
    # "a big new block entering for the first time" and does not count as a rewrite.
    # The 150k below is this detector's own threshold, not a watermark line, and does not move
    # with them: the published rewrite-share readings were measured against exactly this number.
    rewrites = [
        r
        for i, r in enumerate(rows)
        if i > 0 and r["cc"] > 150_000 and r["cr"] < ctx[i - 1] * 0.5
    ]
    eq = sum(r["it"] + 0.1 * r["cr"] + 2 * r["cc"] + 5 * r["ot"] for r in rows)
    rw = sum(r["cc"] for r in rewrites) * 2
    return dict(
        file=os.path.basename(fp),
        last=last,
        n=len(rows),
        days=days,
        p50=int(statistics.median(ctx)),
        peak=max(ctx),
        eq_m=eq / 1e6,
        rewrites=len(rewrites),
        rw_share=(rw / eq * 100) if eq else 0.0,
        compacts=compacts,
    )


def main():
    args = sys.argv[1:]
    if "-h" in args or "--help" in args:
        print(__doc__.strip())
        return 0
    out_path = None
    if "--out" in args:
        i = args.index("--out")
        if i + 1 >= len(args):
            print("usage error: --out needs a path", file=sys.stderr)
            return 2
        out_path = os.path.expanduser(args[i + 1])
        args = args[:i] + args[i + 2:]
    # Everything the terminal gets is kept, so --out can write the same text unchanged.
    # Usage errors above go to stderr and stay out of the file: an artifact is a record of
    # an audit that ran, and a run that never got past its own flags did not audit anything.
    lines = []

    def emit(text=""):
        lines.append(text)
        print(text)

    proj = PROJ
    if "--project" in args:
        i = args.index("--project")
        if i + 1 >= len(args):
            print("usage error: --project needs a directory", file=sys.stderr)
            return 2
        proj = os.path.expanduser(args[i + 1]).rstrip("/") + "/"
        args = args[:i] + args[i + 2:]
    cases = None
    if "--cases" in args:
        i = args.index("--cases")
        if i + 1 >= len(args):
            print("usage error: --cases needs a directory", file=sys.stderr)
            return 2
        cases = os.path.expanduser(args[i + 1]).rstrip("/")
        if not os.path.isdir(cases):
            print(f"usage error: --cases: no such directory: {cases}", file=sys.stderr)
            return 2
        args = args[:i] + args[i + 2:]
    else:
        cases = resolve_cases()
    allmode = not args or args[0] == "--all"
    found = filtered = 0
    if allmode:
        try:
            minmb = float(args[1]) if len(args) > 1 else 2.0
        except ValueError:
            print(f"usage error: --all takes an MB floor, not {args[1]!r}", file=sys.stderr)
            return 2
        if len(args) > 2:
            print(f"usage error: unexpected argument {args[2]!r}", file=sys.stderr)
            return 2
        found = sorted(glob.glob(proj + "*.jsonl"))
        files = [f for f in found if os.path.getsize(f) > minmb * 1e6]
        filtered = len(found) - len(files)
        emit(f"# project directory: {proj}")
        if found and not files:
            # the floor hid everything: say so and drop it, rather than printing a bare
            # header that reads like "this project has no sessions"
            emit(
                f"# {len(found)} session log(s) here, all of them under the {minmb:g}MB floor"
                " — re-running with no floor (same as --all 0)"
            )
            files, filtered, minmb = found, 0, 0.0
        elif filtered:
            emit(
                f"# {filtered} of {len(found)} session log(s) are under the {minmb:g}MB floor"
                " and are not shown — `--all 0` includes them"
            )
        found = len(found)
    else:
        flags = [a for a in args if a.startswith("-")]
        if flags:
            print(
                f"usage error: unknown flag {flags[0]!r} — see --help", file=sys.stderr
            )
            return 2
        missing = [a for a in args if not os.path.isfile(a)]
        if missing:
            print(f"usage error: no such file: {missing[0]}", file=sys.stderr)
            return 2
        files = args
        found = len(files)
    if os.path.isdir(cases):
        n_md = len(glob.glob(os.path.join(cases, "*.md")))
        emit(f"# case library: {cases} ({n_md} .md file(s), the board and any archives included)")
    else:
        emit(
            f"# case library: {cases} — not there. Looked for a `ctx-kit case library:` line in"
            f" {os.path.join(project_root(), 'CLAUDE.md')}, then _ops/CASES/, then cases/"
        )
    # Audit first, then order by the last timestamp each log carries. Ordering by mtime instead
    # has been measured putting the table in the wrong order: a directory copied or restored
    # gets every mtime rewritten at once, and the newest session then sorts wherever the copy
    # happened to touch it. A log whose own timestamps will not parse falls back to its mtime,
    # and the line under the table header says how many did.
    read, guessed = [], 0
    for fp in files:
        r = audit(fp)
        if not r:
            continue
        r["echo"], r["bash"], r["biggest"], r["make"] = session_echo(fp)
        when = None
        if r["last"]:
            when = pt(r["last"])
            if when.tzinfo is None:
                when = when.replace(tzinfo=datetime.timezone.utc)
        if when is None:
            when = datetime.datetime.fromtimestamp(os.path.getmtime(fp), datetime.timezone.utc)
            guessed += 1
        read.append((when, fp, r))
    read.sort(key=lambda t: t[0], reverse=True)
    emit("# newest first, by the last timestamp inside each log" + (
        f" ({guessed} of {len(read)} by file mtime instead — no timestamp this script could read)"
        if guessed else ""))
    # self and reports sit to the left of echo rather than at the end, so a reader taking the
    # last two columns off a row still gets the same pair as before this was added.
    hdr = (f"{'session':34} {'reqs':>5} {'day':>3} {'p50 ctx':>9} {'peak':>9} {'costM':>7}"
           f" {'rw':>4} {'rw%':>7} {'cmp':>4} {'self':>11} {'reports':>9} {'echo':>12}"
           f" {'bash%':>6}")
    emit(hdr)
    shown = 0
    for _when, fp, r in read:
        shown += 1
        flag = (
            " ⚠️"
            if (
                r["rw_share"] >= 10
                or r["p50"] >= 400_000
                or r["peak"] >= 500_000
                or r["compacts"] > 0
            )
            else ""
        )
        bash_share = (100.0 * r["bash"] / r["echo"]) if r["echo"] else 0.0
        emit(
            f"{r['file'][:34]:34} {r['n']:>5} {r['days']:>3} {r['p50']:>9,} {r['peak']:>9,}"
            f" {r['eq_m']:>7.1f} {r['rewrites']:>4} {r['rw_share']:>6.0f}% {r['compacts']:>4}"
            f" {r['make']['self']:>11,} {r['make']['reports']:>9,} {r['echo']:>12,}"
            f" {bash_share:>5.0f}%{flag}"
        )
    if shown:
        # Two readings, no line: the echo the whole table adds up to, and the count of
        # sessions the per-call read gate cannot see — echo past 30,000 characters with no
        # single tool result ever reaching it. Nothing passes or fails on either number.
        total_echo = sum(r["echo"] for _w, _f, r in read)
        blind = [r for _w, _f, r in read if r["echo"] > ECHO_GATE and r["biggest"] <= ECHO_GATE]
        emit(
            f"# echo across the {shown} session(s) shown: {total_echo:,} characters"
            f" (subagent transcripts included)"
        )
        emit(
            f"# {len(blind)} of {shown} session(s) echo more than {ECHO_GATE:,} characters in total"
            f" while no single tool result ever reaches it — a reading, no line is set on it"
        )
        # A third reading, and the only one that says by which route the characters arrived:
        # the same rows split five ways. Percentages are rounded to whole numbers on their
        # own, so the total is printed beside them and any share can be recomputed from it.
        made = {k: sum(r["make"][k] for _w, _f, r in read) for k in MAKEUP + ("dispatch",)}
        whole = sum(made[k] for k in MAKEUP)
        if whole:
            pct = lambda k: 100.0 * made[k] / whole
            emit(
                f"# make-up of those same logs, each one on its own (subagent transcripts are"
                f" not folded in here, unlike the echo column): self {pct('self'):.0f}%"
                f" — of the whole, {pct('dispatch'):.0f}% is prompts written for a subagent —"
                f" echo {pct('echo'):.0f}%, reports {pct('reports'):.0f}%,"
                f" replies {pct('replies'):.0f}%, other {pct('other'):.0f}%,"
                f" out of {whole:,} characters. The fixed part — system prompt and tool"
                f" definitions — is never written into a jsonl and is paid again every turn,"
                f" so it is outside this split rather than a zero inside it"
            )
    else:
        # zero rows is not a pass: say so plainly, so the checkup cannot read an empty
        # table as a clean bill of health. "No sessions found" is reserved for the case
        # where the directory really is empty — a floor that hid them all is a different
        # sentence, and was read as "this project has none" once already.
        if not allmode:
            emit("(no sessions found in the files given)")
        elif not found:
            emit(f"(no sessions found under {proj})")
        else:
            emit(
                f"({found} session log(s) under {proj} read, none of them holds a billable"
                " request — nothing to judge)"
            )
    if out_path:
        try:
            # The directory first: a project's first checkup points --out at a CHECKUP/ that
            # is not there yet, and failing here threw the whole audit away after printing it.
            os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
            with open(out_path, "w", encoding="utf-8") as fh:
                fh.write("\n".join(lines) + "\n")
        except OSError as e:
            print(f"usage error: --out: cannot write {out_path}: {e}", file=sys.stderr)
            return 2
        print(f"# written to {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
