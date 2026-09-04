#!/usr/bin/env python3
"""release-check.py — pre-release consistency check for the ctx-kit repository.

What it checks (every finding prints as `file:line`):
  1. manifest    `.claude-plugin/plugin.json` parses and carries a semver `version`
  2. inventory   every `skills/ctx-*/` holds a SKILL.md whose front-matter `name:`
                 equals the directory name; the hook, the audit script and the
                 digest subagent named in the manifest description all exist
  3. counts      every "<number> skills" / "<数>个 skill" written in the READMEs,
                 CLAUDE-snippet, the manifest description and docs 01-06 equals the
                 real number of skills on disk
  4. names       every skill name appears in both READMEs and in the manifest
                 description, and no README names a `ctx-*` skill that does not exist
  5. version     every ctx-kit version written in the docs equals the manifest version;
                 the manifest version is never behind the newest released git tag

Frozen Chinese copies (`skills/*/SKILL.zh-CN.md`) are excluded on purpose: they are
frozen references and are not kept in step with the English originals.

Usage:
  release-check.py [--root <repo dir>] [-v]
  release-check.py --help

Exit codes:
  0  no drift
  1  drift found (each one printed as `file:line  message`)
  2  the check itself could not run (root not found, manifest unreadable)
"""
import json
import os
import re
import subprocess
import sys

COUNT_FILES = [
    "README.md",
    "README.zh-CN.md",
    "CLAUDE-snippet.md",
    ".claude-plugin/plugin.json",
    "01-BACKGROUND.md",
    "02-METHOD.md",
    "03-PLAYBOOK.md",
    "04-HANDBOOK.md",
    "05-FAQ.md",
    "06-RECIPES.md",
]
READMES = ["README.md", "README.zh-CN.md"]

WORDS = {
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
    "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
    "一": 1, "两": 2, "二": 2, "三": 3, "四": 4, "五": 5,
    "六": 6, "七": 7, "八": 8, "九": 9, "十": 10,
}
NUM_EN = "|".join(k for k in WORDS if k.isascii())
NUM_ZH = "".join(k for k in WORDS if not k.isascii())
COUNT_PATTERNS = [
    re.compile(r"(?<![\w-])(\d+|" + NUM_EN + r")[ \-]+skills?\b", re.I),
    re.compile(r"([" + NUM_ZH + r"]|\d+)\s*(?:个|条)\s*(?:skill|技能)"),
]
VERSION_PATTERNS = [
    re.compile(r"ctx-kit[@ v]+(\d+\.\d+\.\d+)"),
    re.compile(r"(?:version|版本)\s*[:：=]?\s*v?(\d+\.\d+\.\d+)", re.I),
]
SEMVER = re.compile(r"^(\d+)\.(\d+)\.(\d+)(?:[-+].*)?$")


def as_num(tok):
    return int(tok) if tok.isdigit() else WORDS[tok.lower()]


def semver_key(s):
    m = SEMVER.match(s)
    return tuple(int(x) for x in m.groups()) if m else None


def read_lines(path):
    with open(path, encoding="utf-8", errors="replace") as f:
        return f.read().split("\n")


class Report:
    def __init__(self):
        self.drift = []
        self.notes = []

    def bad(self, where, msg):
        self.drift.append(f"{where}  {msg}")

    def note(self, msg):
        self.notes.append(f"note: {msg}")


