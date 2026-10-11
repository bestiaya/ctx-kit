#!/usr/bin/env python3
"""Check source/package Markdown links and the source skill inventory. Stdlib only."""
import argparse
import re
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS = ("kickoff", "status", "handoff", "takeover", "checkup", "profile", "review", "method-doc")
PLATFORMS = ("claude", "codex")
PROFILE_SCRIPTS = ("profile_tool.py", "profile_history.py", "profile_insights.py")
LINK = re.compile(r"(?<!!)\[[^\]\n]+\]\(([^\s)]+)(?:\s+[^)]*)?\)")


def resources(root):
    """Shared documentation copied into every skill, from one inventory."""
    root = Path(root)
    for directory in ("docs", "workflows", "templates"):
        yield from sorted((root / directory).glob("*.md"))
    for platform in PLATFORMS:
        for filename in ("README.md", "EVIDENCE.md", "setup/PLATFORM.md"):
            yield root / platform / filename


def source_files(root):
    """Publication inputs only; never inspect cases, deliveries or snapshots."""
    root = Path(root)
    yield root / "README.md"
    yield from resources(root)
    for name in PROFILE_SCRIPTS:
        yield root / "scripts" / name
    for platform in PLATFORMS:
        setup = root / platform / "setup"
        snippet = "AGENTS-snippet.md" if platform == "codex" else "CLAUDE-snippet.md"
        yield setup / snippet
        for name in WORKFLOWS:
            skill = setup / "skills" / f"ctx-{name}"
            yield skill / "SKILL.md"
            yield from sorted(p for p in (skill / "agents").rglob("*") if p.is_file())
        if platform == "claude":
            yield setup / "scripts/cache-audit.py"
            yield setup / "hooks.json"
            yield from sorted(p for p in (setup / "agents").rglob("*") if p.is_file())
        if platform == "codex":
            yield setup / "scripts/token-audit.py"


def link_errors(root, paths=None, allowed_targets=None):
    root = Path(root).resolve()
    errors = []
    paths = sorted(root.rglob("*.md")) if paths is None else sorted(paths)
    for path in paths:
        path = Path(path).resolve()
        if not path.is_file():
            errors.append(f"missing source: {path.relative_to(root)}")
            continue
        for match in LINK.finditer(path.read_text(encoding="utf-8")):
            raw = match.group(1).strip("<>")
            url = urlsplit(raw)
            if url.scheme or url.netloc or not url.path:
                continue
            target = (path.parent / unquote(url.path)).resolve()
            if not target.is_relative_to(root):
                errors.append(f"{path.relative_to(root)}: link escapes package: {raw}")
            elif not target.exists():
                errors.append(f"{path.relative_to(root)}: missing link: {raw}")
            elif allowed_targets is not None and target not in allowed_targets:
                errors.append(f"{path.relative_to(root)}: link outside publication source: {raw}")
    return errors


def source_errors(root=ROOT):
    root = Path(root).resolve()
    inputs = set(source_files(root))
    errors = link_errors(root, (p for p in inputs if p.suffix == ".md"),
                         {p.resolve() for p in inputs})
    for path in sorted(inputs):
        if path.suffix != ".md" and not path.is_file():
            errors.append(f"missing source: {path.relative_to(root)}")
    for platform in PLATFORMS:
        for name in WORKFLOWS:
            path = root / platform / "setup/skills" / f"ctx-{name}" / "SKILL.md"
            if not path.is_file():
                errors.append(f"missing skill: {path}")
                continue
            body = path.read_text(encoding="utf-8")
            expected = f"---\nname: ctx-{name}\ndescription: "
            if not body.startswith(expected) or "\n---\n" not in body[len(expected):]:
                errors.append(f"invalid skill frontmatter: {path}")
            if not (root / "workflows" / f"{name}.md").is_file():
                errors.append(f"missing workflow: {name}")
    return errors


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--package", type=Path, help="check a generated package instead of source")
    args = parser.parse_args()
    if args.package is not None and not args.package.is_dir():
        parser.error("package directory does not exist")
    errors = link_errors(args.package) if args.package else source_errors()
    if errors:
        print("\n".join(errors))
        return 1
    print("PASS: Markdown references" + ("" if args.package else f"; {len(PLATFORMS) * len(WORKFLOWS)} skill entrypoints"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
