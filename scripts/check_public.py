#!/usr/bin/env python3
"""Check the Git index for private files and recognizable credential material.

Reads staged/tracked blobs, not ignored working files. Findings never print values.
This is a focused release guard, not a guarantee that every secret can be detected.
"""
import argparse
from pathlib import Path
import re
import subprocess

PRIVATE_ROOTS = {"cases", "_ops", "_internal", ".context-kit", ".context-kit-uat", ".claude", ".codex", ".agents"}
PRIVATE_NAMES = {"AGENTS.md", "CLAUDE.md", "credentials.json", ".credentials.json", "id_rsa", "id_ed25519"}
PATTERNS = {
    "private-key": re.compile(rb"-----BEGIN (?:RSA |EC |DSA |OPENSSH )?PRIVATE KEY-----"),
    "provider-token": re.compile(rb"(?:sk-ant-[A-Za-z0-9_-]{16,}|sk-[A-Za-z0-9_-]{24,}|gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{30,}|AKIA[A-Z0-9]{16})"),
    "personal-home-path": re.compile(rb"/(?:Users|home)/[A-Za-z0-9_.-]+/"),
}

def inspect_entry(name, data):
    path = Path(name)
    findings = []
    if path.parts[0] in PRIVATE_ROOTS or path.name in PRIVATE_NAMES or (path.name.startswith(".env") and path.name != ".env.example") or path.suffix in {".pem", ".key", ".p12", ".jsonl", ".sqlite", ".db"}:
        findings.append((name, 0, "private-file"))
    for number, line in enumerate(data.splitlines(), 1):
        for kind, pattern in PATTERNS.items():
            if pattern.search(line):
                findings.append((name, number, kind))
    return findings

def check(root):
    names = subprocess.check_output(["git", "-C", str(root), "ls-files", "-z"]).split(b"\0")
    findings = []
    count = 0
    for raw in names:
        if not raw:
            continue
        name = raw.decode("utf-8")
        data = subprocess.check_output(["git", "-C", str(root), "show", ":" + name])
        findings.extend(inspect_entry(name, data))
        count += 1
    return count, findings

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    try:
        count, findings = check(args.root)
    except (OSError, subprocess.CalledProcessError, UnicodeError) as exc:
        print("ERROR: cannot inspect the Git index (" + type(exc).__name__ + ")")
        return 2
    for name, line, kind in findings:
        print(f"{name}:{line}: {kind} (value redacted)")
    print(f"Scanned {count} index files; {len(findings)} findings. Ignored local records excluded.")
    return 1 if findings else 0

if __name__ == "__main__":
    raise SystemExit(main())
