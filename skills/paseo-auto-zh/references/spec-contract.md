# spec 契约

**什么时候读**：准备给 worker 写 spec 时，任何通道、任何票型。

worker 只看到 `create_agent.initialPrompt` 里的 spec，看不到本 skill。spec 必须自包含，
且把适用的行为规则与实际交付终点写进去。

## 4.4.1 五要素与固定首行

Guide 的 Task-spec contract 五要素必须齐：**Target / Change / Constraints / Ownership /
Observable acceptance**。外加第一条固定为：

```text
前置 skill：<绝对路径>——开工前完整读它，按其流程执行，不许跳过。
```

**这一行是其余 skills 的唯一入口。** 没有它，worker 就不会去读 grill-with-docs /
tdd / diagnosing-bugs / code-review，于是「不用其他 skills」的故障就复现了。路径写在 spec 里，
让 worker 自己读全文，不要由你转述。

**Answer 是什么**：票据的收尾记录。远端 tracker（如 GitHub issue）上，Answer 是该 issue 的
评论或 PR 描述，**正本在 issue**；本地票上，Answer 是该票文件的 `## Answer` 小节，正本在
worker 可见的文件路径。写 spec 时按 tracker 类型二选一，不要假设「正本在 worktree 内」。
本轮无票时省略 Status / Answer，证据写 PR 描述与 §7 报告。

## 4.4.2 实施票模板

```text
【BEHAVIOR RULE（原样遵守，不得转述或删减）】
1. 提问：不要使用 AskUserQuestion，也不要等消息。完成当前能做的部分后，结束回合，
   最后一条消息只输出：
   [[PASEO-ASK]]
   question: <要人定夺的具体问题>
   recommended: <你的推荐与一句理由>
   options: <其余选项的一句话代价>
   [[/PASEO-ASK]]
   coordinator 会通过 send_agent_prompt 回答，然后你继续同一张票。
2. 完成：无论项目文件是否有改动，结束回合时最后一条消息只输出：
   [[PASEO-DONE]]
   status: succeeded | failed
   summary: <三句：改了什么、发现了什么、遗留什么>
   pr: <PR URL 或 none>
   evidence: <测试/检查命令与结果，一行一条>
   files: <改动文件列表>
   [[/PASEO-DONE]]
   有项目文件改动时，先提交、推送并创建或更新 PR，`pr:` 填 URL；PR 号与 CI 读数一次写全
   （PR 创建后一笔提交回填，不为单项读数追加提交；文档-only 提交不追 CI，最终 CI 由
   coordinator 验收）。无项目文件改动时 `pr: none`，并在 summary 说明「无项目文件改动」。
   失败也必须输出；不要用普通总结代替。
3. 需要人类 / 凭证 / 第三方账号 / 付费 / 人工审批 / 不可逆 live 数据操作 → 用 [[PASEO-ASK]]
   原样上抛，不代办。
4. 描述设计时可用 codebase-design 词汇；源码、测试和报告中的既有术语遵循仓库语言。
5. 越出本 spec 授权范围 → [[PASEO-ASK]] 上抛，不擅自扩 scope。
6. 红证据在隔离副本或基线 worktree 上取得；任何还原或自动格式化前先保存并核对全部未提交工作。
   交付前检查 `git status` 与 diff；异常大 diff 先取证并按恢复参考逐文件处理。
   仅在确认仓库确有自动重排风险时，开工前按恢复参考配置本地忽略的 formatter 覆盖项。
7. 你只在自己的 workspace 内工作；不要切换或写入 coordinator 的主工作副本，也不要
   detach 自己或创建新的顶层 agent（长程 worker 除外，见其 spec）。

前置 skill：<绝对路径>——开工前完整读它，按其流程执行，不许跳过。
Target：<文件/模块>
Change：<要产出的具体结果>
Constraints：<不许碰的边界；术语用 codebase-design 词汇>
Ownership：<本票可编辑范围；票据正本位置按 tracker 类型（远端 issue 在 issue、本地票在 worker
  可见路径），有票时你负责 Status 流转并按上述落点追加 Answer；本轮无票时省略 Status/Answer，
  证据写 PR 描述与报告>
Observable acceptance：<适用的测试命令与可观察结果；修复类红→绿证据；需要时含 code-review 双轴。
  项目文件有改动时：解析并使用本机 pr skill 编写 PR body，推分支，以 --body-file 创建或更新 PR，
  PR 号及 body 路径按上述落点写入（与代码同一次推送完成，不为回填追加提交）；
  无论是否有项目文件改动，最后都输出 [[PASEO-DONE]]>
```

