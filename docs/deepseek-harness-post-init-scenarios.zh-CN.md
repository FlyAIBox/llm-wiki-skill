# DeepSeek Harness Wiki：初始化后的应用场景演示

> 实测日期：2026-09-13（Asia/Shanghai）。原始资料在 `/Users/fly/Documents/DeepSeek Harness`，已建知识库在 `/Users/fly/Documents/DeepSeek Harness Wiki`。本次用最新版 `llm-wiki` 的本地运行时做只读演示；没有运行 DeepSeek Harness、改写知识页、发送简报或创建定时任务。

这份文档从「遇到什么问题」出发，而不是逐个展示内部命令。证据链接指向此电脑上的 Wiki 页面及其保存的原件；搬到其他电脑后需替换路径。

## 1. 故障排查：审批通过，为什么命令仍可能被沙箱拦下？

**用户可以问：**「一次工具调用得到人工批准，是否就能写工作区外的文件？」

**现场演示：** 搜索「审批 沙箱 权限 边界」扫描了 467 篇知识页，首位命中[权限与安全的不同控制面][permission-comparison]。继续读该页引用的[审批原文][approval-source]和[沙箱原文][sandbox-source]，得到的回答是：**不能据此推断可以写入**。`allowed-once` 只授权被询问的那一次操作；沙箱的 `read-only` / `workspace-write` 文件效果限制仍由另一层执行。反过来，放宽沙箱也不会自动得到审批授权。权限预设只是把两个独立设置组合为 UI 选项，本身不是执行器。

**可信边界：** 这是对保存的官方文档契约的归纳；具体 profile 的装配和正在运行的版本没有在本次演示中验证。搜索结果由本地 BM25 排序，相关性与结论仍由 Agent 阅读原文后判断。

## 2. 关系探索：从 AgentCBS 找到它与其他概念的分工

**用户可以问：**「AgentCBS、CubeSandbox 和 Brain/Hands 解耦是什么关系？」

**现场演示：** 搜索首先定位到[AgentCBS 实体页][agentcbs]、[CubeSandbox 实体页][cubesandbox]与[Brain/Hands 解耦概念页][brain-hands]；关系图显示 `AgentCBS → CubeSandbox`、`AgentCBS → 腾讯云 Agent Runtime`、`AgentCBS → Brain/Hands 解耦` 三条直接 Wiki 链接。回到[厂商文章原件的“关键底座”和“AgentCBS 存储”段落][agentcbs-source]核对：文中把前者定位为工作现场的保存、恢复、复制底座，把 CubeSandbox 定位为执行环境的隔离、弹性生命周期与复制底座。这让「实体—概念—来源」可以来回导航，而不只是得到一段摘要。

**可信边界：** 页面明确把性能、成本和产品效果标为厂商主张，并未把文章转成独立实测事实。`graph` 的边是知识页里的有向 `[[Wiki 链接]]`，并非带有「依赖」「提供」「反驳」谓词的自动语义图；关系含义仍须读页面和原件。

## 3. 实施任务：想扩展一个工具，从哪里开始？

**用户可以问：**「我要给 DSH 加一个可替换的模型可见工具，应该按什么顺序读和做？」

**现场演示：** 搜索「如何添加一个工具 defineTool」找到了单篇[“开发一个工具”教程提要][tool-tutorial]；顺着链接阅读跨八份原始文档整合的[“从插件到可替换能力的开发路径”][capability-path]，可以形成如下任务路径：

1. 先建立最小插件、`apply`、`cordis.yml` 和配置校验；
2. 确实需要替换实现时，再拆 Service Definition、Provider、Consumer；
3. 设计工具 schema、`execute`、返回值，并检查执行前后的 guard；
4. 涉及新包或 Host/Client 边界时，再接入 workspace 包和 Remote API；
5. 用真实 Host/Client 入口、失败路径与卸载清理验收。

这体现了 Wiki 的**跨文档任务导航**能力。它不是一份已经编译、可直接复制运行的实现；原文中的源码路径位于本次资料文件夹之外，本次没有验证这些代码。

## 4. 版本歧义：资料看起来互相矛盾时怎么办？

**用户可以问：**「Loader 到底会不会计算 `disabled: !!js ...`？」

**现场演示：** 搜索时同时纳入知识页和原始阅读副本，命中[插件组合与配置层][plugin-composition]及[事故复盘 0002 原件][postmortem-0002]。复盘的“根因”描述事故发生时 Loader 只插值插件 `config`，`disabled` 表达式被当作 truthy 对象；同一复盘的修复说明和[《Cordis 入门》][cordis-primer]又描述挂载决策时会插值 `disabled`。Wiki 没有把它们强行压成一个无条件规则，而是按事故前后语境解释，并留下「**具体代码版本及变更点仍未知**」的边界。

这展示的是**证据分层与保留未知**，不是声称已经复现事故或验证了当前 Loader。

## 5. 维护检查：这个库能信到什么程度？

**用户可以问：**「知识库建好了，是否每份来源、每条关系都已核实？」

**现场演示：** `status`、`coverage`、`graph` 与 `review_list` 给出以下可复核快照；解释必须连同[重建报告][rebuild-report]一起看。

