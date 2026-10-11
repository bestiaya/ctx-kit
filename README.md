# context-kit · 多会话协作工具包

版本：**v0.14.0**。公开源码：[bestiaya/ctx-kit](https://github.com/bestiaya/ctx-kit)。

让复杂任务跨会话继续：任务板找到工作，案文件保存当前状态，持笔明确谁负责更新，收件位追踪跨会话事项。

Claude 与 Codex 共用方法、工作流和模板；平台目录只维护安装、工具调用和证据差异。

## 从哪里开始

- 使用 Claude：看 [Claude 安装说明](claude/README.md)。
- 使用 Codex：看 [Codex 安装说明](codex/README.md)。
- 理解方法：[背景](docs/BACKGROUND.md) → [方法](docs/METHOD.md) → [操作手册](docs/HANDBOOK.md)。
- 有疑问：看 [FAQ](docs/FAQ.md)。

| 你要做的事 | 工作流 |
|---|---|
| 开一个需要多轮推进的工作 | `ctx-kickoff`：确定项目、关联目标、建案或复用案、命名 |
| 看多个任务目前到哪里了 | `ctx-status`：读板与案，汇报状态和待处理事项 |
| 把当前工作交给后续会话，或结束某个案 | `ctx-handoff`：识别交接或结案；支持“这个案不用了”，保留历史并安置余项 |
| 接着一个已有案继续，或恢复旧案 | `ctx-takeover`：识别终态、按明确恢复意图重开，再核验与认领 |
| 把方案交给另一方审核，或回收意见 | `ctx-review`：围绕目标讨论，CLI 发起并回收，确认后再改 |
| 检查协作记录和上下文开销 | `ctx-checkup`：检查一致性，按平台证据审核 |
| 管理个人配置、手动议题与关键事项 | `ctx-profile`：七个动作统一入口，查看与历史查询不自动保存 |
| 把工作或判断的方法讲清楚，供读者实践 | `ctx-method-doc`：按用途组织流程指南、判断方法或概念说明 |

`ctx-profile` 的 `init/show/update/adapt/export/topic/task` 分别用于建立、查看、修改、接入、导出个人上下文，以及手动议题和全局事项；无动作默认查看。详见 [个人上下文流程](workflows/profile.md)。个人配置不复制项目状态，topic/task 按明确保存请求写入。适配与安装分别授权，生成入口不等于原生客户端已验证；不会自动恢复已清理的 Claude 环境。

`ctx-review to claude` 或自然语言送审，默认通过 Claude CLI 讨论并回收意见。审核聚焦整体判断、实质异议和推荐方案，不默认逐链接核验；讨论结果经用户确认后再改文件。调用方管理版本与有限轮次，用户也可明确选择人工转读；详见 [方案送审流程](workflows/review.md)。

`ctx-method-doc` 沉淀面向实践的方法说明写法，按工作顺序、判断过程或概念关系选择主线，保留认可原句与来源边界。详见 [写作流程](workflows/method-doc.md)；普通 README、案卷、短邮件和纯数据报告沿用各自文类，不自动套用。

## 文件分工

```text
docs/          共用背景、方法、操作手册、FAQ
workflows/     协作、个人上下文与方法说明文档写作的唯一维护源
templates/     任务板、案、任务书、交付与审核记录模板
claude/        Claude 安装、平台规则、历史实验与现有辅助工具
codex/         Codex 安装、原生会话工具适配与待验证依据
scripts/       打包、结构检查、个人主档与原生历史读取工具
tests/         安装包可搬移、覆盖保护与历史脚本的验证
```

技能源码入口引用共用内容。打包时把依赖复制进每个 skill；生成副本不单独维护，安装后不依赖本仓库路径。

两端发布包各含八个技能；`ctx-profile` 另携带三个标准库脚本，可以单独搬移执行。发布输入采用白名单，不包含个人主档、正式 config、案、交付或本机个人绝对路径。打包不修改已安装的技能或全局接入配置。

真实工作记录留在目标项目既有的案库、任务与交付目录。安装不会创建真实任务或认领持笔。

直接说“终止 C-07”“看当前进展”“重新做 C-07”即可，不必记新 skill 或子命令。进展默认聚焦活跃案，同时报告已结束案的收尾异常；说“包括历史案”可查看结案原因与替代关系。详见 [操作手册](docs/HANDBOOK.md#案不用了做完了或被替代)。

## 两个仍待审核的问题

1. 缓存冷却时，交接后再开会话能否节省整体开销；500k 和一小时间隔目前只是候选观察条件。
2. 当前 GPT 模型在超过实际可用窗口 50% 后，复杂任务表现是否有稳定退化。

公开资料、推论、历史实验与本地实测分开记录。Codex 不预设自动 takeover 阈值，详见 [Codex 证据与审核计划](codex/EVIDENCE.md)。

## 维护与验证

需要 Python 3.9+；打包及仓库检查只用标准库。在本目录运行：

```bash
python3 scripts/check_kit.py
python3 -m unittest discover -s tests -v
python3 scripts/build_package.py --platform codex --output /tmp/context-kit-codex
```

最后一条仅写入指定的新目录；不修改用户配置，不联网、不安装、不 commit/push。目录已存在则拒绝覆盖。

源码链接检查按发布输入清单执行（根入口、共享资源及两端安装源），不扫描案、交付、验收目录或快照；发布源引用非发布文件仍会报错。生成包则检查包内全部 Markdown，继续拒绝缺失或越界依赖。

原文件迁移对应关系及行为差异见 [迁移说明](docs/MIGRATION.md)。

## 从 v0.13 升级

本版采用共用流程加 Claude/Codex 双端入口。`ctx-init` 不再独立提供，项目开工使用 `ctx-kickoff` 和任务板模板；`ctx-forhuman` 已退役。旧版水位提示、case-lint、takeover-load 与旧同步脚本不随本版加载，历史保留在原版本中。新版不按固定时间或 token 水位强制交接。

Claude 插件用户可沿用此 marketplace：

```text
/plugin marketplace add bestiaya/ctx-kit
/plugin install ctx-kit@ctx-kit
```

手动安装与 Codex 安装请先按平台说明生成自足技能包，不要把源码薄入口单独复制。已有安装先核对旧技能和 hook 配置；源码更新不会自动删除机器上的旧配置。

公开提交不包含真实案卷、运行日志、个人主档、本机配置或凭据。维护者在提交前运行 `python3 scripts/check_public.py`，检查暂存/跟踪清单，而不是对整个本地目录执行全量上传。
