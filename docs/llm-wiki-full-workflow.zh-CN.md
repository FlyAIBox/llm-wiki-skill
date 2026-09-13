# LLM Wiki 全流程演示：DeepSeek Harness 本地资料

> 记录日期：2026-09-13（Asia/Shanghai）。原始资料：`/Users/fly/Documents/DeepSeek Harness`；知识库：`/Users/fly/Documents/DeepSeek Harness Wiki`。本文区分「已在该库验证」「只读预览」与「操作流程示例」。[SCNet 风格 PPT][deck] 是这份文档的讲解版。

## 一页看懂：能力与当前状态

| 阶段 | 用户场景 | 本次证据状态 |
|---|---|---|
| 安装 | 让当前 Agent 识别完整技能 | 已验证入口目录、Python 3.11.15 和库内五个操作技能；安装预检无待写文件 |
| 初始化 | 明确主题、范围、目录和维护规则 | 已存在并检查；没有重新初始化或覆盖旧库 |
| 保存资料 | 保留不可变原件和可重建阅读副本 | 已验证 138 份原件与阅读副本的去向，0 原件漂移 |
| 建知识网络 | 提炼实体、概念、方法、比较与有证据的关系 | 已有 467 篇知识页、1,134 条有向 Wiki 链接；质量仍须分层复核 |
| 审核 | 判断来源是否被处理、页面主张是否可信 | 来源去向完整；370 篇候选页、79 篇主题提要及 1 个待审语义批次仍未完成深审 |
| 增量添加 | 新文档改变旧结论时保留前后证据 | 本文给出可执行流程；本次没有收到新的用户资料，未向正式库导入新原件 |
| 检索与检查 | 带来源问答、关系探索、变化与健康检查 | 已做真实检索、图分析、状态及同步只读预览 |
| 简报与通知 | 有新的重要认知时提醒，没有则静默 | 空简报已验证；计划可生成，但未获接收目标授权，未建任务、未发消息 |

技能的 Python 辅助脚本负责文件、哈希、检索、图和状态；Agent 负责读原文、解释关系、判断冲突与写知识。数字展示的是**已保存的可追溯结构**，不是「DeepSeek Harness 本体已运行验证」或「所有主张均已复核」。

## 1. 安装入口技能

面向普通用户，可以直接说：

> 从 `FlyAIBox/llm-wiki-skill` 安装完整的 `llm-wiki`，放到当前 Agent 真正启用的技能目录，重新加载后确认能识别。

项目[中文 README][readme]也提供 Skills CLI 示例：

```sh
npx skills add FlyAIBox/llm-wiki-skill --skill llm-wiki -g -a codex
```

这条命令是**安装说明**，不是本次演示执行记录。安装时要保留整个 `llm-wiki/` 文件夹，包含 `scripts/`、`templates/`、`references/`、`operations/`。入口规范文件是 `SKILL.md`；**不需要也不要求 `SKILL.zh-CN.md`**。中文说明可以放在 README 或 references，不应把不存在的翻译文件当成安装门槛。

本机已验证 `/Users/fly/.codex/skills/llm-wiki/SKILL.md` 和完整资源目录存在，运行环境为 Python 3.11.15。正式库还带有 `.agents/skills/`、`.claude/skills/` 的 `ingest`、`query`、`lint`、`research`、`briefing` 五个操作技能。`skill_install` 的只读预检返回 `files_to_write: []`。**文件存在与 Agent 实际发现它们是两项检查**，部署到其他宿主时仍应在该宿主的新会话中确认。安装到别的 Agent 全局目录不是初始化自动授权的动作。

## 2. 初始化知识库

**应用场景：**「给本地 DeepSeek Harness 资料建一个中文技术 Wiki，用来理解架构、扩展机制、运行流程和工程取舍。」

Agent 应先确认**资料输入目录**与**Wiki 目标目录**不同，再把目的、读者、主题、核心问题、范围边界和优先级写进[本库目的文件][purpose]。初始化会创建 `wiki-schema.md`、`wiki-agent.md`、`wiki-log.md`、`wiki/index.md`、`sources/`、`wiki/raw/`、知识页目录、可移动的 `.llm-wiki/runtime/`，并准备宿主引导及五个库内操作技能。不能只凭某个目录名猜测目标库，也不能在已有库上强行重做初始化。

本次使用的是**已经初始化的正式库**。它的目的明确限制为用户给定的文件夹，不自动抓取网络，不执行资料中的命令，不把文档陈述当作运行中的产品事实。整个 Wiki 目录迁移时必须一并带上 `.llm-wiki/` 状态、原件与快照。

## 3. 资料入库与知识生成

