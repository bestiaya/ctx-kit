#!/usr/bin/env python3
"""Build movable, self-contained skills without modifying any live installation."""
import argparse
import hashlib
import json
import shutil
from pathlib import Path

from check_kit import PLATFORMS, PROFILE_SCRIPTS, ROOT, WORKFLOWS, link_errors, resources, source_errors


def build_package(platform, output, root=ROOT):
    if platform not in PLATFORMS:
        raise ValueError(f"unsupported platform: {platform}")
    root = Path(root).resolve()
    output = Path(output).expanduser().absolute()
    if output.exists() or output.is_symlink():
        raise FileExistsError(f"refusing to overwrite existing output: {output}")
    errors = source_errors(root)
    if errors:
        raise ValueError("source validation failed:\n" + "\n".join(errors))
    shared = list(resources(root))
    for path in shared:
        if not path.is_file():
            raise ValueError(f"missing resource: {path}")

    output.parent.mkdir(parents=True, exist_ok=True)
    output.mkdir()  # Exclusive creation, including concurrent invocations.
    try:
        for name in WORKFLOWS:
            skill = output / "skills" / f"ctx-{name}"
            skill.mkdir(parents=True)
            entry = root / platform / "setup/skills" / f"ctx-{name}" / "SKILL.md"
            text = entry.read_text(encoding="utf-8")
            text = text.replace("../../PLATFORM.md", f"references/context-kit/{platform}/setup/PLATFORM.md")
            text = text.replace("../../../../workflows/", "references/context-kit/workflows/")
            if name == "profile":
                text = text.replace("../../../../scripts/", "scripts/")
            (skill / "SKILL.md").write_text(text, encoding="utf-8")
            if (entry.parent / "agents").is_dir():
                shutil.copytree(entry.parent / "agents", skill / "agents")
            for path in shared:
                dest = skill / "references/context-kit" / path.relative_to(root)
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(path, dest)
            if platform == "claude" and name == "checkup":
                (skill / "scripts").mkdir()
                shutil.copyfile(root / "claude/setup/scripts/cache-audit.py", skill / "scripts/cache-audit.py")
            if platform == "codex" and name == "checkup":
                (skill / "scripts").mkdir()
                shutil.copyfile(root / "codex/setup/scripts/token-audit.py", skill / "scripts/token-audit.py")
            if name == "profile":
                (skill / "scripts").mkdir()
                for script in PROFILE_SCRIPTS:
                    shutil.copyfile(root / "scripts" / script, skill / "scripts" / script)

        snippet = "AGENTS-snippet.md" if platform == "codex" else "CLAUDE-snippet.md"
        shutil.copyfile(root / platform / "setup" / snippet, output / snippet)
        if platform == "claude":
            shutil.copyfile(root / "claude/setup/hooks.json", output / "hooks.json")
        destination = ".agents/skills" if platform == "codex" else ".claude/skills"
        config = "AGENTS.md" if platform == "codex" else "CLAUDE.md"
        (output / "INSTALL.md").write_text(
            f"# context-kit {platform} 安装包\n\n"
            f"将 skills 内 {len(WORKFLOWS)} 个 ctx-* 目录复制到目标项目的 {destination}/；也可仅安装所需技能。\n"
            "复制前检查并备份同名安装，明确替换范围；不要同时安装到多个生效位置。\n"
            f"将 [{snippet}]({snippet}) 的代码块合入既有 {config}，保留原指令。\n\n"
            "每个 skill 内 references 是随包生成的依赖副本，搬移时整个 skill 一起复制。\n"
            "不需要原源码 checkout；源码更新后重新打包，不手工维护生成副本。\n\n"
            "ctx-profile 另带 scripts/ 主档与历史读取工具，个人主档及配置不随包发布。\n"
            "安装技能不会初始化主档或适配客户端；这些动作按用户明确授权分别执行。\n\n"
            + ("hooks.json 是可选项；合并时只取 hooks 字段，不覆盖 settings。\n\n" if platform == "claude" else "")
            + "本包尚未安装。不会修改客户端配置、真实案文件或运行中的会话。\n"
            "卸载仅移除本次安装的技能/可选组件和合入片段，保留项目工作记录。\n",
            encoding="utf-8",
        )
        errors = link_errors(output)
        if errors:
            raise ValueError("package references failed:\n" + "\n".join(errors))
        manifest = {
            "schema_version": 1,
            "platform": platform,
            "skills": [f"ctx-{name}" for name in WORKFLOWS],
            "files": {
                str(path.relative_to(output)): hashlib.sha256(path.read_bytes()).hexdigest()
                for path in sorted(output.rglob("*")) if path.is_file()
            },
        }
        (output / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return manifest
    except BaseException:
        # Only remove the new output directory created by this invocation.
        shutil.rmtree(output)
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--platform", choices=PLATFORMS, required=True)
    parser.add_argument("--output", type=Path, required=True, help="new output directory; never overwritten")
    args = parser.parse_args()
    try:
        manifest = build_package(args.platform, args.output)
    except (OSError, ValueError) as exc:
        parser.exit(1, f"ERROR: {exc}\n")
    print(f"Built {args.platform}: {args.output.resolve()} ({len(manifest['skills'])} skills, {len(manifest['files'])} files)")
    print("Package only; no live installation or configuration changed.")


if __name__ == "__main__":
    main()