def check(root, verbose=False):
    r = Report()
    manifest_rel = ".claude-plugin/plugin.json"
    manifest_path = os.path.join(root, manifest_rel)
    if not os.path.isfile(manifest_path):
        print(f"cannot run: no {manifest_rel} under {root}", file=sys.stderr)
        return None
    try:
        manifest = json.loads(open(manifest_path, encoding="utf-8").read())
    except Exception as e:
        print(f"cannot run: {manifest_rel} does not parse ({e})", file=sys.stderr)
        return None

    # 1. manifest version
    version = str(manifest.get("version", ""))
    vline = next(
        (i + 1 for i, l in enumerate(read_lines(manifest_path)) if '"version"' in l), 1
    )
    if not version:
        r.bad(f"{manifest_rel}:{vline}", "no version in the plugin manifest")
    elif not SEMVER.match(version):
        r.bad(
            f"{manifest_rel}:{vline}",
            f'version "{version}" is not semver (major.minor.patch)',
        )

    # 2. inventory
    skills_dir = os.path.join(root, "skills")
    names = sorted(
        d
        for d in os.listdir(skills_dir)
        if d.startswith("ctx-") and os.path.isfile(os.path.join(skills_dir, d, "SKILL.md"))
    ) if os.path.isdir(skills_dir) else []
    if not names:
        r.bad("skills/", "no skills/ctx-*/SKILL.md found — is --root the repository?")
    n = len(names)
    for d in names:
        rel = f"skills/{d}/SKILL.md"
        lines = read_lines(os.path.join(root, rel))
        fm = next(
            ((i + 1, l.split(":", 1)[1].strip()) for i, l in enumerate(lines[:15])
             if l.startswith("name:")),
            None,
        )
        if not fm:
            r.bad(f"{rel}:1", "no `name:` in the front matter")
        elif fm[1] != d:
            r.bad(f"{rel}:{fm[0]}", f'front-matter name "{fm[1]}" != directory "{d}"')
    for rel in ("hooks/hooks.json", "scripts/cache-audit.py", "agents/digest.md"):
        if not os.path.isfile(os.path.join(root, rel)):
            r.bad(rel, "named in the manifest description but missing from the repository")
    hooks_rel = "hooks/hooks.json"
    if os.path.isfile(os.path.join(root, hooks_rel)):
        try:
            json.loads(open(os.path.join(root, hooks_rel), encoding="utf-8").read())
        except Exception as e:
            r.bad(f"{hooks_rel}:1", f"does not parse as JSON ({e})")

    # 3. counts written in prose
    seen_counts = 0
    for rel in COUNT_FILES:
        p = os.path.join(root, rel)
        if not os.path.isfile(p):
            r.bad(rel, "listed as a count-bearing file but missing from the repository")
            continue
        for i, line in enumerate(read_lines(p), 1):
            for pat in COUNT_PATTERNS:
                for m in pat.finditer(line):
                    seen_counts += 1
                    got = as_num(m.group(1))
                    if got != n:
                        r.bad(
                            f"{rel}:{i}",
                            f'says "{m.group(0).strip()}" but {n} skills are on disk',
                        )
                    elif verbose:
                        r.note(f'{rel}:{i} "{m.group(0).strip()}" ok')
    if not seen_counts:
        r.note("no skill count is written anywhere — the count check had nothing to compare")

    # 4. skill names in the READMEs and the manifest description
    desc = str(manifest.get("description", ""))
    for d in names:
        if d not in desc:
            r.bad(f"{manifest_rel}:{vline}", f"manifest description does not name {d}")
    for rel in READMES:
        p = os.path.join(root, rel)
        if not os.path.isfile(p):
            r.bad(rel, "missing from the repository")
            continue
        body = open(p, encoding="utf-8", errors="replace").read()
        for d in names:
            if d not in body:
                r.bad(rel, f"does not name the skill {d}")
        for i, line in enumerate(body.split("\n"), 1):
            for tok in set(re.findall(r"ctx-[a-z][a-z0-9-]*", line)):
                # `ctx-kit` is the product, and names derived from it (the backup
                # directory `ctx-kit-backup-<timestamp>`, say) are not skill names
                if tok != "ctx-kit" and not tok.startswith("ctx-kit-") and tok not in names:
                    r.bad(rel + f":{i}", f"names {tok}, which is not a skill on disk")

    # 5. version written in the docs, and the newest released tag
    declared = 0
    for rel in COUNT_FILES:
        p = os.path.join(root, rel)
        if not os.path.isfile(p) or rel == manifest_rel:
            continue
        for i, line in enumerate(read_lines(p), 1):
            for pat in VERSION_PATTERNS:
                for m in pat.finditer(line):
                    declared += 1
                    if m.group(1) != version:
                        r.bad(
                            f"{rel}:{i}",
                            f'says version {m.group(1)}, manifest says {version}',
                        )
                    elif verbose:
                        r.note(f"{rel}:{i} version {m.group(1)} ok")
    if not declared:
        r.note(
            "no ctx-kit version is written in the READMEs or docs — only the manifest "
            "and the git tag carry it, so nothing pins the docs to a version"
        )

    tags = []
    try:
        out = subprocess.run(
            ["git", "-C", root, "tag", "-l", "v*"],
            capture_output=True, text=True, timeout=20,
        )
        tags = [t.strip() for t in out.stdout.split("\n") if t.strip()]
    except Exception as e:
        r.note(f"git tags unreadable ({e}) — the tag comparison was skipped")
    keyed = [(semver_key(t[1:]), t) for t in tags if semver_key(t[1:])]
    if not keyed:
        r.note("no vX.Y.Z git tag — the tag comparison had nothing to compare")
    elif semver_key(version):
        latest = max(keyed)
        if semver_key(version) < latest[0]:
            r.bad(
                f"{manifest_rel}:{vline}",
                f"version {version} is behind the released tag {latest[1]}",
            )
        elif semver_key(version) > latest[0]:
            r.note(
                f"version {version} is ahead of the newest tag {latest[1]} "
                "(expected while a release is being prepared)"
            )
        else:
            r.note(f"version {version} matches the newest tag {latest[1]}")
    return r, n, names


def main():
    args = sys.argv[1:]
    if "-h" in args or "--help" in args:
        print(__doc__.strip())
        return 0
    verbose = False
    if "-v" in args:
        verbose = True
        args.remove("-v")
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if "--root" in args:
        i = args.index("--root")
        if i + 1 >= len(args):
            print("usage: release-check.py [--root <repo dir>] [-v]", file=sys.stderr)
            return 2
        root = os.path.abspath(os.path.expanduser(args[i + 1]))
        args = args[:i] + args[i + 2:]
    if args:
        print(f"unknown argument: {args[0]}\nusage: release-check.py [--root <repo dir>] [-v]",
              file=sys.stderr)
        return 2
    if not os.path.isdir(root):
        print(f"cannot run: {root} is not a directory", file=sys.stderr)
        return 2

    got = check(root, verbose)
    if got is None:
        return 2
    r, n, names = got
    print(f"# release-check: {root}")
    print(f"# {n} skills on disk: {', '.join(names)}")
    for line in r.notes:
        print(line)
    for line in r.drift:
        print(line)
    if r.drift:
        print(f"--- {len(r.drift)} drift(s) — fix these before releasing ---")
        return 1
    print("--- no drift ---")
    return 0


if __name__ == "__main__":
    sys.exit(main())
