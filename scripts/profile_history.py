#!/usr/bin/env python3
"""Read native history without modifying logs, metadata, or a shared index.

CLI writes one JSON object. Matches are in path/line order, limited to 20 by
default; coverage counts refer to all candidate files examined. Date-only bounds
are inclusive UTC days. Codex event_msg is deliberately excluded because it is
an overlapping event stream, not a second copy of the conversation.
"""
import argparse
from datetime import datetime, time, timezone
import json
import os
from pathlib import Path
import sqlite3
import sys


class ConfigurationError(ValueError):
    pass


def _path(value, base):
    if not isinstance(value, str) or not value.strip():
        raise ConfigurationError("历史路径必须是非空字符串")
    path = Path(value).expanduser()
    return (base / path if not path.is_absolute() else path).absolute()


def _date(value, end=False):
    if value is None:
        return None
    if len(value) == 10:
        day = datetime.strptime(value, "%Y-%m-%d").date()
        return datetime.combine(day, time.max if end else time.min, timezone.utc)
    result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return result.replace(tzinfo=timezone.utc) if result.tzinfo is None else result


def _project(value):
    return os.path.normpath(os.path.abspath(os.path.expanduser(value)))


def _text(value):
    """Extract text blocks only; never stringify hidden reasoning blocks."""
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        return "\n".join(filter(None, (_text(item) for item in value)))
    if isinstance(value, dict) and value.get("type") in (
            "text", "input_text", "output_text"):
        return value.get("text", "") if isinstance(value.get("text"), str) else ""
    return ""


def _json_text(value):
    return value if isinstance(value, str) else json.dumps(value, ensure_ascii=False)


def _codex_parts(payload):
    kind = payload.get("type")
    if payload.get("channel") in ("analysis", "reasoning") or kind == "reasoning":
        return []
    if kind == "message" and payload.get("role") in ("user", "assistant"):
        body = _text(payload.get("content"))
        return [("discussion", payload["role"], body, None, None)] if body else []
    if kind in ("function_call", "custom_tool_call"):
        return [("tool_call", "assistant", _json_text(payload.get(
            "arguments", payload.get("input", ""))), payload.get("call_id"), payload.get("name"))]
    if kind in ("function_call_output", "custom_tool_call_output"):
        output = payload.get("output", "")
        body = _text(output) if isinstance(output, list) else _json_text(output)
        return [("tool_result", "tool", body, payload.get("call_id"), None)]
    return []


def _claude_parts(record):
    message = record.get("message")
    if not isinstance(message, dict) or record.get("type") not in ("user", "assistant"):
        return []
    if message.get("channel") in ("analysis", "reasoning"):
        return []
    content = message.get("content", [])
    if isinstance(content, str):
        return [("discussion", record["type"], content, None, None)]
    parts = []
    for block in content if isinstance(content, list) else []:
        if not isinstance(block, dict):
            continue
        if block.get("type") == "text":
            parts.append(("discussion", record["type"], _text(block), None, None))
        elif block.get("type") == "tool_use":
            parts.append(("tool_call", "assistant", _json_text(block.get("input", {})),
                          block.get("id"), block.get("name")))
        elif block.get("type") == "tool_result":
            parts.append(("tool_result", "tool", _text(block.get("content", "")),
                          block.get("tool_use_id"), None))
    return parts


