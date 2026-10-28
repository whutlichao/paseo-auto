# agent 派活失败、权限与失联恢复

**什么时候读**：`create_agent` 失败、turn 没有开始、收到权限请求、agent 报错 / 被关闭 /
被取消，或 worker 长时间无进展时。正常路径不读它。

## 1. `create_agent` 失败

先读错误，再决定；不要无条件重试，也不要换一个 provider 猜。

| 错误 / 现象 | 取证 | 动作 |
| --- | --- | --- |
| provider/model 不被识别 | `inspect_provider({provider})`；`list_models` | 用返回的合法 model 重建；仍不行就报告 provider 配置问题 |
| workspace 不存在 / 无权访问 | `list_workspaces`；核对台账里的 workspaceId | 用正确 workspaceId；workspace 丢了就重建同一分支的 workspace（`checkout-branch`） |
| worktree 创建失败（分支已存在、base 解析失败） | 读 `create_workspace` 错误；`git -C <repo> branch --list <slug>` | 分支已存在时改用 `mode: "checkout-branch", branch: <slug>`；base 写 §0 解析出的本轮默认 base |
| 首条 prompt 被拒绝 / 立即 idle | `get_agent_status`；`get_agent_activity` | 检查 spec 是否为空、是否超长、是否含 provider 不接受的附件；修正后重建 |

重试前必须确认失败原因已消除。同一原因的连续失败按 §6 熔断处理，不无限重试。
**不要**为绕过失败而把 worker 建到 main 工作区。

## 2. turn 没有开始

`create_agent` 返回 `status: running` 只说明 provider 接受了 turn；是否真的开始，用
`get_agent_status` 与 `get_agent_activity` 判断：

- 有 `turn_started` / 工具调用 / assistant 输出 ⇒ 已开始，等待通知。
- 仍是 `running` 但无任何事件，且刚创建 ⇒ 可能仍在初始化；给一次通知的等待窗口。
- `idle` 且无 assistant 输出 ⇒ 起跑失败。读活动里的错误；必要时发一次
  `send_agent_prompt`：「从 spec 第一条开始执行；遇到决策类问题按 `[[PASEO-ASK]]` 结束回合」。
  这次发送会重新武装通知。
- `error` / `closed` ⇒ 按 §5 处理。

不要连续发「继续」；一次续跑后仍无事件，按失败处理并保留现场。

## 3. 权限请求

通知会带 `<permission-request>` JSON（`agentId`、`requestId`、`request`）。

1. 读 `request` 的具体操作、目标路径、命令与风险。
2. 只处理本轮已授权的操作。项目内的读写、运行测试、提交、推送通常已在实施授权范围内；
   凭证、第三方账号、付费、人工审批、不可逆 live 数据操作必须按 §5 升级给人。
3. 批准：
   - MCP：`respond_to_permission({ agentId, requestId, response })`，
     `response` 用该 provider 要求的形状（通知里的 request 会给出可接受值）；
   - CLI：`paseo permit allow <agentId> <requestId>`，或 `--all` 批准该 agent 的全部待决请求。
4. 拒绝：`paseo permit deny <agentId> <requestId>`，并给 worker 一条说明原因的
   `send_agent_prompt`，让它换一条已授权路径。
5. 处理后 `list_pending_permissions` 复核，确认没有残留。

不得把「允许」当默认，也不为避免提示而切到 bypass / full-access 模式。

## 4. 通知丢失

先按 [通知与等待](notifications-and-waiting.md) §5 的三处取证（status / activity / workspace），
再决定。常见结论：

- agent 已 idle 且产物完整 ⇒ 通知丢了，工作没丢；直接验收。
- agent 已 idle 但停在半截 ⇒ 一次续跑指令。
- agent `running` ⇒ 等通知，不打扰。

## 5. agent 报错、被关闭或被取消

1. 读 `get_agent_activity` 的最后错误与最后一条 assistant 消息。
2. 读 workspace：`git status`、`git log --oneline -5`、`git branch --show-current`。
   **先确认已提交的工作是否已持久化**；未提交的改动按
   [格式化恢复](reformat-noise-recovery.md) 的保护步骤处理，不要直接 reset。
3. 分支已提交但未推送：让替代 worker 先推送，再继续。
4. 可恢复（同一 workspace、同一分支）：在原 workspace 建替代 agent，spec 里写明
   「已有提交 `<sha>`，从当前分支继续；不要重做已完成部分」。
5. 不可恢复：保留产物与证据，报告阻塞；不另开一个空白 worktree 重做整票。

同一票始终只有一个活跃编辑者。替代 agent 建好后，旧 agent 归档，避免两条分支并行。

## 6. 停止条件

- 同一原因连续两次派活失败 ⇒ 停下问人，附精确错误与已排除项。
- 同一票连续 2 次过不了同一门禁 ⇒ 单票熔断，暂停该票并请人决定。
- run 级累计打回达到 5 次，或长时间无实质进展 ⇒ 停止新派活，安全收尾在途工作并报告。
- 权限请求涉及 escalation 五类 ⇒ 立即升级，不自动批准。
