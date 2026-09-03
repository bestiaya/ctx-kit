#!/usr/bin/env python3
"""cache-audit.py — weekly cache checkup for claude CLI sessions (ships with ctx-kit)

Pre-registered criteria (the checkup measure; a fail is reported as a fail):
  - discussion / lead session: rewrite share <10% and p50 watermark <150k
  - exec session: compact count = 0 and peak watermark <200k
  - any row over the line is flagged with a trailing warning sign

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
  python3 cache-audit.py --all [min MB]             # sweep the current project (default >2MB)
  python3 cache-audit.py --project <dir> --all      # a named project directory
  python3 cache-audit.py -h                         # one-line usage
The project directory is derived from cwd by default: ~/.claude/projects/ + cwd with every
non-alphanumeric character replaced by '-'.
"""
import json, sys, glob, os, re, datetime, statistics

PROJ = (
    os.path.expanduser("~/.claude/projects/")
    + re.sub(r'[^A-Za-z0-9]', '-', os.getcwd())
    + "/"
)


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
        print(
            "usage: cache-audit.py [--project <dir>] [--all [min MB] | <jsonl path...>]"
            "  — weekly cache checkup; --all sweeps the current project (default floor 2MB)"
        )
        return
    proj = PROJ
    if "--project" in args:
        i = args.index("--project")
        proj = os.path.expanduser(args[i + 1]).rstrip("/") + "/"
        args = args[:i] + args[i + 2:]
    allmode = not args or args[0] == "--all"
    if allmode:
        minmb = float(args[1]) if len(args) > 1 else 2.0
        files = [f for f in glob.glob(proj + "*.jsonl") if os.path.getsize(f) > minmb * 1e6]
        print(f"# project directory: {proj}")
    else:
        files = args
    hdr = f"{'session':34} {'reqs':>5} {'day':>3} {'p50 ctx':>9} {'peak':>9} {'costM':>7} {'rw':>4} {'rw%':>7} {'cmp':>4}"
    print(hdr)
    shown = 0
    for fp in sorted(files, key=os.path.getmtime, reverse=True):
        r = audit(fp)
        if not r:
            continue
        shown += 1
        flag = " ⚠️" if (r["rw_share"] >= 10 or r["p50"] >= 150_000 or r["compacts"] > 0) else ""
        print(
            f"{r['file'][:34]:34} {r['n']:>5} {r['days']:>3} {r['p50']:>9,} {r['peak']:>9,}"
            f" {r['eq_m']:>7.1f} {r['rewrites']:>4} {r['rw_share']:>6.0f}% {r['compacts']:>4}{flag}"
        )
    if not shown:
        # zero rows is not a pass: say so plainly, so the checkup cannot read an empty
        # table as a clean bill of health
        print(
            f"(no sessions found under {proj})"
            if allmode
            else "(no sessions found in the files given)"
        )


if __name__ == "__main__":
    main()
