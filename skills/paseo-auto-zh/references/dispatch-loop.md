# 派活闭环：profile 物化、workspace/agent 参数、turn 确认

**什么时候读**：每次 B/C 派活都读，以获取完整的 `create_workspace` / `create_agent` 参数、
profile 物化细节、turn 确认方式，以及无 MCP 时的 CLI 降级写法。

## 4.2 profile 物化

派活前 `list_profiles` 一次，读每个 profile 的 `notes`：

1. 用户点名 profile → 按名字选。
2. 否则选 notes 最贴合本票工作的一个（设计/审查/研究/实施分开匹配）。
3. 多个都合适时，优先与 coordinator 不同 provider family 的，减少同源盲点。
4. 没有合适 profile → 用 `list_providers` / `inspect_provider` / `list_models` 发现，
   并把「回退路径」写进本轮报告。

把 profile 物化进 `create_agent`：

```text
provider  = "<profile.provider>/<profile.model>"
settings  = {
  modeId:          <profile.modeId>,
  thinkingOptionId:<profile.thinkingOptionId>,
  features:        <profile.featureValues>
}
```

缺项省略；不要保留 `profile` 字段（`create_agent` 没有这个参数），也不要跨 Run 复用记忆值。
只设置 `inspect_provider` 返回过的 feature ID。

## 4.3 两步派活

### 第一步：建 worktree workspace

```text
create_workspace({
  isolation: "worktree",
  mode: "branch-off",
  path: "<目标 repo 绝对路径>",
  branchName: "<票 slug>",
  baseBranch: "<本轮默认 base，通常 origin/main>",
  worktreeSlug: "<票 slug>",
  title: "<票标题>"
})
```

返回 `{ workspaceId, projectId, cwd, isolation, kind, title, background }`。
把 `workspaceId` 与 `cwd` 写入台账；`cwd` 是后续只读取证与验收的工作目录。

约束：

- `path` 必须是源 checkout 的绝对路径；daemon 在它自己的机器上解析这个路径。
  会话 cwd 与目标 repo 不一致时尤其不能省略。
- `baseBranch` 显式写 §0 解析出的本轮默认 base（通常是 `origin/main`）。裸 `main` 会优先本地
  main，可能不是你想要的基线；硬编码 `origin/main` 在非 main 默认分支仓库会直接失败。
- 一张票一个 workspace。不要复用另一张票的 workspace，也不要用 `isolation: "local"`
  把 worker 放进现有目录。
- `background` 省略。只有用户明确要求隐藏时才传 `true`。

### 第二步：建 agent

```text
create_agent({
  title: "<票标题>",
  provider: "<profile.provider>/<profile.model>",
  workspaceId: "<第一步的 workspaceId>",
  initialPrompt: "<§4.4 的完整 spec>",
  notifyOnFinish: true,
  labels: { "ticket": "<票 slug>", "run": "<run id>" },
  settings: { ... }
})
```

回执至少取 `agentId`、`status`、`workspaceId`、`guidance`。`guidance` 含
「You will get notified…」才说明完成通知已武装；否则按通知参考的有界档运行。

**不用** `create_agent` 省略 `workspaceId`：那会落在 coordinator 自己的工作区（agent-scoped），
或在顶层调用时新建一个 local workspace——都不是本 skill 允许的实施落点。

## 4.3.1 确认 turn 开始

1. 回执 `status: running`：turn 已被 provider 接受。
2. `get_agent_status({agentId})`：仍是 `running`，或已有工具调用/assistant 输出 ⇒ 已开跑。
3. 回执 `status: idle` 且 `get_agent_activity` 里没有 `turn_started` / 工具调用 / assistant 输出：
   - 没有 `error` ⇒ 初始 turn 没有起跑，按 [agent 恢复](agent-recovery.md) §2 发一次明确续跑
     指令（该 send 会重新武装通知）；
   - 有 `error` / 立即 `closed` ⇒ 按 agent-recovery 取证；
   - 仍无事件 ⇒ 按失败取证，不盲等——初始 turn 未起跑时不会有终态通知。
