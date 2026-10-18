# ctx-kit · 换个聊天，接着做

**把决策和进展留在项目里，让后续会话知道从哪里继续。**

[English](README.md) · [动手试一次](docs/TRY-IT.md) · [Claude 安装](claude/README.md) · [Codex 安装](codex/README.md)

任务做了两天，聊天却要换了：已经决定什么、哪些尝试失败了、还有什么没做，往往又得解释一次。

ctx-kit 是面向 **Claude Code 和 Codex** 的文件协作工作流。它让 agent 在项目中维护普通 Markdown 记录，保存目标、当前决策、未完成事项和下一步，供后续会话接手。

## 先试一次交接

1. **开始工作**：用 `ctx-kickoff` 建立或找到任务记录。
2. **暂时停下**：用 `ctx-handoff` 保存当前状态、未完成事项和下一步。
3. **换个聊天继续**：用 `ctx-takeover` 读取该案文件，核对它的理解后继续工作。

需要查看多个任务时，用 `ctx-status`。第一次使用先走通这一条链，不必先学完所有概念。

**[打开最小可复现示例 →](docs/TRY-IT.md)**

示例使用虚构数据，有明确验收步骤；它是操作演示，不是效果基准。也可以选你自己的一个真实任务试用。

## 安装

**直接下载技能包：**[Codex ZIP](https://github.com/bestiaya/ctx-kit/releases/download/v0.15.0/ctx-kit-codex-v0.15.0.zip) · [Claude ZIP](https://github.com/bestiaya/ctx-kit/releases/download/v0.15.0/ctx-kit-claude-v0.15.0.zip) · [SHA256SUMS](https://github.com/bestiaya/ctx-kit/releases/download/v0.15.0/SHA256SUMS)。解压后按包内 `INSTALL.md` 安装到目标项目，无需自己打包。试用示例仍从源码仓库取得。

当前源码版本：**v0.15.0**。打包需要 Python 3.9+，仅使用标准库。

在 macOS / Linux shell 中执行：

```bash
git clone https://github.com/bestiaya/ctx-kit.git
cd ctx-kit
python3 scripts/build_package.py --platform codex --output /tmp/ctx-kit-codex
```

Claude 使用 `--platform claude --output /tmp/ctx-kit-claude`。输出目录必须尚不存在。

然后按 [Codex](codex/README.md) 或 [Claude](claude/README.md) 的说明，把生成的技能安装到**一个目标项目**，合入提供的指令片段。打包本身不安装技能、不修改配置。[示例指南](docs/TRY-IT.md) 提供临时项目中的完整步骤。

每个生成技能都带齐依赖。不要只复制源码里的 `SKILL.md` 薄入口。

**旧 Claude 插件用户**：插件分发和可选 `digest` agent 已移除，升级前请读[迁移说明](docs/MIGRATION.md)。

## 需要时再展开

| 技能 | 用途 |
|---|---|
| `ctx-kickoff` | 开始或复用任务记录 |
| `ctx-status` | 查看进度、未决问题和待办 |
| `ctx-handoff` | 交接当前工作，或结束完成的任务 |
| `ctx-takeover` | 在后续会话接手已有任务 |
| `ctx-review` | 按你的要求送审和回收意见 |
| `ctx-checkup` | 检查协作记录及可取得的上下文用量证据 |
| `ctx-profile` | 按明确保存与适配步骤管理个人上下文 |
| `ctx-method-doc` | 编写面向实践的方法说明 |

每个案只有一位当前持笔，未处理消息和未完成事项保存在项目文件中，由接手方核对。多会话协作见[操作手册](docs/HANDBOOK.md)。

## 适用范围

适合跨天任务、项目中途换会话，以及需要统览多项工作的人。一个聊天就能完成的小任务，通常无需额外记录。

这些工作流帮助 agent 维护和核对状态，不能保证无遗漏、不会出错，也没有确立普遍节省 token 的结论。打包通过不等于你的客户端已加载技能，安装说明列有实际验收步骤。

快速试用指南为英文，共用工作流与详细手册目前为中文。不同客户端的原生能力不同；缺少会话改名等工具时，文件流程仍可继续，并应如实报告限制。

## 给我们一个真实反馈

完成一次交接后，告诉我们：**新会话漏了什么，你又解释了什么？** 在 [issue](https://github.com/bestiaya/ctx-kit/issues/new?template=feedback.md) 留一段脱敏描述即可，请勿公开真实对话、案文件或其他私有材料。

如果它对你有帮助，欢迎 **star 仓库**，让其他开发者更容易找到。

[背景](docs/BACKGROUND.md) · [方法](docs/METHOD.md) · [FAQ](docs/FAQ.md) · [维护与验证](docs/MAINTAINING.md) · [MIT 许可证](LICENSE)