**应用场景：**「把这整个文件夹整理进去，保留原件，同时生成可搜索的实体、概念和关联。」

完整摄取分三层：

1. **证据层**：清点文件、版本、格式及双语配对，`source_import` 将原件按内容哈希保存到 `sources/`，记录输入路径和 SHA-256；同内容重复导入会复用批次。
2. **阅读层**：UTF-8 文本生成 `wiki/raw/` 阅读副本；PDF、图片等由宿主实际提取后再形成派生副本。阅读副本可以重建，不能冒充不可变原件。
3. **知识层**：先按来源或长文分段列候选实体、概念、主张、限制、故障、方法和关系，再和旧页、别名去重；为值得独立检索的主题建立聚焦页面。关系要在正文说明**谁以何种关系连到谁，以及哪段来源支持**，不能只放一条 Wiki 链接。

本库[重建记录][rebuild-report]显示，138 份原件中有 133 份 Markdown、1 份 PDF、4 张 PNG；原件与输入文件夹按 SHA-256 核对无不符。现有知识页为 176 篇实体、229 篇概念、31 篇方法、19 篇发现、5 篇比较、6 篇问题和 1 篇概览，共 467 篇。图有 1,134 条有向链接。它已远超「给每份资料写一篇摘要」，但页面/边数量本身不证明语义穷尽。

## 4. 审核：来源去向、页面主张和待审变化

**应用场景：**「哪些资料还没处理？重要结论能否追到原文？」

审核有三个不同层级：

| 层级 | 检查方式 | 目前结果及边界 |
|---|---|---|
| 来源去向 | `coverage` 查直接引用、不建页理由、阅读副本、原件哈希 | 138 份中 137 份被知识页直接引用，1 份导航/跳转资料有具体不建页理由；0 未覆盖、0 缺阅读副本、0 原件漂移。只证明原件被交代 |
| 主张级审核 | 阅读页面的 `sources`、章节/页码/短引文，和原件逐条对照 | 370 篇 `provisional-source-matched` 的来源字节已匹配但主张未逐条复核；79 篇 `source-dossier-needs-deeper-analysis` 仅保存原文线索，需要继续拆分 |
| 新旧语义审核 | `review_list` 给出前后检查点，Agent 对比旧/新主张 | 目前 1 个待审批次涉及 457 页。待审不等于已发现 457 个冲突，也不能为使状态变绿而直接标完成 |

典型审核示范是[权限与安全控制面][permission]: 它把审批、沙箱、权限预设、文件新鲜度策略和凭据分开，并追到[审批][approval-source]与[沙箱][sandbox-source]的原文段落。结论是「审批一次允许不自动放宽文件沙箱」，仍需按真实 profile 与运行版本核验执行效果。审阅应优先处理高影响页面和长目录，而不是按页数凑进度。

## 5. 添加新内容与更新旧知识

**应用场景：**「我有一份新的 DSH 设计文档；加入 Wiki，告诉我它是否改变已有结论。」

这一步需要**真实的新资料**。本轮用户没有提供新文档，所以没有向正式库导入新的原件。以下是实际操作时应遵守的顺序：

1. `checkpoint` 固定更新前知识页与引用，搜索现有实体、概念、别名及邻居。
2. `source_import` 保存新原件；有 PDF/图片时，用实际提取文字创建 `raw_view`，保留页码、截图上下文和不可读取的部分。
3. 列出有证据的候选清单，决定更新旧页、建立新页、合并同义项或明确暂缓；不要为了凑数量建页。
4. 对新旧说法按版本、时间、条件和证据分类：真实矛盾、结论更新、语境不同，或仅仅是改写措辞。保留不能决断的双方。
5. 更新 `wiki/index.md`、追加 `wiki-log.md`、运行 `sync` 保存变化；逐批语义审核后才 `review_complete`。再查 `coverage`、`status`、原件哈希及代表性链接。

本库已有一次可追溯的历史增量例子：[操作日志][wiki-log]记录四张提供方设置截图的文字转录，以及 Loader `disabled: !!js` 事故语境的澄清。截图原件没有改动；[插件组合页][plugin-composition]把事故发生时的行为与后续防护说明分开，明确表示**资料不足以确定精确代码版本和变更点**。这说明更新知识不等于无条件覆盖旧说法。

## 6. 带证据的问答、图导航和知识缺口

**应用场景 A：**「人工审批后，是否就能写工作区外？」本地 `search` 对 467 篇知识页做 BM25 召回，Agent 阅读[权限比较页][permission]及保存的原文后回答：不能由 `allowed-once` 推出沙箱已经放宽。检索排序不是答案置信度。

