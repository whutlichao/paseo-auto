# paseo-auto

**[简体中文](README.md) · [English](README.en.md)**

[![License: MIT](https://img.shields.io/badge/license-MIT-green)](./LICENSE)

给 [Paseo](https://paseo.sh) 的 Agent Skill：把「派活 → 监督 → 门禁验收 → 自动合并」跑成闭环。
仓库同时提供两版内容等价的 skill：`paseo-auto-zh`（简体中文）与 `paseo-auto`（英文）；
流程、门禁、references 文件名与评测场景一一对应。

派活容易，最后 20% 才难。这个 skill 写的是那 20%：worker 落在哪个 workspace、什么情况下合并、
什么情况下必须问人、通知丢了或 agent 崩了怎么恢复。

## 安装

```bash
# 简体中文
npx skills add whutlichao/paseo-auto --skill paseo-auto-zh

# English
npx skills add whutlichao/paseo-auto --skill paseo-auto
```

手动安装：把 `skills/paseo-auto-zh/` 或 `skills/paseo-auto/` 整个目录复制到
`~/.agents/skills/<同名目录>/`。

## 它覆盖什么

| 场景 | 行为 |
| --- | --- |
| 一张及以上票要实施 | 在独立 worktree 里建 supervised worker，spec 五要素 + 前置 skill 绝对路径 |
| 完整票图要长程实施 | 只派一个 `implement-spec` worker，集成 PR 收口 |
| 门禁验收与打回 | 按票型过 G-docs / G-spec / G-tickets / G-impl / G-merge；证据不齐就退回 |
| 双向门 PR | 门禁通过后自动合并并同步主分支；单向门或拿不准就交人 |
| 执行受阻 | daemon 起不来、MCP 报错、通知丢失、agent 崩溃：先取证、精确报告，不擅自重派 |
| 流程出错 | 按 retro 参考复盘，改流程而不是硬重试 |

触发与排除条件写在两版 `SKILL.md` 的 frontmatter 里：用户提到 Paseo 编排、worker 派活、
workspace/worktree 隔离、门禁验收、PR 自动合并或派活故障排查时使用；纯问答、只读审查、
或 Orca 侧编排不启动本 skill。

## 结构

```text
skills/
├── paseo-auto-zh/                # 简体中文版
│   ├── SKILL.md                  # 路由与核心约束（references 按条件读）
│   ├── references/               # 11 个按条件读取的参考文件
│   └── evals/evals.json          # 行为评测场景
└── paseo-auto/                   # 英文版，与中文版逐节对等
    ├── SKILL.md
    ├── references/               # 文件名与中文版完全一致
    └── evals/evals.json
```

两版 `references/` 下的文件同名同构：

```text
references/
├── dispatch-preflight.md      # 派活前 tick sheet / 收尾检查
├── dispatch-loop.md           # workspace / agent 参数、profile 物化、turn 确认
├── spec-contract.md           # 给 worker 写 spec 的模板与判据
├── reply-protocol.md          # 提问分类：决策问人、细节代答
├── gate-acceptance.md         # 门禁与合并执行
├── notifications-and-waiting.md
├── agent-recovery.md
├── long-horizon-tickets.md
├── gates-docs-planning.md
├── reformat-noise-recovery.md
└── failure-and-reporting.md
```

与 Orca 侧的 [`orchestra-auto`](https://github.com/whutlichao/orchestra-auto) 同源：同一套监督、
隔离、门禁与合并纪律，控制面换成 Paseo 的 MCP / CLI。

## 开发

```bash
python3 -m unittest discover -s tests -v
```

测试不需要网络、凭证或特定机器：遍历 `skills/*/SKILL.md`，校验 frontmatter、reference 可达性、
evals 可解析、无绝对家目录路径，并核对两版 skill 的 references 文件名与评测场景 id 一致、
英文版不含 CJK 字符。

## 说明

Paseo 是第三方产品，本仓库不是官方仓库，也不代表其背书。本仓库只包含本 skill 的中文与英文正文
及评测，不包含 Paseo 本体或其它 paseo-* skill。

## License

MIT
