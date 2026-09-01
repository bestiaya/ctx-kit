---
name: ctx-status
description: 查看现状。用户说"现在什么情况""进展如何""有哪些案""资产都在哪""看一下板"，或显式 /ctx-status 时用。读任务板与案文件，人话汇报目标链、各案状态、待拍板项与散活，不让用户翻文件。 Report status — use on "what's the status", "where do things stand", "show the board", or /ctx-status; reads the board and case files, reports goal chain, case states, pending decisions and one-offs in plain language.
---

# 查看：板 → 案 → 人话汇报

## 1. 读什么（只读这些，不翻转录、不翻交货件正文）
- **任务板**（案目录内的 `TASKBOARD.md`，如 `_ops/CASES/TASKBOARD.md`；旧位 `_ops/TASKBOARD.md` 为后备）：头部目标链 + 案索引 + 散活区。无板 → 改读案目录文件列表，并提示"建议建板"。
- **每个活跃案**的：头行（状态/持笔/更新日期）+ A 节 M 读数 + D 节前三项。案多时只展开用户点名的，其余一行带过。

## 2. 汇报格式（固定四段，人话）
1. **目标链**：产品总目标一句 + 各线一行（节点 / 目标 / 状态）；
2. **各案现状**：案号+人话名 | 持笔在谁 | 最新读数 | 头号未决（候谁）；
3. **等负责人的**：各案 D 节"候拍/候校订"项汇总，每项一句 + 建议；
4. **散活与在跑**：板散活区 + 各案 E 台账里"在跑/待验收"的行。

## 3. 纪律
- 数字只报盘上有的；无读数明说"无数"，**不猜、不引转录里的旧状态**。
- 板与案不一致 → 两边都报并标"待对齐"，不悄悄采信一边。
- 首答不超一屏；用户点名某案/某件才往深处读。
- 汇报完即停，不追加建议清单（用户要建议会问）。