**应用场景 B：**「AgentCBS 与 CubeSandbox 怎样配合？」从[AgentCBS][agentcbs]能沿链接到 CubeSandbox、腾讯云 Agent Runtime 和 Brain/Hands 解耦，再回到[厂商文章原件][agentcbs-source]。页面把存储、执行环境职责分开，同时把性能和成本写为**厂商主张**，未冒充独立测量。

**应用场景 C：**「Loader 到底计算不计算 `disabled: !!js`？」[插件组合页][plugin-composition]结合事故复盘与入门文档指出事故前后叙述的语境差异；具体版本变更点缺证据。问答可以指向缺口，外部研究需另行明确授权。

`graph` 目前报告 467 节点、1,134 条边、49 个算法社区、0 未解析链接、0 歧义链接、114 个零入链页面。边来自显式 Wiki 链接，**不是自动标注谓词的知识图谱**。零入链可提示导航检查，但不自动证明页面无价值。

## 7. 本地变化、健康检查与修复边界

**应用场景：**「先看看是否有人修改了知识库，再决定要不要处理。」

本次 `sync` 只读预览返回 `added: []`、`modified: []`、`deleted: []`、`unchanged: 744`。`status` 的结构 `issues: []`、`signals: []`；`coverage.traceability_complete: true`。这些结果只证明结构、哈希和来源去向当前正常，不能替代页面事实核对、软件运行验收或新版本时效检查。

只有用户要求修复时才修改页面。修复前读来源并保存 checkpoint；对断链要核对目标名称和关系，不能为消除警告虚构链接；对原件哈希漂移不能直接接受新哈希覆盖旧证据。修复后重建索引、记录变化并做语义复核。

## 8. 认知变化与简报

**应用场景：**「新资料真的推翻了旧建议，能提醒我吗？」

知识页的已归属主张才构成这个 Wiki 的旧认知基线；一份新来源自身的观点不是用户个人信念。记录前要读更新前 checkpoint 和新原文，引用双方确切文字，并说明是 `conflict`、`update` 还是 `context_difference`、适用条件、影响和待用户判断的问题。脚本能验证引文是否存在，**语义判断仍由 Agent 承担**。

之后 `digest_prepare` 生成预览；「已生成」「已投递」「已读」是三个不同事件。仅在宿主实际送达且拿到可核对的回执后，才 `digest_ack`。用户说「已读」「保留争议」「稍后提醒」「接受新观点」时，反馈要绑定具体认知项；接受观点若要改知识页，仍需更新页面、留存旧证据并重新审核。

**本库当前实测：** `cognition_list` 为空；对 `demo-only` 做简报只读预览得到 `empty: true, notify: false`。因此没有可投递的新增认知。上面的 457 页待审批次不能未经审阅就推送为“认知冲突”。

## 9. 定时通知的授权与实际运行

**应用场景：**「每个工作日北京时间 09:00 把新增认知发到我选定的渠道。」

这句话要由用户**明确提出并指定接收位置**。技能先 `schedule_plan` 生成提案，再检查宿主是否有原生调度器、授权渠道、本地文件访问、空更新静默、送达确认能力。创建或更新真正的宿主任务成功后，才把其 job ID 写入本地绑定并称之为 active；以后暂停、改时段或停用要同时调整宿主任务和本地记录。仅有 TOML 配置不证明任务在跑。

本次只对 `demo-only` 做了**无写入计划预览**：工作日 09:00、`Asia/Shanghai` 时区得到 `state: planned`，且列明还需要调度器、授权投递渠道、无变化静默和送达确认。**没有创建后台任务、没有绑定 job ID、没有发送任何消息。** 将演示时间误当订阅授权会产生不受欢迎的通知。

## 10. 可以现场演示的提问顺序

1. 「列出当前已加载的 llm-wiki 操作技能，确认入口安装完整。」
2. 「读这个 Wiki 的目的与范围，说明原始资料和知识页保存在哪里。」
3. 「抽查 AgentCBS：展示实体页、相关概念、厂商原文及尚未验证的主张。」
4. 「审批放行是否等于沙箱放行？给我原文依据。」
5. 「统计未覆盖来源、断链、零入链页面和待审内容，先只读报告。」
6. 「预览从上次记录以来的本地变动，不提交状态。」
7. 「预览认知简报；为空就保持安静。」
8. 待用户提供新资料时：「保存原件，更新相关知识页，比较旧结论，完成有证据的审阅。」
9. 待用户明确授权时：「按指定时区、时间和接收渠道配置通知，验证宿主任务与送达回执。」

## 11. 验收清单与当前仍未完成的事项