| 维度 | 本次实测 | 该数字说明什么、不能说明什么 |
|---|---:|---|
| 知识页 | 467（实体 176、概念 229、方法 31、发现 19、比较 5、问题 6、概览 1） | 可检索的页面规模，不等于逐条主张已核实 |
| 原件去向 | 138 份；137 份被直接引用，1 份有理由记录为不建页 | `traceability_complete: true`；0 未覆盖、0 缺阅读副本、0 原件漂移，不等于概念已穷尽 |
| 知识链接 | 467 节点、1,134 条有向链接、49 个算法社区 | 0 未解析链接、0 歧义链接；114 个零入链页仍值得审查，但零入链不自动等于错误 |
| 结构检查 | `issues: []`、`signals: []` | 只覆盖结构/规则信号，不证明资料事实正确或版本新鲜 |
| 内容复核 | 370 篇 `provisional-source-matched`，79 篇 `source-dossier-needs-deeper-analysis` | 来源已匹配或已保存章节线索，仍需逐条核对与深入拆分 |
| 语义审阅 | 1 个待审批次，涉及 457 页 | 批次未被伪装成“审阅完成”；应按证据与优先级分批处理 |

实际维护动作应先选高影响的未审页面或零入链主题，读原件后补充或纠错；不能为了让图指标好看而制造链接。此演示只做审计，没有自动修复。

## 6. 日常更新：没有新变化时保持安静

**用户可以问：**「资料或知识页有变化吗？今天要发认知简报吗？」

**现场演示：** `sync` 的只读预览报告 `added: []`、`modified: []`、`deleted: []`、`unchanged: 744`。`cognition_list` 当前为空；对仅用于测试的目标 `demo-only` 做 `digest_prepare` 预览，得到 `empty: true, notify: false`。因此现在**没有可发送的认知更新**，不会生成“今天没新闻”的例行通知。上一节的待审批次也不能直接当作已证实冲突发送。

未来若有真实新增证据，流程才是：更新前保存检查点 → 纳入来源与知识页 → `sync` 记录变化 → 对比旧/新证据 → 只为有依据的冲突、更新或语境差异记录认知项 → 预览简报 → 经授权渠道实际送达后再确认回执。此次没有制造示例冲突、创建日程或发送消息。

## 可以直接复用的自然语言提问

- 「审批放行是否代表沙箱放行？请给原始文档证据。」
- 「从 AgentCBS 出发，列出相关实体和概念，并区分厂商主张与实测。」
- 「我要加一个模型可见工具，给我按依赖排序的阅读与验收路径。」
- 「`disabled: !!js` 的两种说法对应什么语境？哪些版本信息仍未知？」
- 「检查当前 Wiki 的来源覆盖、断链、孤页和待审内容，不要自动修改。」
- 「预览有无值得推送的认知变化；没有就不要发通知。」

## 复现入口与未演示范围

在本仓库根目录运行以下**只读**请求即可复核关键结果（需 Python 3.11+；库路径以本机为准）：

```sh
printf '%s' '{"op":"search","root":"/Users/fly/Documents/DeepSeek Harness Wiki","query":"审批 沙箱 权限 边界","limit":5}' | python3 scripts/wiki_tool.py
printf '%s' '{"op":"status","root":"/Users/fly/Documents/DeepSeek Harness Wiki"}' | python3 scripts/wiki_tool.py | jq '{knowledge_pages:.result.knowledge_pages,coverage:.result.coverage,issues:.result.issues}'
printf '%s' '{"op":"sync","root":"/Users/fly/Documents/DeepSeek Harness Wiki","dry_run":true}' | python3 scripts/wiki_tool.py
printf '%s' '{"op":"digest_prepare","root":"/Users/fly/Documents/DeepSeek Harness Wiki","target":"demo-only","dry_run":true}' | python3 scripts/wiki_tool.py
```

本次没有执行新的来源摄取、认知项写入、语义审阅完成、定时任务创建、外部消息投递，也没有验证 DeepSeek Harness 本体行为。以后可以分别在真实新增资料、真实观点更新和明确的通知配置下验收这些写入/投递能力；不能从此处的只读预览推断它们已经端到端运行。

[permission-comparison]: </Users/fly/Documents/DeepSeek Harness Wiki/wiki/comparisons/permission-and-safety-planes.md>
[approval-source]: </Users/fly/Documents/DeepSeek Harness Wiki/sources/2026-09-12/781536b84a27871e90570627/offical docs/subsystems/approval.zh.md:21>
[sandbox-source]: </Users/fly/Documents/DeepSeek Harness Wiki/sources/2026-09-12/781536b84a27871e90570627/offical docs/subsystems/sandbox.zh.md:9>
[agentcbs]: </Users/fly/Documents/DeepSeek Harness Wiki/wiki/entities/agentcbs.md>
[cubesandbox]: </Users/fly/Documents/DeepSeek Harness Wiki/wiki/entities/cubesandbox.md>
[brain-hands]: </Users/fly/Documents/DeepSeek Harness Wiki/wiki/concepts/brain-hands-解耦.md>
[agentcbs-source]: </Users/fly/Documents/DeepSeek Harness Wiki/sources/2026-09-12/781536b84a27871e90570627/article/基于 DeepSeek Harness 构建生产可用的 Agent 服务，需要怎样的 Agent Infra？.md:94>
[tool-tutorial]: </Users/fly/Documents/DeepSeek Harness Wiki/wiki/methods/user-develop-basic-tool.md>
[capability-path]: </Users/fly/Documents/DeepSeek Harness Wiki/wiki/methods/develop-capability-path.md>
[plugin-composition]: </Users/fly/Documents/DeepSeek Harness Wiki/wiki/concepts/plugin-composition.md>
[postmortem-0002]: </Users/fly/Documents/DeepSeek Harness Wiki/sources/2026-09-12/781536b84a27871e90570627/offical docs/postmortem/0002-js-expression-disabled-filesystem-tools.zh.md>
[cordis-primer]: </Users/fly/Documents/DeepSeek Harness Wiki/sources/2026-09-12/781536b84a27871e90570627/offical docs/cordis-primer.zh.md>
[rebuild-report]: </Users/fly/Documents/DeepSeek Harness Wiki/REBUILD-REPORT.md>
