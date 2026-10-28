---
name: paseo-auto-zh
description: >-
  当用户要在 Paseo 里派活、监督多个任务，或把已授权的开发/规划工作推进到验收与自动合并时，使用本 skill。
  覆盖：为一张及以上票在独立 worktree 建 supervised worker；把完整票图交给 `implement-spec` 做长程实施；
  用集成 PR 的 Merge Danger 决定自动合并还是交人；门禁验收、打回、PR 合并与主分支同步；流程出错后的 retro。
  也覆盖 Paseo 执行受阻时的处置与请示：daemon 起不来、`paseo status` 超时、MCP `create_agent` /
  `send_agent_prompt` 报错或 permission denied、通知丢失、agent 崩溃失联、需要按规则上报或熔断——
  用户问「这轮还能怎么继续」「是否上报」「别乱重派」时同样使用；此时先取证、精确报告，绝不擅自重派。
  用户提到 Paseo 编排、worker 派活、workspace/worktree 隔离、门禁验收、PR 自动合并或派活故障排查，都用本 skill。
  排除：Orca / Orca worker 改用 `orchestra-auto-zh`；只需线程消息与 DAG 协调用 `orchestration`；
  单 agent 查询与操作、第二意见、交班分别走 `paseo` / `paseo-advisor` / `paseo-handoff`。
  纯问答及阅读、审查或修改本 skill 不启动编排。
---

# Paseo Auto — 全自动派活闭环

你是 coordinator。先确定用户要求的工作范围。凡本轮要落盘到项目仓库的改动，默认由 worker
提交、推分支、创建 PR；门禁通过后由 coordinator 自动合并，并同步主分支。用户已授权
此默认流程，合并前无需再请示。「改完开 PR」「给我个 PR」说的是交付方式，不是本轮停在哪；
开放 PR 例外只认明确要求**不合并、保留 PR 自己看**这一种。用户要求该例外、仓库规则阻止合并
或门禁未过时，保留 PR 并如实报告状态；纯问答与不写仓库的报告不创建 PR。

人在三种时刻出现：任务开始时说了一句话；worker 提出决策类问题时被请来定夺（§5）；
遇到必须人类处理的问题（凭证/第三方/审批/权限）。**auto 自动的是流程（派活 / 门禁 / 打回），
不是决策**——worker 给的推荐答案只是参考信息，凡 §5 判为决策类的提问，附上你的倾向
请人定夺之后才回复 worker。

本 skill 提供编排流程；用户请求、仓库约定与 Paseo 当前工具契约决定本轮范围与执行方式。
通道判定见 §1，角色边界见 §2，派活参数见 §4。
不依赖 repo 的 `AGENTS.md` 是否有 `WORK_SCOPE` 一节——**缺它不构成停止理由**。

```text
用户输入 → §1 确定交付终点与通道 → §2 铁律自检 → 需要编辑时 §4 建 workspace + agent
              → 完成/提问通知到达时 §5 应答（决策问人）→ §6 门禁验收
              → 打回 or 推进 → 双向门 PR 通过 G-merge 后 §6.5 自动合并
              → 归档 agent / workspace → §7 收口报告；达到约定交付终点即停止
```

`references/` 下的文件按条件读取，SKILL.md 保留路由和核心约束：

| 文件 | 什么时候读 |
| --- | --- |
| `references/dispatch-preflight.md` | 每次派活之前（逐项打勾），以及 worker 报完成后、宣称门禁通过前的收尾检查 |
| `references/dispatch-loop.md` | 每次 B/C 派活时（workspace/agent 完整参数、profile 物化、turn 确认、CLI 降级） |
| `references/spec-contract.md` | 给 worker 写 spec 时，任何通道、任何票型 |
| `references/reply-protocol.md` | 对 worker 提问分类或应答，或判断升级问人还是代答时 |
| `references/gate-acceptance.md` | 票据收尾、要选门禁时；合并项目 PR 或归档 agent / workspace 时 |
| `references/notifications-and-waiting.md` | 首次派活前、每次收到通知后、通知没来或 worker 失联时 |
| `references/agent-recovery.md` | `create_agent` 失败、turn 未开始、权限请求、agent 崩溃或被关闭时 |
| `references/long-horizon-tickets.md` | G-tickets 已验收完整票图且本轮要实施；或流程错误后需要 retro 时 |
| `references/gates-docs-planning.md` | 手上是设计票 / 规格票 / 拆分票，准备过 G-docs / G-wayfinder / G-spec / G-tickets |
| `references/reformat-noise-recovery.md` | §4.0.1 检出万行级未提交改动（格式化重排噪声） |
| `references/failure-and-reporting.md` | Paseo daemon 不可用、MCP 工具缺失、熔断触发或需要上报时 |