| 检查项 | 当前结论 |
|---|---|
| 安装入口 | 完整 `llm-wiki/` 可用；`SKILL.md` 是入口；无需 `SKILL.zh-CN.md` |
| 初始化 | 已有专用 Wiki，根规则与库内技能存在；没有覆盖旧库 |
| 原始资料 | 138 份均有去向，0 原件漂移，0 缺阅读副本 |
| 检索/图 | 可从问答追到原件；0 断链、0 歧义链接 |
| 内容质量 | 370 候选页、79 主题提要和一个 457 页待审批次仍需人工语义复核 |
| 增量新源 | 本轮未收到新文件，因此未实测新的正式库来源导入及完整写回 |
| 简报 | 无新认知时 `notify: false` 已预览；有真实认知项时的实际投递尚未演示 |
| 定时通知 | 仅生成 planned 预览；未配置、未激活、未送达 |

后续最有价值的实际测试是：用户提供一份新版本的 DSH 文档，选一条已有明确旧主张的主题，做完整的「保存原件—更新页面—前后证据审阅—简报草稿」闭环；只有用户指定接收渠道和时段后，再验收原生投递。原始资料中的命令与外链均按资料处理，本次没有执行 DeepSeek Harness 软件或外部链接。

## 维护者复现命令

普通使用只需自然语言。以下 JSON 是内部辅助接口；运行前应确认知识库路径，命令本身不自动访问网络：

```sh
printf '%s' '{"op":"skill_list"}' | python3 scripts/wiki_tool.py
printf '%s' '{"op":"skill_install","root":"/Users/fly/Documents/DeepSeek Harness Wiki","dry_run":true}' | python3 scripts/wiki_tool.py
printf '%s' '{"op":"coverage","root":"/Users/fly/Documents/DeepSeek Harness Wiki"}' | python3 scripts/wiki_tool.py
printf '%s' '{"op":"search","root":"/Users/fly/Documents/DeepSeek Harness Wiki","query":"审批 沙箱 权限 边界","limit":5}' | python3 scripts/wiki_tool.py
printf '%s' '{"op":"sync","root":"/Users/fly/Documents/DeepSeek Harness Wiki","dry_run":true}' | python3 scripts/wiki_tool.py
printf '%s' '{"op":"review_list","root":"/Users/fly/Documents/DeepSeek Harness Wiki"}' | python3 scripts/wiki_tool.py
printf '%s' '{"op":"digest_prepare","root":"/Users/fly/Documents/DeepSeek Harness Wiki","target":"demo-only","dry_run":true}' | python3 scripts/wiki_tool.py
```

更多后初始化案例见[六个应用场景的实测记录][scenarios]；更详细的接口与使用边界见[中文手册][manual]、[摄取流程][ingest-playbook]与[认知生命周期][cognition].

[readme]: </Users/fly/code/llm-wiki-skill/README.zh-CN.md>
[deck]: </Users/fly/code/llm-wiki-skill/docs/llm-wiki-full-workflow-scnet.pptx>
[purpose]: </Users/fly/Documents/DeepSeek Harness Wiki/wiki-purpose.md>
[rebuild-report]: </Users/fly/Documents/DeepSeek Harness Wiki/REBUILD-REPORT.md>
[permission]: </Users/fly/Documents/DeepSeek Harness Wiki/wiki/comparisons/permission-and-safety-planes.md>
[approval-source]: </Users/fly/Documents/DeepSeek Harness Wiki/sources/2026-09-12/781536b84a27871e90570627/offical docs/subsystems/approval.zh.md>
[sandbox-source]: </Users/fly/Documents/DeepSeek Harness Wiki/sources/2026-09-12/781536b84a27871e90570627/offical docs/subsystems/sandbox.zh.md>
[agentcbs]: </Users/fly/Documents/DeepSeek Harness Wiki/wiki/entities/agentcbs.md>
[agentcbs-source]: </Users/fly/Documents/DeepSeek Harness Wiki/sources/2026-09-12/781536b84a27871e90570627/article/基于 DeepSeek Harness 构建生产可用的 Agent 服务，需要怎样的 Agent Infra？.md>
[wiki-log]: </Users/fly/Documents/DeepSeek Harness Wiki/wiki-log.md>
[plugin-composition]: </Users/fly/Documents/DeepSeek Harness Wiki/wiki/concepts/plugin-composition.md>
[scenarios]: </Users/fly/code/llm-wiki-skill/docs/deepseek-harness-post-init-scenarios.zh-CN.md>
[manual]: </Users/fly/code/llm-wiki-skill/references/usage-manual.zh-CN.md>
[ingest-playbook]: </Users/fly/code/llm-wiki-skill/references/semantic-ingest.md>
[cognition]: </Users/fly/code/llm-wiki-skill/references/cognition.md>
