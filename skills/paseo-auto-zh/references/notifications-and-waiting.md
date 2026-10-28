# 通知、等待与失联恢复

**什么时候读**：每个 Run 首次派活前；每次收到通知后；通知迟迟不来或 worker 像失联时。

## 目录

- [1. 唯一的唤醒机制](#1-唯一的唤醒机制)
- [2. 通知长什么样](#2-通知长什么样)
- [3. 一次性与重新武装](#3-一次性与重新武装)
- [4. 等待纪律](#4-等待纪律)
- [5. 通知没来时](#5-通知没来时)
- [6. 没有 MCP 时的有界档](#6-没有-mcp-时的有界档)
- [7. 台账](#7-台账)

---

## 1. 唯一的唤醒机制

Paseo 不提供 Orca 那样的收件箱轮询。supervised worker 的唤醒来自 **finish notification**：

- agent-scoped `create_agent` + `notifyOnFinish: true` 会登记一个完成观察者；
- worker 完成、出错、请求权限、被关闭时，Paseo 把一条通知消息送进 coordinator 的会话；
- 通知以 `steer` 方式投递，即使 coordinator 正在别的 turn 里也会被追加进来。

这条通知就是唤醒。**不要**为了「看看进度」去轮询 `list_agents`、`get_agent_status` 或
`get_agent_activity`；那会在 worker 正常工作时白烧调用，也会让你把「还在跑」误读成「没动静」。

## 2. 通知长什么样

完成 / 出错 / 被关闭：

```text
Agent <childAgentId> (<title>) finished.

<agent-response>
…worker 最后一条 assistant 消息（可能被截断到 4000 字符）…
</agent-response>
```

请求权限：

```text
Agent <childAgentId> (<title>) needs permission.

Respond with `respond_to_permission` using the `agentId` and `requestId` below.

<permission-request>
{"agentId": "...", "requestId": "...", "request": { ... }}
</permission-request>
```

被取消的消息会以 `errored` 事件出现；被关闭的是 `closed`。三者都不能当成「正常完成」。

`<agent-response>` 超过 4000 字符会带 `[truncated …; use get_agent_activity for the full response]`。
被截断时先 `get_agent_activity` 读全文，再分类。

## 3. 一次性与重新武装

**终态通知**（finished / errored / was closed / was canceled）是一次性的：触发后观察者就停止，
不会对同一 agent 的下一次空闲再发一次。**权限通知（needs permission）不是终态**：它不解除
观察者，按 `requestId` 去重，每个不同 requestId 各发一次；`respond_to_permission` 不改变武装
状态，权限解决后该 turn 结束时仍会收到一次终态通知——所以应答权限后既不要补发消息「重新武装」，
也不用退回轮询。

`send_agent_prompt` 在 agent-scoped 调用里默认 `notifyOnFinish: true`，会为这次新 turn
重新登记观察者。所以正常循环是：

```text
create_agent (武装) → worker 提问/完成 → 通知到达
  → 读响应 → 分类 → send_agent_prompt (重新武装) → 下一次通知
```

规则：

- 回答 worker 的提问一律用 `send_agent_prompt`，不要用别的通道；它同时负责重新武装。
- **不要**把 `notifyOnFinish` 设成 `false`，除非这个 worker 真的 fire-and-forget。
- 回执里的 `guidance` 是判断通知是否武装的现场证据：
  - 「You will get notified when the prompted agent finishes…」⇒ 已武装；
  - 「Observe completion using get_agent_status…」⇒ 没武装，按 §6 的有界档处理。

## 4. 等待纪律

- 派活完成后，把 agentId / workspaceId / 票 slug / 最后一次通知时间写进台账，然后**去做别的事**。
- 多票并行时，每张票一个 worker；谁先通知就先处理谁。不要为了「按顺序」空等某一张。
- worker 一次 run 10–30 分钟很常见；不要每两分钟查一次状态。
- 通知到达后同一步完成三件事：读全文 → 更新台账 → 分类处理（提问 / 完成 / 权限 / 故障）。

## 5. 通知没来时

通知可能因为 agent 从未起跑、通知观察者被替换、会话中途重启或 worker 直接崩溃而丢失。
按顺序取证，不要直接重派：

1. `get_agent_status({agentId})`：看 `status` 与 `pendingPermissions`。
2. `get_agent_activity({agentId})`：读最近事件与最后一条 assistant 消息。
3. workspace 实况：`git -C <workspace.cwd> status --porcelain`、`git log --oneline -5`、
   `git branch --show-current`。只读，不修改。
4. 若是权限请求，用 `list_pending_permissions` 交叉确认。

| 观察 | 动作 |
| --- | --- |
| `idle`，有完整完成消息 | 通知丢了但工作已结束；按完成处理，继续验收，不要求重发 |
| `idle`，最后消息是 `[[PASEO-ASK]]` | 按提问处理，用 `send_agent_prompt` 回答并重新武装 |
| `idle`，最后消息停在半截或工具调用后无结论 | 发一次明确的续跑指令（读 spec 剩余项、继续实施、按 spec 收尾），只发一次 |
| `running` | 已在工作；不要发消息，等通知 |
| `error` / `closed` / `canceled` | 读错误与 workspace 证据，按 [agent 恢复](agent-recovery.md) 处置 |
| agent 不存在 | 台账记录与实际状态不符；核对 agentId，不凭标题猜 |

续跑或补收尾最多一次。之后仍无进展，保留产物并报告阻塞；不循环发「继续」，也不另开一个
编辑同一票的 worker。

## 6. 没有 MCP 时的有界档

如果当前会话没有 Paseo MCP 工具（例如在终端里直接跑 Claude Code / Codex），只能用 CLI：

- `paseo run <prompt>` **默认前台阻塞到 agent 结束**，进程返回就是一次唤醒；用
  `--wait-timeout` 限制单次等待。它能拿到最终结果，但**不会**给父 agent 发完成通知。
- `paseo run --no-wait` 只拿到 agentId，之后用 `paseo wait <agentId> --timeout <秒>` 阻塞等待。
- `paseo send <agentId> --behavior steer --no-wait "<answer>"` 发送回答；CLI send 同样不武装
  通知。**必须带 `--no-wait`**：不带时 send 会前台阻塞到该 turn 结束、硬上限 600 秒，没有可
  缩短该等待的选项，与本档「单次前台等待 ≤60 秒」冲突。需要结果时另跑
  `paseo wait <agentId> --timeout 60`。
- 判断状态用 `paseo inspect <agentId> --json` 与 `paseo logs <agentId> --tail 40 --json`。

有界档的纪律：

- 单次前台等待不超过 60 秒；超时后读 `inspect` / `logs` / workspace 证据，再决定下一步。
- 连续三轮没有进展才按 [agent 恢复](agent-recovery.md) 处理。
- 环境必须交还控制权时，明确报告：仍在运行的 agentId、最后进展、台账路径、无法自动唤醒的限制。
  不能声称「会自动继续」。

## 7. 台账

每个 Run 一份，放在 repo 外（默认 `~/.paseo-auto/runs/<run-id>/ledger.md`）。至少记录：

```text
Run / coordinator agentId
每张票：workspaceId / workspace.cwd / agentId / branch / 最后通知时间 / 状态 / PR
每次提问：question id / 分类（决策/细节）/ 谁答 / 答案 / 依据
每次完成：通知时间 / 结论 / 验收结果
```

上下文压缩或恢复后，先读台账与 `get_agent_status` 的真实状态，不凭旧对话猜 agentId 或进度。