## 4.4.3 票型行

**紧随前置 skill 写出票型、门禁与测试档**：

```text
票型：研究票 | 设计票 | 规格票 | 票据拆分 | 实施票
门禁：<研究票=来源与结论核验 / 设计票=G-docs / 规格票=G-spec / 拆分=G-tickets / 实施票=G-impl>
测试档：窄（受影响测试 + 选择器）| 宽（全量）   ← 实施票必写；窄档须写明为何影响面可圈定
本票不跑：<列出不适用的源码门禁>                 ← 研究/设计/规格/拆分票必写；实施票按实际填写
```

**为什么这一行是硬要求**：worker 只会把 spec 里写的东西当交付面。spec 不写票型，它就只能去猜；
它手上唯一关于「门禁」的通用线索是仓库 `CONTRIBUTING.md` 的 `Keep it green`，
于是一张零源码改动的设计票会去跑全量测试。缺这一行的代价很具体：一段很长的等待 +
一次远超任何有用超时的全量 + 一例它自己缺二进制的假红。

同样地，不写「不跑」，「双轴 review」就会被当成所有票的必需品，而它审的是 diff——
设计票的 diff 是文档，Standards 轴只能去挑证据目录的毛病。

**测试档这一行同理**：窄/宽是 coordinator 在派活前就该做完的判断，但 worker 看不到这个判断。
不写测试档，它就退回「跑全量最安全」或自行挑几条测试；写了窄档却不写理由，它也无法判断
某条测试算不算「受影响」。窄档必须带一句「为什么影响面可圈定」，并给出能直接照着跑的
选择器（`node glob` 只是举例；Python 写 `python3 -m unittest tests.test_x`，不要让 worker 自己拼命令）。
测试档判断错了由 coordinator 打回时改判，不是 worker 现场改口径。

## 4.4.4 长程票图附加项

`前置 skill` 是 `implement-spec` 的绝对路径。另加：

```text
skill 解析：有 Skill tool 时用 `tdd` / `code-review`；没有就直接读它们的绝对路径，不许转述。
PR skill：<绝对路径>/pr/SKILL.md——用它写唯一的集成 PR 正文。
Tracker：<docs/agents/issue-tracker.md 或本地票目录绝对路径>。
Spec：<绝对路径或 issue URL>。
Tickets：<tracker 查询 / 本地目录；写明 frontier 与阻塞边>。
Integration branch：<名称>；base：<本轮默认 base，通常 origin/main>。
并发：最多 <N> 个 implementer；用户或仓库未另说时默认 3。
Paseo 派活：每个 implementer 用 create_workspace（isolation worktree，base 为 integration branch）
  建独立 workspace，再 create_agent 指定该 workspaceId、notifyOnFinish: true。
  首次报告必须证明你能这样做；不能证明就串行跑 implementer 并记录降级。
```

长程 worker 是**编排者**，不得自己实现票。它维护图和 frontier，为每张就绪票启动一个新鲜
implementer，通过 merger 步骤合入各自分支，跑最终 review 并开 PR。嵌套的决策类问题经顶层
worker 上抛；worker 不得替人类作答。逐票 TDD 加 integration branch 上的一次 `code-review`
是本路径的 review 模型，不要安排逐票双轴 review。

## 4.4.5 判据

派活前根据 Target / Change 与预期文件定票型；worker 完成后再用真实 diff 复核。
若真实改动越过票型边界，按 §5 升级范围问题，不靠一个路径正则自动改判。