## 0. 执行编排时初始化；编辑本 skill 不启动编排

只有当前任务确实要求执行 Paseo 编排时才进入以下流程。用户要求修改、审查本 skill 时，
它是待编辑材料，不创建 workspace、不派 agent、不因读到正文自行切换角色。先按 §1 判断本轮是否真的要派 worker。

即将派活时确认 Paseo 控制面可用：优先使用会话内的 Paseo MCP 工具
（`create_workspace`、`create_agent`、`send_agent_prompt`、`get_agent_status`）；MCP 不在时
退回 CLI，要求 `paseo status --json` 能报告 daemon 正常，否则停止并报告。**派活一律优先走
MCP**：只有 MCP `create_agent` / `send_agent_prompt` 会武装完成通知；CLI 派活不会（详见
[通知与等待](references/notifications-and-waiting.md)）。

即将派活时读一次 `list_profiles`，记录本轮可用 profile 及其 `notes`；用户点名的 profile 优先，
否则选 notes 最贴合本票工作的一种。没有合适 profile 时用 `list_providers` / `inspect_provider`
发现能力，并明确告知用户这是回退路径。profile 只是启动配置，不要跨 Run 记忆或推断漂移。
纯 A 通道答复不查 profile。

```text
模式 paseo-auto | 通道 <A|B|C> | 意图 <任务类型> | 前置 skill <实际路径 / 无> | worker <profile → provider/model / 无> | 交付终点 <答复 / 报告 / 项目改动合并 / 用户明确指定的其他终点>
```

六栏都要给**具体值**，不许写「待定」。不派活时 worker 写「无」；派活时前置 skill 栏必须写成
`<skill 根>/<name>/SKILL.md` 形式的**实际绝对路径**，取值按 §1 的请求类型：单票实施 = `implement`、
修 bug = `diagnosing-bugs`、研究 / 设计 / 规格 / 拆票 = `research` / `grill-with-docs` / `to-spec` /
`to-tickets`、完整票图 = `implement-spec`。裸 skill 名不算数，spec-contract 要求的正是绝对路径。
worktree 名派活时再取 slug。

每轮首次派活前解析一次**本轮默认 base**：`git symbolic-ref --short refs/remotes/origin/HEAD`，
失败时用 `gh repo view --json defaultBranchRef --jq .defaultBranchRef.name`；解析结果写进模式声明与
台账，后文所有 `baseBranch` 都用它。硬编码 `origin/main` 在默认分支为 `master` / `develop`
或远端不叫 `origin` 的仓库会直接让 worktree 创建失败，或从错误基线切出分支。

## 1. 通道与交付终点

记录用户要什么、停在哪里。项目改动默认自动创建并合并 PR；单向 Merge Danger 门例外，
保留开放 PR 给人类手动合并。探索可改实现路径，不可擅自扩大工作范围。

| 请求 | 通道 | 处理 |
| --- | --- | --- |
| 解释、状态、讨论或口头研究结论 | A | 直接答复；不派 worker，不写仓库 |
| 边界清楚的小改动、修 bug、已有 spec 或票 | B | 只读探索后派实施 worker；修 bug 先用 `diagnosing-bugs` |
| 必须落盘的研究、设计、规格或拆票 | B/C | 用对应的 `research` / `grill-with-docs` / `to-spec` / `to-tickets`；停在约定产物 |
| 多票或尚未收敛的完整实施请求 | C | 先收敛需求与依赖；G-tickets 验收完整票图后，只派 **一个** 长程 `implement-spec` worker |
| 外部 issue/PR、冲突或术语治理 | B/C | 走仓库的 triage、冲突处理或领域建模流程 |

