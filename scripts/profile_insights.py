#!/usr/bin/env python3
"""Save selected quotations and personal ideas as knowledge entries; preview by default."""
import argparse
from datetime import date
import json
from pathlib import Path
import re
import sys

from profile_tool import Plan, encode_json, safe_path, sha

TITLE = "核心论断与精彩表达"
TOPIC = Path("knowledge/topics/003-" + TITLE)
MAIN_HEADER = "| 主题 | 一句话摘要 |"
ENTRY_HEADER = "| 日期 | 论断或表达 | 来源 |"
KINDS = {"agent": "agent", "user": "用户", "joint": "共同整理"}
ID_PATTERN = r"[0-9]{8}-[a-z0-9-]{1,48}"


def append_row(text, header, row, target):
    """Append to the selected existing table, preserving all other text."""
    if target in text:
        if text.count(target) != 1 or row not in text.splitlines():
            raise ValueError("existing index entry differs; inspect before changing it")
        return text
    lines = text.splitlines(keepends=True)
    positions = [i for i, line in enumerate(lines) if line.rstrip("\r\n") == header]
    if len(positions) != 1:
        raise ValueError("expected one index table: " + header)
    end = positions[0] + 1
    if end >= len(lines) or not re.fullmatch(r"\|[\s:|\-]+\|\s*", lines[end]):
        raise ValueError("index table separator missing")
    while end < len(lines) and lines[end].startswith("|"):
        end += 1
    if not lines[end - 1].endswith("\n"):
        lines[end - 1] += "\n"
    lines.insert(end, row + "\n")
    return "".join(lines)


def initialize(plan):
    index = plan.root / "knowledge/INDEX.md"
    main = plan.read(index, required=False)
    text = main.decode() if main is not None else "# 个人知识库\n\n" + MAIN_HEADER + "\n|---|---|\n"
    target = "(topics/" + TOPIC.name + "/README.md)"
    if TITLE in text and target not in text:
        raise ValueError("topic name already appears at another location; inspect before creating")
    row = "| [" + TITLE + "]" + target + " | 保存值得留存的判断、结论、精彩表达和个人想法，保留原文、必要背景及出处。 |"
    plan.put(index, append_row(text, MAIN_HEADER, row, target).encode())
    readme = plan.root / TOPIC / "README.md"
    if plan.read(readme, required=False) is None:
        body = ("# " + TITLE + "\n\n"
                "收录用户明确选择的 agent 判断、结论与表达，也收录用户自己的想法。"
                "每条为 entries/ 下的独立短文件，保存核心原文、必要背景、用户补充和出处。\n\n"
                "原文与整理内容分开；来源区分用户、agent 和共同整理。"
                "收录表示值得保留，不表示已验证，也不自动成为全局行为规则。\n\n"
                + ENTRY_HEADER + "\n|---|---|---|\n\n"
                "[返回知识库索引](../../INDEX.md)\n")
        plan.put(readme, body.encode())
    return readme