def read_history(config_file, agent, session=None, project=None, query=None,
                 limit=20, date_from=None, date_to=None, kind=None):
    """Return matches plus explicit coverage. Raises only for invalid input/config."""
    if agent not in ("codex", "claude_code"):
        raise ConfigurationError("agent 必须为 codex 或 claude_code")
    if limit < 1:
        raise ConfigurationError("limit 必须大于零")
    if kind not in (None, "discussion", "tool_call", "tool_result"):
        raise ConfigurationError("kind 必须为 discussion、tool_call 或 tool_result")
    try:
        start, end = _date(date_from), _date(date_to, end=True)
    except (TypeError, ValueError) as exc:
        raise ConfigurationError("日期应为 YYYY-MM-DD 或 ISO 8601") from exc
    if start and end and start > end:
        raise ConfigurationError("date-from 不得晚于 date-to")
    config_path = Path(config_file).expanduser().absolute()
    try:
        config = json.loads(config_path.read_text(encoding="utf-8"))
        history = config["agents"][agent]["history"]
    except (OSError, UnicodeError, ValueError, KeyError, TypeError) as exc:
        raise ConfigurationError("无法读取配置或缺少 agents.%s.history: %s" % (agent, exc)) from exc
    if not isinstance(history, dict) or not isinstance(history.get("roots"), list):
        raise ConfigurationError("history.roots 必须为路径数组")
    roots = [_path(root, config_path.parent) for root in history["roots"]]
    db = _path(history["metadata_db"], config_path.parent) if history.get("metadata_db") else None
    wanted_project = _project(project) if project else None
    coverage = dict(roots=[str(p) for p in roots], metadata_db=str(db) if db else None,
                    candidate_selection="session 文件名线索 + Codex 精确 ID 元数据" if session else "登记 roots 内主日志 .jsonl",
                    metadata_lookup=False, candidate_files=0, scanned_files=0,
                    verified_files=0, lines_read=0, malformed_lines=0,
                    truncated_lines=0, skipped_event_messages=0, skipped_subagents=0,
                    filtered_files=0, filtered_records=0, undated_records=0,
                    matched_records=0, limit=limit, truncated=False)
    warnings = []
    matches = []
    candidates = set()

    def warning(code, path, detail, line=None):
        item = dict(code=code, path=str(path), detail=str(detail))
        if line is not None:
            item["line"] = line
        warnings.append(item)

    for root in roots:
        if not root.is_dir():
            warning("missing_root", root, "日志目录不存在或不是目录")
            continue
        def walk_error(exc):
            warning("unreadable_directory", exc.filename or root, exc)
        for directory, dirs, files in os.walk(root, onerror=walk_error, followlinks=False):
            if agent == "claude_code" and "subagents" in dirs:
                dirs.remove("subagents")
                coverage["skipped_subagents"] += 1
            dirs.sort()
            for filename in sorted(files):
                if filename.endswith(".jsonl") and (not session or session in filename):
                    candidates.add((Path(directory) / filename).resolve())

    # Existing metadata is only consulted for an exact requested Codex ID.
    if agent == "codex" and session and db:
        coverage["metadata_lookup"] = True
        connection = None
        try:
            connection = sqlite3.connect(db.as_uri() + "?mode=ro", uri=True)
            connection.execute("PRAGMA query_only = ON")
            columns = {row[1] for row in connection.execute("PRAGMA table_info(threads)")}
            if not {"id", "rollout_path"}.issubset(columns):
                warning("unsupported_metadata", db, "threads 表缺少 id/rollout_path")
            else:
                row = connection.execute("SELECT rollout_path FROM threads WHERE id = ?", (session,)).fetchone()
                if row and row[0]:
                    candidates.add(_path(row[0], db.parent).resolve())
                elif not candidates:
                    warning("metadata_id_missing", db, "现有 threads 表未找到该 ID")
        except (sqlite3.Error, ConfigurationError) as exc:
            warning("unreadable_metadata", db, exc)
        finally:
            if connection:
                connection.close()
    if not roots and not (agent == "codex" and session and db):
        warning("unconfigured_history", config_path, "未登记可读日志目录")
    coverage["candidate_files"] = len(candidates)
    seen_claude = set()
    for path in sorted(candidates):
        try:
            stream = path.open("r", encoding="utf-8")
        except OSError as exc:
            warning("unreadable_file", path, exc)
            continue
        coverage["scanned_files"] += 1
        current_session = None
        current_project = None
        verified = False
        rejected = False
        with stream:
            try:
                for line_number, raw in enumerate(stream, 1):
                    coverage["lines_read"] += 1
                    try:
                        record = json.loads(raw)
                        if not isinstance(record, dict):
                            raise ValueError("JSONL 记录不是对象")
                    except ValueError as exc:
                        key = "malformed_lines" if raw.endswith("\n") else "truncated_lines"
                        coverage[key] += 1
                        warning(key, path, exc, line_number)
                        continue
                    if agent == "codex":
                        payload = record.get("payload")
                        if not isinstance(payload, dict):
                            continue
                        if record.get("type") == "session_meta":
                            sid, cwd = payload.get("id"), payload.get("cwd")
                            if not isinstance(sid, str) or not sid or not isinstance(cwd, str) or not cwd:
                                warning("missing_identity", path, "session_meta 缺少 id/cwd", line_number)
                                rejected = True
                            elif current_session and (sid != current_session or _project(cwd) != current_project):
                                warning("conflicting_identity", path, "session_meta 身份发生变化", line_number)
                                rejected = True
                            else:
                                current_session, current_project = sid, _project(cwd)
                                if (session and sid != session) or (wanted_project and current_project != wanted_project):
                                    coverage["filtered_files"] += 1
                                    rejected = True
                                else:
                                    verified = True
                            if rejected:
                                break
                            continue
                        if record.get("type") == "event_msg":
                            coverage["skipped_event_messages"] += 1
                            continue
                        if not verified or record.get("type") != "response_item":
                            continue
                        parts = _codex_parts(payload)
                    else:
                        if record.get("isSidechain"):
                            coverage["skipped_subagents"] += 1
                            continue
                        sid, cwd = record.get("sessionId"), record.get("cwd")
                        if isinstance(sid, str) and sid:
                            current_session = sid
                        if isinstance(cwd, str) and cwd:
                            current_project = _project(cwd)
                        parts = _claude_parts(record)
                        if not parts:
                            continue
                        if not current_session or not current_project:
                            warning("missing_identity", path, "正文缺少可核验的 sessionId/cwd", line_number)
                            continue
                        if (session and current_session != session) or (wanted_project and current_project != wanted_project):
                            coverage["filtered_records"] += 1
                            continue
                        verified = True
                    if not parts:
                        continue
                    timestamp = record.get("timestamp")
                    if start or end:
                        try:
                            instant = _date(timestamp) if isinstance(timestamp, str) else None
                        except ValueError:
                            instant = None
                        if instant is None:
                            coverage["undated_records"] += 1
                            warning("undated_record", path, "日期筛选无法判断，跳过该记录", line_number)
                            continue
                        if (start and instant < start) or (end and instant > end):
                            continue
                    for part_number, (part_kind, role, body, call_id, name) in enumerate(parts):
                        if (kind and kind != part_kind) or not body or (query is not None and query.casefold() not in body.casefold()):
                            continue
                        uuid = record.get("uuid")
                        if agent == "claude_code" and isinstance(uuid, str) and uuid:
                            key = (current_session, uuid, part_number)
                            if key in seen_claude:
                                continue
                            seen_claude.add(key)
                        coverage["matched_records"] += 1
                        if len(matches) < limit:
                            matches.append(dict(agent=agent, kind=part_kind, role=role, text=body,
                                                timestamp=timestamp, session=current_session,
                                                project=current_project, path=str(path), line=line_number,
                                                part=part_number, call_id=call_id, tool_name=name))
            except (OSError, UnicodeError) as exc:
                warning("unreadable_file", path, exc)
        if verified:
            coverage["verified_files"] += 1
        elif not rejected and agent == "codex":
            warning("missing_identity", path, "未读到可核验的 session_meta.id/cwd")
    coverage["truncated"] = coverage["matched_records"] > len(matches)
    return dict(status="partial" if warnings else "ok", matches=matches, coverage=coverage,
                warnings=warnings, filters=dict(agent=agent, session=session, project=project,
                                              query=query, date_from=date_from, date_to=date_to, kind=kind),
                note="未命中仅表示本次已登记且可读取的范围内未找到，不能推断从未发生。工具返回不自动证明业务成功。")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True)
    parser.add_argument("--agent", required=True, choices=("codex", "claude_code"))
    parser.add_argument("--session")
    parser.add_argument("--project")
    parser.add_argument("--query")
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument("--date-from")
    parser.add_argument("--date-to")
    parser.add_argument("--kind", choices=("discussion", "tool_call", "tool_result"))
    args = parser.parse_args(argv)
    try:
        result = read_history(args.config, args.agent, args.session, args.project,
                              args.query, args.limit, args.date_from, args.date_to, args.kind)
    except ConfigurationError as exc:
        print(json.dumps(dict(status="error", error=str(exc)), ensure_ascii=False))
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