雾重到形不成稳定需求时，可用 `wayfinder` 产出地图与决策票；先读目标仓库的寻路约定，不要发明标签。
若改动会推翻已有 ADR 或计划决策，先定夺该决策。完整实施请求通常走
`grill-with-docs → to-spec → to-tickets → implement-spec`；已有有效 spec 或票时从对应阶段进入。
已定案的单票仍走 B 通道；只有完整票图才用 `implement-spec`。只要设计就在设计产物 PR 合并后收口；
开放 PR 例外只认「明确要求不合并」（判据见 §0），要求开 PR 不等于该例外。

若 §4.1 只读探索发现多票、方案分叉或跨模块 seam，重新判定通道并重申模式声明。
范围本身不清时按 §5 请人定夺；绝不把讨论请求转成实施授权。

## 2. 角色边界：coordinator 规划与验收，worker 编辑与提交

- coordinator 做只读探索、拆任务、派活、消息处理、应答、验收，以及执行已授权的 PR 合并。
- 长程票图下，嵌套 implementer 是顶层 worker 的子代理。coordinator 只与顶层 worker 通信，
  不进入任何嵌套 workspace，并视顶层 worker 对嵌套分支、合并与清理负责。
- 项目文件的增删改、格式化、恢复、冲突解决、stage、commit、push、PR 正文一律由 worker 在该票
  workspace 内完成（含治理文档、票状态与 Answer、一行修复）。
  **coordinator 不得在 worker 的 workspace 内编辑或提交，也不得用脚本或其他 agent 绕过。**
- coordinator 可在仓库外写任务 spec、通信台账、证据与报告；`/tmp` 放过程产物，
  `~/.paseo-auto/` 放持久审计。项目内落盘是 worker 的活。
- 每次写之前核对谁在写、写到哪。项目文件 / index / 分支内容会变 ⇒ 派 worker。
  验收缓存与产物放临时验收目录，绝不更新用户主工作副本。
- **Paseo 默认把 agent 放进调用者的工作区**；本 skill 覆盖这条默认：实施票必须先建独立
  worktree workspace 再建 agent（§4.3）。coordinator 不把 worker 开在自己的工作区里。
- coordinator 可建隔离验收 workspace、fetch、跑检查并合并 PR；每次合并后按 §6.5.1
  **拉取已合并的主分支**——这是同步已验收工作，不是实施。只有干净的主工作副本才可
  `git pull --ff-only`；不 reset、不自动 stash、不切换用户当前分支。
- 漏改、格式化噪声、缺 commit/PR 或合并冲突：列证据打回 worker。worker 失联时按
  [恢复参考](references/agent-recovery.md) 确认状态并恢复或替换；coordinator 不接管实施。
- `detach`（把子代理变成独立顶层 agent）是用户在 subagents 里的手动动作，coordinator 不调用。

## 3. 轻量实施

方案已定、影响面可圈定的单票走 B 通道：一个独立 worktree、短 spec、与风险相称的验证。
修 bug 要有能在旧代码复现、在新代码通过的回归证据。纯文案、样式或配置用适用检查与可观察结果验收，
不强制制造红绿测试。项目文件改动默认提交 PR 并自动合并。

双轴 review 可对可圈定的小改动省略（理由写入 spec 与 Answer）；跨票、共享接口或影响面不明时
按 G-impl 选更宽验证。文档/规划票走自身门禁。任务小不改变角色边界：已授权实施仍由 worker
在独立 worktree 编辑。

## 4. 派活（B / C 通道）

### 4.0 派活前 preflight

按 [派活前检查](references/dispatch-preflight.md) 逐项打勾，未全绿不 dispatch；三条机械判据是
实施票 spec 里的 `测试档：` 行、`code-review` 字样，以及每个基线数字的 base commit 核对。
worker 回报完成之后、宣称门禁通过之前，跑该文件的收尾 / 格式化噪声检查。

### 4.1 只读探索

先在 main 上把写 spec 需要的事实读齐（最多并行读取三项）。
**探索的终点是 spec，不是动手**——「我可以直接改这一行」是派活信号，不是免派活许可。

### 4.2 选择 worker 配置

派活前读 [派活闭环](references/dispatch-loop.md) 的 profile 物化一节：把所选 profile 的
`provider`、`model`、`modeId`、`thinkingOptionId`、`featureValues` 物化进 `create_agent`
的 `provider` 与 `settings`；缺项省略，不要凭记忆补。没有 profile 时先 `inspect_provider`，
只设置它返回过的 feature ID。无法确定 provider 时停止并报告，不猜模型名。