def normalize(record):
    if not isinstance(record, dict):
        raise ValueError("entry must be a JSON object")
    allowed = {"id", "title", "original", "background", "notes", "source"}
    if set(record) - allowed:
        raise ValueError("unknown entry fields: " + ", ".join(sorted(set(record) - allowed)))
    for key in ("title", "original", "background"):
        if not isinstance(record.get(key), str) or not record[key].strip():
            raise ValueError("nonempty text required: " + key)
    if "\n" in record["title"] or "\r" in record["title"]:
        raise ValueError("title must be one line")
    source = record.get("source")
    if not isinstance(source, dict) or source.get("kind") not in KINDS:
        raise ValueError("source.kind must be agent, user or joint")
    if set(source) - {"kind", "date", "platform", "agent", "session_id", "location"}:
        raise ValueError("unknown source fields")
    if not all(isinstance(value, str) for value in source.values()):
        raise ValueError("source values must be text")
    if not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", source.get("date", "")):
        raise ValueError("source.date must be YYYY-MM-DD")
    date.fromisoformat(source["date"])
    if not isinstance(record.get("notes", ""), str):
        raise ValueError("notes must be text")
    result = {key: record[key] for key in ("title", "original", "background", "source")}
    result["notes"] = record.get("notes", "")
    stable = json.dumps(result, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    entry_id = record.get("id", source["date"].replace("-", "") + "-" + sha(stable)[:12])
    if not isinstance(entry_id, str) or not re.fullmatch(ID_PATTERN, entry_id):
        raise ValueError("invalid entry ID; expected YYYYMMDD-lowercase-suffix")
    result["id"] = entry_id
    return result


def quote(text):
    # Prefix each line only; do not strip whitespace, punctuation or blank lines.
    return "\n".join("> " + line for line in text.split("\n"))


def render(record):
    source = record["source"]
    text = ("# " + record["title"] + "\n\nID：" + record["id"] + "\n\n"
            "## 核心原文\n\n" + quote(record["original"]) + "\n\n"
            "## 必要背景\n\n" + record["background"] + "\n\n"
            "## 我的补充\n\n" + (record["notes"] or "未提供。") + "\n\n"
            "## 出处\n\n- 日期：" + source["date"] + "\n- 来源：" + KINDS[source["kind"]] + "\n")
    for key, label in (("platform", "平台"), ("agent", "Agent"),
                       ("session_id", "会话 ID"), ("location", "原始位置")):
        if source.get(key):
            text += "- " + label + "：" + source[key] + "\n"
    return text.encode()


def table_text(text):
    return (text.replace("\\", "\\\\").replace("|", "\\|")
            .replace("[", "\\[").replace("]", "\\]")
            .replace("<", "&lt;").replace(">", "&gt;"))


def prepare(root, record=None):
    plan = Plan(root)
    readme = initialize(plan)
    entry = None
    if record is not None:
        record = normalize(record)
        entry = plan.root / TOPIC / "entries" / (record["id"] + ".md")
        content = render(record)
        old = plan.read(entry, required=False)
        if old is not None and old != content:
            raise FileExistsError("entry ID already contains different text: " + str(entry))
        plan.put(entry, content)
        target = "(entries/" + entry.name + ")"
        row = ("| " + record["source"]["date"] + " | [" + table_text(record["title"]) + "]" + target
               + " | " + KINDS[record["source"]["kind"]] + " |")
        current = plan.after.get(readme, plan.read(readme, required=False))
        plan.put(readme, append_row(current.decode(), ENTRY_HEADER, row, target).encode())
    return plan, entry


def read_entries(root, query=None):
    root = safe_path(root)
    directory = safe_path(root / TOPIC / "entries")
    entries = []
    for path in sorted(directory.glob("*.md"), reverse=True):
        content = safe_path(path).read_bytes().decode()
        if query and query.casefold() not in content.casefold():
            continue
        entries.append({"id": path.stem, "title": content.split("\n", 1)[0].removeprefix("# "),
                        "path": str(path)})
    return {"topic": str(root / TOPIC / "README.md"),
            "initialized": (root / TOPIC / "README.md").is_file(), "entries": entries}


def parser():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--root", type=Path, default=Path.home() / ".context-kit")
    commands = cli.add_subparsers(dest="action", required=True)
    init = commands.add_parser("init", help="create the empty topic and link it from knowledge/INDEX.md")
    init.add_argument("--apply", action="store_true")
    add = commands.add_parser("add", help="save one explicitly selected quotation or idea")
    add.add_argument("--from", dest="source", type=Path, required=True)
    add.add_argument("--apply", action="store_true")
    listing = commands.add_parser("list", help="read entries, optionally filter by text")
    listing.add_argument("--query")
    show = commands.add_parser("show", help="read one entry")
    show.add_argument("entry_id")
    return cli


def run(args):
    if args.action == "list":
        return read_entries(args.root, args.query)
    if args.action == "show":
        if not re.fullmatch(ID_PATTERN, args.entry_id):
            raise ValueError("invalid entry ID")
        path = safe_path(safe_path(args.root) / TOPIC / "entries" / (args.entry_id + ".md"))
        return {"path": str(path), "text": path.read_bytes().decode()}
    record = json.loads(args.source.read_bytes()) if args.action == "add" else None
    plan, entry = prepare(args.root, record)
    result = plan.apply() if args.apply else plan.report()
    result["topic"] = str(plan.root / TOPIC / "README.md")
    if entry is not None:
        result.update(entry_id=entry.stem, entry_path=str(entry))
    return result


def main():
    try:
        result = run(parser().parse_args())
    except (ValueError, OSError) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    sys.stdout.buffer.write(encode_json(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
