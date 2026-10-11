#!/usr/bin/env python3
"""Maintain current personal files and adapted entries; stdlib, preview by default."""
import argparse
from datetime import datetime, timezone
import difflib
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import sys
import tempfile
import uuid

PROFILE = ("CONTEXT.md", "SPEC.md", "TOOLS.md")
FILES = PROFILE + ("TOPICS.md", "global-task/BOARD.md", "config.json")
BEGIN = "<!-- BEGIN CONTEXT-KIT PROFILE"
END = "<!-- END CONTEXT-KIT PROFILE -->"
ACTIVE = {"adapted", "configured_unverified"}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def encode_json(value):
    return (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode()


def safe_path(path):
    path = Path(path).expanduser().absolute()
    for part in (path,) + tuple(path.parents):
        if part.is_symlink():
            # macOS exposes its temporary directories through these system aliases.
            if str(part) in ("/var", "/tmp") and part.resolve() == Path("/private" + str(part)):
                continue
            raise ValueError("symlink needs explicit reconciliation: " + str(part))
    return path


def atomic_write(path, data, mode=0o600):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix="." + path.name + ".", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(tmp, mode)
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


class Plan:
    """Compare-and-swap every input, back up all writes, roll back partial failure."""
    def __init__(self, root):
        self.root = safe_path(root)
        self.before = {}
        self.after = {}

    def read(self, path, required=True):
        path = safe_path(path)
        if path not in self.before:
            if path.exists() and not path.is_file():
                raise ValueError("not a regular file: " + str(path))
            self.before[path] = path.read_bytes() if path.exists() else None
        value = self.before[path]
        if value is None and required:
            raise ValueError("missing file: " + str(path))
        return value

    def put(self, path, data):
        path = safe_path(path)
        before = self.read(path, required=False)
        if before != data:
            self.after[path] = data

    def report(self):
        changes = []
        for path, data in self.after.items():
            before = self.before[path]
            changes.append({"path": str(path), "before_sha256": sha(before) if before is not None else None,
                            "after_sha256": sha(data), "diff": "".join(difflib.unified_diff(
                                (before or b"").decode().splitlines(True), data.decode().splitlines(True),
                                fromfile=str(path), tofile=str(path)))})
        return {"applied": False, "changes": changes}

    def validate(self):
        for path, before in self.before.items():
            safe_path(path)
            current = path.read_bytes() if path.exists() else None
            if before != current:
                raise ValueError("changed after read; re-read and merge: " + str(path))

    def apply(self):
        result = self.report()
        if not self.after:
            return dict(result, applied=True)
        self.root.mkdir(parents=True, exist_ok=True)
        lock = self.root / ".profile.lock"
        safe_path(lock)
        try:
            fd = os.open(lock, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        except FileExistsError:
            raise ValueError("another operation or interrupted write holds " + str(lock))
        os.close(fd)
        done = []
        modes = {}
        try:
            self.validate()
            backup = self.root / "backups" / (datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ-") + uuid.uuid4().hex[:8])
            safe_path(backup).mkdir(parents=True, mode=0o700)
            records = []
            for i, path in enumerate(self.after):
                before = self.before[path]
                modes[path] = stat.S_IMODE(path.stat().st_mode) if before is not None else 0o600
                saved = None
                if before is not None:
                    saved = str(i) + "-" + path.name
                    atomic_write(backup / saved, before)
                records.append({"path": str(path), "backup": saved,
                                "before_sha256": sha(before) if before is not None else None})
            atomic_write(backup / "manifest.json", encode_json({"status": "prepared", "files": records}))
            self.validate()
            try:
                for path, data in self.after.items():
                    atomic_write(path, data, modes[path])
                    done.append(path)
            except BaseException:
                for path in reversed(done):
                    before = self.before[path]
                    if before is None:
                        path.unlink()
                    else:
                        atomic_write(path, before, modes[path])
                atomic_write(backup / "manifest.json", encode_json({"status": "rolled_back", "files": records}))
                raise
            atomic_write(backup / "manifest.json", encode_json({"status": "applied", "files": records}))
            return dict(result, applied=True, backup=str(backup))
        finally:
            lock.unlink()


def read_config(plan):
    config = json.loads(plan.read(plan.root / "config.json"))
    if config.get("schema_version") != 1 or not isinstance(config.get("agents"), dict):
        raise ValueError("unsupported config schema; preserve it and reconcile")
    return config


def absolute_links(text, root):
    def replace(match):
        label, dest = match.groups()
        if re.match(r"[a-zA-Z][a-zA-Z0-9+.-]*:", dest) or dest.startswith(("/", "#")):
            return match.group(0)
        path = str(root / dest)
        return "[" + label + "](" + ("<" + path + ">" if " " in path else path) + ")"
    return re.sub(r"\[([^\]]+)\]\(([^)]+)\)", replace, text)


def generated_block(root, contents):
    sections = ["<!-- source: " + str(root / name) + "; sha256: " + sha(contents[name]) + " -->\n" +
                absolute_links(contents[name].decode(), root).strip() for name in PROFILE]
    return ("<!-- BEGIN CONTEXT-KIT PROFILE v2 -->\n"
            "以下内容由 `" + str(root) + "/` 的个人主档生成；更新主档后需同步此块。\n"
            "历史议题和关键事项按请求读取；进入具体项目后再读取该项目的板、案。\n\n" +
            "\n\n".join(sections) + "\n" + END)


def merge_block(old, block):
    starts = list(re.finditer(r"<!-- BEGIN CONTEXT-KIT PROFILE[^\n]*-->", old))
    if old.count(BEGIN) != len(starts) or len(starts) > 1 or old.count(END) != len(starts):
        raise ValueError("duplicate or malformed generated blocks; reconcile before writing")
    if starts:
        start = starts[0].start()
        end = old.index(END) + len(END)
        if end < starts[0].end():
            raise ValueError("generated block markers out of order")
        return old[:start] + block + old[end:]
    return old + ("\n\n" if old and not old.endswith("\n\n") else "") + "# 用户全局个人上下文\n\n" + block + "\n"


def profile_contents(plan):
    return {name: plan.after.get(plan.root / name, plan.read(plan.root / name)) for name in PROFILE}


def sync_entries(plan, config, agents):
    block = generated_block(plan.root, profile_contents(plan))
    touched = []
    entries = set()
    for name in agents:
        if name not in config["agents"]:
            raise ValueError("agent not registered: " + name)
        adapter = config["agents"][name]
        raw_entry = adapter.get("global_instructions")
        if not raw_entry or not Path(raw_entry).expanduser().is_absolute():
            raise ValueError("absolute global_instructions required: " + name)
        entry = safe_path(raw_entry)
        if entry in entries:
            raise ValueError("two adapters share an entry; reconcile config")
        entries.add(entry)
        # Reading a stale path must not recreate a removed platform installation.
        if not entry.parent.is_dir():
            raise ValueError("platform directory unavailable; no environment rebuild: " + str(entry.parent))
        if name == "codex" and entry.name == "AGENTS.md":
            override = entry.parent / "AGENTS.override.md"
            if plan.read(override, required=False) is not None:
                raise ValueError("AGENTS.override.md takes precedence; reconcile active entry first")
        before = plan.read(entry, required=False)
        after = merge_block((before or b"").decode(), block).encode()
        if name == "codex" and len(after) > 32768:
            raise ValueError("entry exceeds conservative 32 KiB loading budget; reconcile size first")
        plan.put(entry, after)
        if before != after or adapter.get("adaptation_status") not in ACTIVE:
            adapter.update(adaptation_status="configured_unverified", native_load_verified=False,
                           verification_method="pending_native_load")
            adapter.pop("verified_at", None)
        touched.append({"agent": name, "entry": str(entry), "changed": before != after,
                        "native_load_verified": adapter.get("native_load_verified", False)})
    plan.put(plan.root / "config.json", encode_json(config))
    return touched


def candidate(plan, filename, source, expected):
    current = plan.read(plan.root / filename)
    if not expected or sha(current) != expected:
        raise ValueError("expected hash differs; re-read current document and merge")
    proposed = plan.read(source)
    if not proposed.strip():
        raise ValueError("refusing empty personal document")
    proposed.decode("utf-8")
    plan.put(plan.root / filename, proposed)


def run(args):
    plan = Plan(args.root)
    action = args.action or "show"
    if action == "init":
        source = safe_path(args.source)
        for name in FILES[:-1]:
            dest = plan.root / name
            if plan.read(dest, required=False) is None:
                plan.put(dest, plan.read(source / name))
        if plan.read(plan.root / "config.json", required=False) is None:
            # Prior delivery status/paths are snapshots, not runtime facts.
            plan.put(plan.root / "config.json", encode_json({"schema_version": 1, "agents": {}}))
        result = plan.apply() if args.apply else plan.report()
        return dict(result, action=action, retained_existing=True)
    if action == "show":
        config = read_config(plan)
        documents = {name: {"sha256": sha(plan.read(plan.root / name)),
                            "text": plan.read(plan.root / name).decode()} for name in PROFILE}
        return {"root": str(plan.root), "documents": documents, "config": config,
                "note": "configuration status is recorded evidence; show does not verify a native client"}
    if action == "export":
        if args.agent:
            config = read_config(plan)
            if args.agent not in config["agents"]:
                raise ValueError("agent not registered: " + args.agent)
        text = "\n\n".join(absolute_links(plan.read(plan.root / name).decode(), plan.root).strip() for name in PROFILE) + "\n"
        if args.output:
            out = safe_path(args.output)
            out.parent.mkdir(parents=True, exist_ok=True)
            # Exclusive creation: an export never overwrites any existing file.
            with out.open("xb") as handle:
                handle.write(text.encode())
            out.chmod(0o600)
            return {"action": action, "output": str(out), "sha256": sha(text.encode())}
        return {"action": action, "text": text}
    if action in ("topic", "task"):
        filename = "TOPICS.md" if action == "topic" else "global-task/BOARD.md"
        if not args.source_file:
            if args.apply or args.expect_sha:
                raise ValueError("--from is required for a save")
            data = plan.read(plan.root / filename)
            return {"action": action, "sha256": sha(data), "text": data.decode()}
        candidate(plan, filename, args.source_file, args.expect_sha)
        return dict(plan.apply() if args.apply else plan.report(), action=action)
    config = read_config(plan)
    if action == "update":
        candidate(plan, args.file, args.source_file, args.expect_sha)
        agents = [name for name, item in config["agents"].items() if item.get("adaptation_status") in ACTIVE]
    else:
        if args.entry:
            if args.agent == "all":
                raise ValueError("--entry requires one specific agent")
            if not args.entry.expanduser().is_absolute():
                raise ValueError("--entry must be absolute")
            adapter = config["agents"].setdefault(args.agent, {})
            if adapter.get("global_instructions") != str(args.entry.expanduser()):
                adapter.update(global_instructions=str(args.entry.expanduser()),
                               adaptation_status="not_adapted", native_load_verified=False)
        agents = list(config["agents"]) if args.agent == "all" else [args.agent]
        reader = Path(__file__).resolve().with_name("profile_history.py")
        if reader.is_file():
            for name in agents:
                if name in config["agents"]:
                    config["agents"][name].setdefault("history", {})["reader_script"] = str(reader)
    touched = sync_entries(plan, config, agents) if agents else []
    result = plan.apply() if args.apply else plan.report()
    return dict(result, action=action, adapters=touched)


def parser():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--root", type=Path, default=Path.home() / ".context-kit")
    sub = p.add_subparsers(dest="action")
    sub.add_parser("show")
    init = sub.add_parser("init")
    init.add_argument("--source", required=True, type=Path, help="selected current documents, never auto-discovered")
    init.add_argument("--apply", action="store_true")
    update = sub.add_parser("update")
    update.add_argument("--file", required=True, choices=PROFILE)
    update.add_argument("--from", dest="source_file", required=True, type=Path)
    update.add_argument("--expect-sha", required=True)
    update.add_argument("--apply", action="store_true")
    adapt = sub.add_parser("adapt")
    adapt.add_argument("--agent", choices=("codex", "claude_code", "all"), required=True)
    adapt.add_argument("--entry", type=Path, help="explicit active native entry for registering or correcting one adapter")
    adapt.add_argument("--apply", action="store_true")
    export = sub.add_parser("export")
    export.add_argument("--output", type=Path)
    export.add_argument("--agent", choices=("codex", "claude_code"))
    for action in ("topic", "task"):
        x = sub.add_parser(action)
        x.add_argument("--from", dest="source_file", type=Path)
        x.add_argument("--expect-sha")
        x.add_argument("--apply", action="store_true")
    return p


def main():
    p = parser()
    try:
        result = run(p.parse_args())
    except (OSError, ValueError, KeyError, TypeError) as exc:
        p.exit(1, "ERROR: " + str(exc) + "\n")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