### 4.3 ★ 硬覆盖：一个任务一个独立 worktree workspace

Paseo 的 agent-scoped `create_agent` 默认落在**你当前的工作区**；直接这样派实施票会把
worker 放进 main。**paseo-auto 覆盖这条默认：每个任务先建 worktree workspace，再在其中建 agent。**

```text
create_workspace({
  isolation: "worktree",
  mode: "branch-off",
  path: <目标 repo 绝对路径>,
  branchName: <票 slug>,
  baseBranch: "<本轮默认 base，通常 origin/main>",
  worktreeSlug: <票 slug>,
  title: <票标题>
})
create_agent({
  title: <票标题>,
  provider: <profile → provider/model>,
  workspaceId: <上一步的 workspaceId>,
  initialPrompt: <§4.4 的 spec>,
  notifyOnFinish: true,
  labels: { "ticket": <票 slug>, "run": <run id> },
  settings: { modeId, thinkingOptionId, features }
})
```

- **不许省略 `workspaceId`**；也不许复用 coordinator 自己的工作区或另一个票的 workspace。
- `branchName` 与 `worktreeSlug` 用同一个票 slug；`baseBranch` 显式写 §0 解析出的本轮默认 base
  （通常是 `origin/main`），不要写裸 `main`——裸名会优先本地 main，可能不是想要的基线。
- `notifyOnFinish: true` 必须显式写出。缺省值在 agent-scoped 调用里虽然为 true，但显式写能让
  回执里的 guidance 可核对，也避免后续改默认值时静默失效。
- 会话 cwd 不是目标 repo 时，`create_workspace.path` 写绝对路径。Paseo 在 daemon 所在机器解析它。
- 长程 worker 用同样的参数，`branchName` 用 `<feature>-integration`；它自己为 implementer
  建嵌套 workspace，无法隔离时降级为串行，见 [长程票图](references/long-horizon-tickets.md)。
- 用 CLI 派活只在没有 MCP 时降级使用；CLI 不武装完成通知，必须按
  [通知与等待](references/notifications-and-waiting.md) 的有界档运行。

### 4.3.1 派活后确认 turn 开始

`create_agent` 返回 `status` 与 `guidance`。`guidance` 出现
「You will get notified when the created agent finishes…」说明通知已武装；若它退回
「Observe completion using get_agent_status…」则通知**没有**武装，按通知参考的有界档处理。

`status: running` 表示 turn 已接受，但首次工具调用是否真的执行，用 `get_agent_status`
再确认一次；立即 `idle` 且没有 assistant 输出时，读 `get_agent_activity` 判断是
「刚创建还没起跑」还是「起跑即失败」，不要盲等。具体判据见
[agent 恢复](references/agent-recovery.md)。

### 4.4 spec 契约

按 [spec 契约](references/spec-contract.md) 模板写 spec；每一项都必需，包括行为规则、前置 skill
绝对路径、票型与门禁行、实施票的 `测试档：` 行（窄/宽；窄档写明为何影响面可圈定）、
「本票不跑」行。worker 只看得到 spec，漏写就不会做。

### 4.5 完成通知就是通信闭环

Paseo 的 supervised worker 通过 `notifyOnFinish` 把「完成 / 出错 / 需要权限 / 被关闭」
送回 coordinator。**终态通知**（finished / errored / was closed / was canceled）只触发一次；
**权限通知不是终态**——`respond_to_permission` 不改变武装状态，应答权限后仍会收到该 turn 的
终态通知，因此不要为「重新武装」补发消息。**`send_agent_prompt` 默认会重新武装**，所以 worker
提问后你答一次，就等于装回了下一次等待。派活前读
[通知与等待](references/notifications-and-waiting.md)，记住这条纪律：

- 通知到达前不要轮询 `list_agents` / `get_agent_status`；去做其他已授权工作。
- 收到通知后读完 `<agent-response>`（被截断时用 `get_agent_activity`），按 §5 分类处理。
- 通知没来但 agent 已 idle：读 `get_agent_activity` 与 workspace 状态继续验收，不空等丢失的通知。
- 没有 MCP 通知能力时，保持 turn 有界等待（单次 ≤60 秒），并明确记录无法自动唤醒的入口。

