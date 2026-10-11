# {{task_id}} {{task_name}}

所属项目：{{absolute_project_root}}
所属案/目标节点：{{case_id_or_goal}}
权威案位置：{{absolute_path_and_checkout}}
派发者：{{platform / thread_id / display_name}}
执行者：{{platform / thread_id / display_name_or_unassigned}}
派发者编号：{{案号-任期号 或 C00-散活登记行号；已有旧编号沿用，未派发写不适用}}
派定会话名：{{C07-03.1｜案短名-工作内容-exec；散活如 C00-02.1｜工作内容-exec；当前会话执行写不适用}}
子号依据：{{派发者已派记录及本次分配；未派发写不适用}}
派发状态：{{已准备 / 已派出；预留号占号，重试沿用本任务派定名，取消也不复用}}
版本/时间：{{version / ISO8601}}

## 目标与必要上下文

{{用户要求、相关方案的必要片段；独立验证不附预期答案或讨论者倾向}}

## 输入与边界

- 可读：{{paths_or_sources}}
- 可写：{{explicit_output_scope}}
- 不可触碰：{{real_constraints_only}}
- 工作目录/分支：{{cwd_and_branch_if_relevant}}
- 需要用户决定的条件：{{actual_decision_points_or_none}}

## 执行前约定的验收

{{已有基线、要验证的行为/指标、失败与部分完成如何判；未知不得补造成已知}}

## 交付与回收

- 输出目录：{{absolute_delivery_path}}
- 人读结论与结构化数据/原始证据：按 DELIVERY 模板。
- 通知目标：{{recipient_thread_id_if_authorized_or_offline_inbox_path}}
- 回收者：{{case_owner}}
- 执行者写自己的交付件；由持笔更新案 E/B/C，避免并发覆盖。

## 变更记录

{{判据/范围改变时记原因、时间和授权来源；没有则写无}}