4. 返回 `guidance` 是「Observe completion…」⇒ 通知没武装。不要假装能自动继续；
   改用有界等待，或改用带 MCP 的调用方。

## 4.3.2 长程派活（一张票图一个 worker）

G-tickets 验收完整票图后，为整张图启动 **一个** worker：

```text
create_workspace({ isolation: "worktree", mode: "branch-off",
  path: <repo>, branchName: "<feature>-integration",
  baseBranch: "<本轮默认 base，通常 origin/main>",
  worktreeSlug: "<feature>-integration", title: "<feature> integration" })
create_agent({ title: "<feature> integration", provider: <profile>, workspaceId: <ws>,
  notifyOnFinish: true, initialPrompt: <长程 spec> })
```

spec 以 `implement-spec` 为前置 skill，带 `Tracker：` / `Spec：` / `Tickets：` /
`Integration branch：` 指针（见 [长程票图](long-horizon-tickets.md)）。它必须先证明能为
implementer 建隔离 workspace 与 agent，再花整张图；不能证明就串行跑 implementer，
或由 coordinator 回退到逐票 worker（默认并发 3）。coordinator 只验收唯一的集成 PR。

## 4.5 通信闭环

- 派活后不轮询；完成 / 提问 / 权限都会以通知形式回来。
- 每次收到通知：读全文 → 更新台账 → 分类 → 处理。回答提问用 `send_agent_prompt`
  （默认 `steer`，同时重新武装通知）。
- 一次 worker run 10–30 分钟很常见。通知到达前去做其他票或其他已授权工作。
- 通知丢了但 agent 已 idle：读活动与 workspace 证据继续，按
  [通知与等待](notifications-and-waiting.md) §5 处理。

## 4.6 无 MCP 的 CLI 降级

只在 MCP 工具不可用时使用。CLI **不会**给父 agent 发完成通知，所以必须用有界档。

```bash
# 建 workspace
paseo workspace create --isolation worktree --mode branch-off \
  --path "<repo>" --new-branch "<slug>" --base "<本轮默认 base，通常 origin/main>" \
  --worktree-slug "<slug>" --title "<票标题>" --json
# 派 agent（--no-wait 立即返回 agentId）
paseo run --provider "<provider/model>" --mode "<modeId>" \
  --thinking "<thinkingOptionId>" --workspace "<workspaceId>" \
  --title "<票标题>" --label "ticket=<slug>" --label "run=<run-id>" \
  --no-wait "<spec>"
# 后续
paseo wait <agentId> --timeout 60
paseo inspect <agentId> --json
paseo logs <agentId> --tail 40 --json
paseo send <agentId> --behavior steer --no-wait "<answer>"   # 不带 --no-wait 会阻塞至多 600 秒
```

`paseo run` 不带 `--no-wait` 时会前台阻塞到结束；Bash 工具的超时与应用层一致时，
优先用 `--no-wait` + 有界 `paseo wait`，避免一个长任务把调用拖死。

## 4.7 归档

- 合并并同步主分支后：`archive_agent({agentId})`，再按需 `archive_workspace({workspaceId})`。
- `archive_workspace` 会归档其 agent 与终端，并在最后一个活动引用归档后移除 Paseo 拥有的
  worktree。**只在分支已推送、PR 已合并后使用**；开放 PR 时保留 workspace 到人类处理完，
  除非用户明确要求清理。
- 单向门保留开放 PR 时：agent 保留到该票确定不再跟进（PR 合并或人类接手）后再归档；
  workspace 保留到人类处理完，除非用户明确要求清理。远端分支必须先确认已推送。
- 归档时机的权威判据是 [gate-acceptance](gate-acceptance.md) 的「agent 生命周期与打回」，
  本节与其冲突时以它为准。