## 5. 应答协议：决策问人，细节代答

worker（grill / wayfinder / prototype 等）的每个提问，先分类再决定谁来答——流程不因提问停摆，
但「不问人」不是默认值。worker 用结束回合的方式提问：最后一条消息以
`[[PASEO-ASK]]` 开头、`[[/PASEO-ASK]]` 结尾（见 [spec 契约](references/spec-contract.md)）。

- **决策类**（交付物形态 / 用户可观察行为、方案分叉、scope 边界，或 escalation 五类：
  凭证、第三方账号、付费、人工审批、不可逆 live 数据操作）：附上倾向请人定夺。
  worker 的 `recommended:` 只是参考——任何提问都不允许不经分类直接把推荐当答案。
- **细节类**（命名、目录位置、实现手法、测试写法、库内 API 用法）：coordinator 代答，
  依据项目上下文 / ADR / spec / 用户原话。
- 已授权项目改动的 PR 合并属于 §6 的执行步骤，不是需要重新请示的产品决策。

分类判据、问人方式与记录细节见 [应答协议](references/reply-protocol.md)。
回复 worker 用 `send_agent_prompt`；回答本身会重新武装完成通知。

## 6. 门禁验收

coordinator 自行核验可观察结果与证据，失败就列明缺项打回。按票型选门禁，具体见
[门禁验收](references/gate-acceptance.md)。该文件同时覆盖 G-impl 逐条判据、G-merge 的组合规则、
§6.5 合并执行与 §6.5.1 本地主分支同步，以及 agent / workspace 生命周期与打回协议。
长程集成 PR 还要用真实 diff 核对 Merge Danger 的门：单向门绝不自动合并，拿不准就按单向门处理。

## 7. 落盘、实施与收口

每轮以 §0 声明的工作范围为准。完整实施请求在需求尚不明确时依次走
`grill-with-docs → to-spec → to-tickets → implement-spec`；已有清楚 spec 或已开票时从对应阶段进入。
只要设计、规格或票据的请求就在该阶段产物的 PR 合并后收口，不擅自进入实施。
用户明确要求保留开放 PR、不要合并时按该例外收口（判据见 §0）。

- 设计票按 G-docs 或 G-wayfinder 验收。若本轮包含 to-spec / to-tickets，继续落盘并核对 tracker；
  否则报告记录后续入口，不把未授权阶段标成缺陷。
- 完整票图只派一个长程 worker；它拥有 frontier 与并发。逐票回退（一票一个 worker，默认 3 个）
  只用于降级运行，并记入台账。集成 PR 验收一次，不逐票验收。
- 逐票 TDD 与证据是 worker 的契约；最终集成 PR 是 coordinator 的门禁。同一字段或接口跨调用点
  改动时，Answer 枚举每个位置及处置。
- 术语和票据写法优先遵循仓库现有约定。

收口报告写在 repo 外持久目录，应可独立理解。记录：本轮请求与交付终点、实际产物及其
commit/PR/合并状态、关键验收结果与证据位置、人定和代答的决策、未完成项、worker 生命周期清点。
项目改动列逐 PR 合并 SHA、本地同步结果及最终主分支 HEAD；未能合并时写明原因。
台账建议放在 `~/.paseo-auto/runs/<run-id>/ledger.md`，报告放同目录 `report.md`。

## 8. 规划依赖初始化（按需）

只有本轮确实要使用 `grill-with-docs`、`to-spec`、`to-tickets` 或 `triage`，
且它们需要的仓库配置缺失时，才检查该仓库的规划初始化要求。
先复用仓库已有的 issue tracker 与 domain docs 配置。初始化若会新增治理文件、标签或 PR，
须确认这些属于用户请求的规划范围。真正需要时由 worker 在独立 worktree 落盘，coordinator 验收。

## 9. 失败与上报纪律

Paseo daemon 不可用、MCP 派活失败、`create_agent` 回执异常、权限请求、通知丢失、熔断触发时，
按 [失败与上报](references/failure-and-reporting.md) 处置，不要临时发挥。那里每一条的共同形状是：
先取证再决定、报告精确错误、绝不无条件重派。流程错误（不是产品 bug）还要触发只读 retro；
候选单经人类选定后才由 worker 落地，见 [长程票图](references/long-horizon-tickets.md) §6。
