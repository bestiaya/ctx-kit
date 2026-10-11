# Claude 版

原有 Claude 工具迁至 `setup/`，历史实验保存在 [EVIDENCE](EVIDENCE.md)。协作方法、工作流和模板与 Codex 共用；差异见 [平台规则](setup/PLATFORM.md)。原缓存脚本、digest 和提醒 hook 保留，计价结论未重新验证。

## 安装

在工具包根目录先生成自足包，输出目录须尚不存在：

```bash
python3 scripts/build_package.py --platform claude --output /tmp/context-kit-claude
```

包含八个 `skills/ctx-*`（原五个协作技能、`ctx-profile`、`ctx-review` 与 `ctx-method-doc`）、`agents/digest.md`、`CLAUDE-snippet.md`、`hooks.json`、`INSTALL.md` 和文件哈希清单。每个 skill 带齐依赖，不能只复制源码入口；也可仅复制需要的技能。

在目标项目根目录，先确认没有同名安装（有则备份并明确替换范围），再复制：

```bash
mkdir -p .claude/skills .claude/agents
cp -R /tmp/context-kit-claude/skills/ctx-* .claude/skills/
# digest 为可选，确认没有同名 agent 后复制
cp /tmp/context-kit-claude/agents/digest.md .claude/agents/
```

也可使用 `~/.claude/skills/` 与 `~/.claude/agents/`，避免重复生效。把包内常驻片段合入目标项目的 `CLAUDE.md`；可选 hook 只合并 `hooks` 部分到 `.claude/settings.json`，保留已有配置，不复制 `_note`。安装不会自动完成这些合并。

## 使用与验证

按 [共用手册](../docs/HANDBOOK.md) 使用协作技能。缓存周检仍是 Claude 历史口径；不要用它算 Codex 的费用。

个人上下文只使用 `ctx-profile` 入口，按 [共用流程](../workflows/profile.md) 分发 `init/show/update/adapt/export/topic/task`，无动作默认查看。自然表达“保存当前讨论为话题”“更新话题结论”“记录关键事项”即可，查看和历史查询不自动保存。随技能携带的两个标准库脚本不依赖源码仓库；主档、议题和看板不随包发布。

安装技能不自动 adapt 或恢复已清理的 Claude 环境。使用临时 `--root` 验证只读、预览、幂等和手动保存，正式接入按明确选择处理 `claude_code`，不把文件生成当客户端原生加载验证。

在临时项目走建案、收件、交接、接手，检查案 ID 稳定、缺口与来件未漏、持笔一致。标题工具或其他集成缺失时，确认文件流程仍可继续且 UI 限制有明确报告。

方案送审和回收使用 `/ctx-review` 或自然语言。收到自足请求后直接讨论整体判断、实质异议和推荐方案，不默认逐链接核验；CLI 输出正文由调用方保存，人工审核只写独立回执。版本和运行记录由调用方管理，讨论结果经用户确认后再改文件；见 [共用送审流程](../workflows/review.md)。

方法说明文档写作可使用 `/ctx-method-doc` 或自然语言“使用方法说明文档写作”，按 [共用写作流程](../workflows/method-doc.md) 组织流程指南、判断方法或实践概念说明。普通 README、案卷、短邮件和纯数据报告不自动套用；对文档有异议时先回应，明确同意后再改。

## 升级与卸载

原 `03-setup/` 路径已迁移，更新自行保存的路径；旧安装不会被本次源码变更自动修改。先备份所选同名技能再明确替换，其他技能不动。

卸载仅移除本次安装的技能、自己安装的 digest 和合入的指令/hook 段。个人主档、目标项目的案与交付保留。行为调整见 [迁移说明](../docs/MIGRATION.md)。
