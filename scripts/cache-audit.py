#!/usr/bin/env python3
"""cache-audit.py — weekly cache checkup for claude CLI sessions (ships with ctx-kit)

Pre-registered criteria (the checkup measure; a fail is reported as a fail):
  - discussion / lead session: rewrite share <10% and p50 watermark <150k
  - exec session: compact count = 0 and peak watermark <200k
  - a row is flagged with a trailing warning sign when it crosses any of those four lines:
    rewrite share >=10%, p50 watermark >=150k, peak watermark >=200k, or compacts >0.
    The script cannot tell a discussion session from an exec one, so the flag is the union of
    both rows of the table — read a flagged row against that session's own type.

Measures:
  - equivalent = input x1 + cache_read x0.1 + cache_write x2 + output x5
    (writes priced at the measured 2x for the 1h bucket)
  - a rewrite event = not the first request, a single cache_write >150k, and the read collapsing
    to under half the existing context (a read still close to the existing context is "a big new
    block entering for the first time", not a cold rewrite of the whole thing, and does not count)
  - known blind spot: the compact summary request is not billed into the jsonl, so its cost is
    absent from this table
  - jsonl timestamps are UTC; convert to the local timezone before comparing with a local clock

Usage:
  python3 cache-audit.py <jsonl path...>            # named sessions
  python3 cache-audit.py --all [min MB]             # sweep the current project (default floor 2MB)
  python3 cache-audit.py --project <dir> --all      # a named project directory
  python3 cache-audit.py --cases <dir> --all        # a named case library (skips the rule below)
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

Exit codes:
  0  the audit ran. A zero-row table still exits 0 — read the line printed under the table;
     zero rows is not a pass.
  2  usage error: unknown flag, --project or --cases with no directory, --cases pointing at
     a directory that is not there, a non-numeric MB floor, or a jsonl path that is not there.
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
    ctx = [r["it"] + r["cr"] + r["cc"] for r in rows]
    # A rewrite = a large write with the read collapsing to under half the existing context
    # (only the shared header is left). A read still close to the existing context is
    # "a big new block entering for the first time" and does not count as a rewrite.
    rewrites = [
        r
        for i, r in enumerate(rows)
        if i > 0 and r["cc"] > 150_000 and r["cr"] < ctx[i - 1] * 0.5
    ]
    eq = sum(r["it"] + 0.1 * r["cr"] + 2 * r["cc"] + 5 * r["ot"] for r in rows)
    rw = sum(r["cc"] for r in rewrites) * 2
    return dict(
        file=os.path.basename(fp),
        n=len(rows),
        days=(pt(rows[-1]["ts"]) - pt(rows[0]["ts"])).days,
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
        print(f"# project directory: {proj}")
        if found and not files:
            # the floor hid everything: say so and drop it, rather than printing a bare
            # header that reads like "this project has no sessions"
            print(
                f"# {len(found)} session log(s) here, all of them under the {minmb:g}MB floor"
                " — re-running with no floor (same as --all 0)"
            )
            files, filtered, minmb = found, 0, 0.0
        elif filtered:
            print(
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
        print(f"# case library: {cases} ({n_md} .md file(s), the board and any archives included)")
    else:
        print(
            f"# case library: {cases} — not there. Looked for a `ctx-kit case library:` line in"
            f" {os.path.join(project_root(), 'CLAUDE.md')}, then _ops/CASES/, then cases/"
        )
    hdr = f"{'session':34} {'reqs':>5} {'day':>3} {'p50 ctx':>9} {'peak':>9} {'costM':>7} {'rw':>4} {'rw%':>7} {'cmp':>4}"
    print(hdr)
    shown = 0
    for fp in sorted(files, key=os.path.getmtime, reverse=True):
        r = audit(fp)
        if not r:
            continue
        shown += 1
        flag = (
            " ⚠️"
            if (
                r["rw_share"] >= 10
                or r["p50"] >= 150_000
                or r["peak"] >= 200_000
                or r["compacts"] > 0
            )
            else ""
        )
        print(
            f"{r['file'][:34]:34} {r['n']:>5} {r['days']:>3} {r['p50']:>9,} {r['peak']:>9,}"
            f" {r['eq_m']:>7.1f} {r['rewrites']:>4} {r['rw_share']:>6.0f}% {r['compacts']:>4}{flag}"
        )
    if not shown:
        # zero rows is not a pass: say so plainly, so the checkup cannot read an empty
        # table as a clean bill of health. "No sessions found" is reserved for the case
        # where the directory really is empty — a floor that hid them all is a different
        # sentence, and was read as "this project has none" once already.
        if not allmode:
            print("(no sessions found in the files given)")
        elif not found:
            print(f"(no sessions found under {proj})")
        else:
            print(
                f"({found} session log(s) under {proj} read, none of them holds a billable"
                " request — nothing to judge)"
            )
    return 0


if __name__ == "__main__":
    sys.exit(main())
