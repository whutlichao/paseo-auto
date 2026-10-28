# 派活前检查：tick sheet 与收尾检查

**什么时候读**：每次派活之前（逐项打勾），以及 worker 报 `[[PASEO-DONE]]` 之后、
宣称门禁通过之前的收尾阶段。

## 实时 worker 配置查找

只在 Run 即将派活时查询，且只用 Paseo 自己的工具面：

```text
MCP：list_profiles → 读 notes → 选中 → 物化 provider/model/mode/thinking/features
CLI：paseo provider ls --json；paseo provider models <provider> --json
```

不要从旧会话、本 skill 文本、eval 夹具或过期日志推断 provider 与模型。
用户点名的 profile 优先于你的匹配结果；没有合适 profile 时走
`inspect_provider` 回退，并在报告里写明。

## 4.0 派活前 tick sheet（逐项打勾，未全绿不 dispatch）

唯一作用是让「我是不是漏了哪条」变成一次勾选，而不是靠记性——长 spec 写到后半段时，
前面已经确认过的约束最容易悄悄掉队。括号里是它的归属小节。

- [ ] **Paseo 控制面活着**：MCP `create_workspace` / `create_agent` 可用，或
      `paseo status --json` 报告 daemon 正常。起不来 → 按 §9 报告精确错误并停，
      不换可执行文件、不猜命令。
- [ ] **worker 配置已物化**（§4.2）：profile 的 provider/model/mode/thinking/features
      已转成 `create_agent` 参数；没有合适 profile 时已记录回退与理由。
- [ ] **通道已判定，且若探索过就已复核**（§1 末尾「探索后必须重判」）。
- [ ] **票型已判定，且 spec 里写了票型行**（§4.4）：研究、设计、规格、票据拆分或实施。
      派活前依据 Target、Change 和预期文件判断；workspace 尚未创建，不运行针对它的 `git diff`。
      文档票只写适用的文档门禁，不把源码测试或双轴源码 review 写成验收项。完成后再以真实 diff 复核票型。
- [ ] **spec 五要素齐**：Target / Change / Constraints / Ownership / Observable acceptance，
      且开头是 BEHAVIOR RULE 与前置 skill 绝对路径（§4.4）。
- [ ] **workspace/agent 参数对**（§4.3）：`create_workspace` 用 `isolation: "worktree"`、
      `mode: "branch-off"`、显式 `path`、`branchName` = `worktreeSlug` = 票 slug、
      `baseBranch` 与本轮解析出的默认 base 一致（§0，通常 `origin/main`）；
      `create_agent` **显式带 `workspaceId`** 与 `notifyOnFinish: true`。
      长程票图用 `<feature>-integration`，只派一个 worker。
- [ ] **长程票图确实就绪**：一个集成 PR、`implement-spec` 作为前置 skill、票图完整、tracker 可达；
      worker 的首次报告证明它能建嵌套 workspace/agent，或记录串行降级（见长程票图参考）。
- [ ] **main 铁律自检真的过了一遍**（§2）：本轮不会在 main 工作区修改项目文件或创建提交；
      仅 §6.5.1 已合并成果的快进同步可更新主分支。
- [ ] **票据位置已按 tracker 类型明确**（§4.4）：远端 tracker 正本在 issue（Answer 是 issue
      评论或 PR 描述），本地票正本在 worker 可见路径；本轮无票时已明确记录「无票」，
      证据写 PR 描述与 §7 报告。coordinator 在 main 上只读验收。
- [ ] **门禁已点名且可判定**：本阶段该过哪几道（G-docs / G-spec / G-tickets / G-impl /
      G-merge），每条的证据形式都能按 §6 机械判定。实施票多勾两笔：
      ① 按 §6 G-impl 第 1 条选定测试档（窄/宽），并**已写进 spec 的 `测试档：` 行**；
      若选「窄」，同一行里已写明为何影响面可圈定，并给出能照着直接跑的选择器；
      ② 若本票要省双轴 review，已按 §3 的可数判据确认并写明理由。
      **机械判据（测试档）**：`grep -c '测试档：' <spec>` 得 0 就不许 dispatch（实施票）。
      **机械判定法（review）**：实施票 spec 的 `Observable acceptance` 里必须**逐字出现
      `code-review`**（连同「双轴 / Standards + Spec」字样），除非按 §3 省掉。长程票图写
      「integration branch 上的一次双轴 code-review」加逐票 TDD，不得再要求逐票双轴 review。
      跑一句 `grep -c 'code-review' <spec>`，得 0 就是没写、不许 dispatch。
- [ ] **spec 里的每个基线数字都核过 base commit**：凡引用「改动前基线：Test Files X /
      Tests Y」这类实测数字，必须确认那条日志来自**与本票 workspace 相同的 base commit**。
      不同就**不要用**那个数字，或明写「基线来自 `<commit>`，与本票 base 差 N 个 commit，
      仅作量级参考」。
- [ ] **本仓库若确有自动格式化风险，已写入针对性的预防与安全恢复要求**（§4.4）。
- [ ] **派活后已确认 turn 真的开始**（§4.3.1），且回执 `guidance` 证明通知已武装。
      没武装时已改用有界档并在台账记录。

打回与熔断不在这张表里——照 §6 的「打回协议」执行（带具体缺项清单；同一票连续 2 次不过
同一门禁则停下问人）。

## 4.0.1 收尾时必查：格式化噪声

worker 报 `[[PASEO-DONE]]` 之后、宣称门禁通过之前，**先跑这三条**（§6 的 G-impl 第 0 步）。
用 `create_workspace` 返回的 `cwd` 只读执行，不进入编辑：

```bash
cd <任务 workspace cwd>
git status --porcelain
git diff --numstat | awk '{a+=$1; d+=$2} END {print "worktree 未提交:", a, "增", d, "删"}'
```

- 未提交为空 → 干净，继续验收。
- 有未提交且总量是**万行级** → 整份重排噪声，读
  `references/reformat-noise-recovery.md` 恢复。
- 有未提交且量正常 → 问 worker 为什么有未提交改动，不要默认收下。

**判据一句话**：`git diff --numstat` 出现四位数以上，就去看行宽是否被压到 80 附近——
编辑器插件与仓库 formatter 在写文件时会按自己的默认行宽重排**整个文件**，而仓库没有
formatter 配置时这一动作不受约束，很多仓库源码本是宽行风格。

**恢复由 worker 执行，coordinator 只存证并打回。** 先备份完整 diff、未跟踪文件与 index，
再逐文件确认哪些内容是真实工作。`git diff --cached` 非空也不能证明工作区其余改动全是噪声；
确认并留底之前不得 checkout。完整恢复顺序见参考文件。

**治本**：只有确认当前 worker 确实加载了会重排的插件、且仓库存在自动重排风险时，才按
[恢复参考](reformat-noise-recovery.md) 配置本地忽略的覆盖项；其他环境不引入该配置。
