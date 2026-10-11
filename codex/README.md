# Codex 版

用于复杂任务的多会话协作。共用 [方法](../docs/METHOD.md)、[操作手册](../docs/HANDBOOK.md) 和模板；Codex 差异集中在 [平台适配](setup/PLATFORM.md)。

## 安装

先从工具包根目录生成自足包，输出目录必须尚不存在：

```bash
python3 scripts/build_package.py --platform codex --output /tmp/context-kit-codex
```

生成目录含 `skills/ctx-*`、`AGENTS-snippet.md`、`INSTALL.md` 和文件哈希清单。每个 skill 内有依赖的共用流程与平台规则，可以搬移后独立使用。不要直接只拷源码中的 skill 入口。

推荐项目级安装到目标项目 `.agents/skills/`；用户级位置为 `~/.agents/skills/`，见 [官方技能目录说明](https://learn.chatgpt.com/docs/build-skills)。已有环境若实际使用 `~/.codex/skills/`，按其生效配置处理，不自动迁移。避免项目级、用户级同时有同名 `ctx-*`。

发布包含原五个协作技能、`ctx-profile`、`ctx-review` 及 `ctx-method-doc`。复制前检查所选目标目录均不存在；已有同名版本先备份并明确替换范围。示例在**目标项目根目录**执行（一次只运行一行/一段，失败先处理）：

```bash
mkdir -p .agents/skills
# 确认 .agents/skills/ctx-* 没有同名安装后，再复制八个目录
cp -R /tmp/context-kit-codex/skills/ctx-* .agents/skills/
```

将包内 `AGENTS-snippet.md` 的代码块合入目标项目既有 `AGENTS.md`，不要覆盖原文。工具包不自动修改全局配置或活动会话。使用客户端技能列表确认已发现；必要时按客户端要求新开会话或重启。

## 使用

说“开始这个复杂任务”“看任务板”“交接”“接手某案”“检查协作记录”，或在支持的 Codex 输入框中选择 `$ctx-kickoff`、`$ctx-status`、`$ctx-handoff`、`$ctx-takeover`、`$ctx-checkup`。

个人上下文统一使用 `$ctx-profile`；可自然表达“查看个人配置”“修改我的使用习惯”“保存当前讨论为话题”“记录一个关键事项”。七个动作见 [共用流程](../workflows/profile.md)，无动作默认 `show`。查询不保存，主档不复制项目状态。技能随包携带主档与历史读取脚本；安装技能不自动初始化主档或 adapt，真实客户端加载仍需单独验证。

会话命名与 Claude 共用 [METHOD](../docs/METHOD.md#会话命名)：例如 `C07-01｜计费-方案讨论`，编号来自案号与案头任期；派生执行为 `C07-01.1｜计费-压测-exec`，散活读取板上登记行号。无需查询会话列表取号，用户指定名和运行中的旧名保留。Codex 仅适配原生改名、稳定 ID 与回读工具。CLI/IDE 没有标题工具时仍保留文件流程，并如实记录 UI 未同步。

方案送审使用 `$ctx-review to claude`，或说“把当前方案交给 Claude 审核”；默认由调用方通过 CLI 发起、监测并回收，审核方聚焦思路和实质异议，用户确认后再改文件。见 [共用送审流程](../workflows/review.md)。用户明确选择时保留人工转读；安装不会替换项目专用旧入口，冲突仍按明确授权处理。

方法说明文档写作可使用 `$ctx-method-doc`，或说“使用方法说明文档写作”。例如：“为开发负责人写一份存量系统变更影响分析的方法说明，让读者知道怎样开始、各步形成什么输出，以及如何进入验证。依据以下材料……”按 [共用写作流程](../workflows/method-doc.md) 处理，用户对文档有异议时先回应、明确同意后再改；明确修改请求直接按授权执行。

## 安装后的验收

用临时项目建一个案并关联任务板；确认名称和 ID 正确。准备一条离线来件，交接后在新聊天接手：H 缺口被保留、I 与离线来件被读到、案与任务 ID 没变、持笔只有一位。最后核对真实交付和 Git 状态。

静态/打包检查不代表以上原生交互已经通过。本地复杂任务的缓存收益与 50% 质量假设仍待审核，见 [EVIDENCE](EVIDENCE.md)。

`ctx-profile` 先用临时 `--root` 验证默认只读、写入预览、适配幂等、同步和手动保存；不要用测试覆盖个人正式主档。原生加载验证应从当前客户端的真实入口读取新内容，脚本成功不能替代此证据。

## 升级与卸载

备份安装目录，明确替换所选 skill 及对应常驻片段，不覆盖其他技能。卸载只移除本次安装的目录与自己合入的指令片段；个人主档、目标项目中的任务板、案和交付记录保留。

## Token 统计器

源码 `codex/setup/scripts/token-audit.py`，生成包位于 `skills/ctx-checkup/scripts/token-audit.py`。使用项目 Python 3.9+ 环境；仅需标准库。显式指定日志文件，可一次传入多个文件：

```bash
python3 codex/setup/scripts/token-audit.py /path/to/rollout.jsonl
python3 codex/setup/scripts/token-audit.py /path/to/rollout.jsonl --model gpt-6-astra --json --records
python3 codex/setup/scripts/token-audit.py /path/to/rollout.jsonl --since 2026-10-08 --until 2026-10-09 --timezone Asia/Taipei --json
```

时间区间为左含右不含；无时区的日期/时间使用 `--timezone`，默认 Asia/Taipei。可直接读 context-kit 提取的 `request_records` 用量快照 JSON，不读取对话正文或认证配置。输出只写 stdout，不改源文件或自动安装技能。

默认以唯一响应 ID 去重，完整保留独立压缩响应。旧日志只有 `token_count` 时回退累计增量，重复累计通知不多算；可以用 `--source token-count` 对照旧工具口径。兼容增量不一定对应一次请求，模型分组可能受缺失元数据限制。

报告区分完整输入、缓存读取、未命中输入、写入、输出/推理分项、原始总数及加权数。默认配置只覆盖 `gpt-6-astra`；混入其他模型时总加权数为 `null`，同时提供 `weighted_covered_records` 与部分小计。用 `--model` 筛选可比模型，或提供自己的固定配置：

```json
{"id":"my-fixed-v1","models":["exact-model-name"],"weights":{"uncached_input":"1","cached_input":"0.1","output":"5"}}
```

以 `--profile /path/to/profile.json` 加载；A/B 使用同一配置哈希。权重固定，不计算价格、峰谷或订阅额度。未知字段保留 `null`。JSON 中 `status=partial`（退出码 2）表示存在坏行、冲突、缺失或累计覆盖问题；`issues` 和 `source_files` 保存证据位置、文件哈希和校验结果。`unmatched_token_count` 也需检查，它可能出现在压缩或混合日志处，不能因为退出码为 0 就认定全部通知都已解释。

与其他统计工具比较时使用相同文件字节快照、时间范围、模型范围与字段定义。某些工具的 `inputTokens` 指未缓存输入，需加缓存分项才与这里的 `input_tokens` 对齐；压缩/重试的记录范围也应逐项核查。
