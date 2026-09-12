# LLM Wiki Skill

[English](README.md) | 简体中文

通过与 AI Agent 对话，维护本地 Markdown 知识库：保存资料、连接概念、基于证据回答问题，并持续追踪结论的变化。

Agent 负责阅读与综合，内置 Python 辅助脚本负责文件操作、检索、链接分析和变化追踪。知识库保存在普通本地文件中，可以用 Obsidian 或任意文本编辑器打开。

## 功能

- **保留来源**：保存原始文件及 SHA256 哈希，生成 Markdown 阅读副本，跨来源整理知识。
- **基于证据问答**：使用支持中日韩文本分词的本地 BM25 检索，再由 Agent 阅读页面、追踪链接并解释结论。
- **知识图谱与健康检查**：查看主题社群、中心页、孤立页、未解析链接和结构问题。
- **可追溯更新**：更新知识前保存检查点和证据快照，追踪文件新增、修改与删除。
- **认知审查**：区分真实矛盾、结论更新和适用条件差异，保留双方证据。
- **认知简报**：按需汇总重要变化，也可接入宿主 Agent 的原生定时任务和投递渠道。
- **跨 Agent 适配**：通过共享规则与操作技能适配 Codex、Claude Code、OpenClaw、Hermes 等宿主，具体能力取决于当前环境。

## 环境要求

- 能读写本地文件并加载技能的 AI Agent。
- **Python 3.11+**，辅助脚本仅使用标准库，无需安装 Python 第三方依赖。
- 网页、PDF、图片、音频等非文本资料需要宿主提供提取工具；辅助脚本只自动读取 UTF-8 文本。
- 无人值守简报需要原生调度器、本地知识库访问能力，以及已授权的投递渠道。

## 安装

克隆仓库：

```bash
git clone https://github.com/FlyAIBox/llm-wiki-skill.git llm-wiki
```

使用当前 Agent 支持的技能安装方式，安装或复制**完整的 `llm-wiki/` 目录**。保留 `SKILL.md`、`scripts/`、`templates/`、`references/` 和 `operations/`，只复制 `SKILL.md` 无法正常使用。请确认宿主当前启用的技能目录，并验证 Agent 已发现 `llm-wiki`。

各宿主的安装与调度注意事项见[跨 Agent 适配](references/agent-adapters.md)。

## 快速开始

加载技能后，直接告诉 Agent 建库位置和用途：

> 在 `~/my-wiki` 建立一个知识库，积累 AI Agent 的记忆与知识管理研究，帮助我做产品设计。主要关注检索、知识更新和跨 Agent 使用。内容用中文，面向有基本技术背景的产品负责人。

Agent 会生成目的与行为说明、初始索引、本地操作技能及可随知识库迁移的运行资源。之后用普通对话操作：

| 任务 | 示例 |
| --- | --- |
| 导入资料 | “把这个文件夹整理进知识库，保留原件，并连接到已有概念。” |
| 查询知识 | “知识库里有哪些关于长期记忆检索的结论？列出依据和不确定的地方。” |
| 保存分析 | “比较这三种方案，把值得长期保留的结论写回知识库。” |
| 查看图谱 | “看看知识网络有哪些主题群、中心页、孤立页和待补充的概念。” |
| 检查质量 | “检查知识库的结构问题、薄弱证据和可能过时的判断。” |
| 查看变化 | “先预览自上次记录以来改了什么。” |
| 阅读简报 | “给我一份新增认知冲突和重要结论更新的简报。” |

需要定时简报时，说明时间、时区和接收渠道。Agent 必须在宿主中创建并验证真实的定时任务；生成简报文件本身不会开启通知。在宿主支持静默投递的情况下，没有变化的内容不会重复通知。

## 知识库结构

```text
my-wiki/
├── AGENTS.md / CLAUDE.md     # 宿主启动引导
├── wiki-purpose.md          # 目标、读者、范围和优先级
├── wiki-schema.md           # 页面、证据与链接约定
├── wiki-agent.md            # 本知识库的 Agent 行为规则
├── wiki-log.md              # 只追加的操作日志
├── wiki/
│   ├── index.md
│   ├── raw/                 # 可重建的 Markdown 阅读副本
│   ├── entities/
│   ├── concepts/
│   ├── comparisons/
│   ├── queries/
│   └── assets/
├── sources/                 # 按日期和批次保存的原件
├── .claude/skills/          # 知识库本地操作技能
├── .agents/skills/
└── .llm-wiki/               # 配置、快照、审查状态与运行资源
```

迁移时请移动整个知识库目录，包括 `.llm-wiki/`，以保留操作状态与运行资源。

## 工作方式

`sources/` 保存原始证据，`wiki/raw/` 保存提取出的阅读副本，知识页综合多个来源并标注依据。实质更新前通过检查点保留旧知识，以便比较前后变化。

检索先在本地匹配关键词，再由 Agent 阅读和综合。它不是全库向量检索，必要时需要扩展同义词或扩大查找范围。图谱社群反映链接结构，其含义由 Agent 结合内容解释。来源的观点或 Agent 的推断不会自动视为用户信念。

辅助脚本的 `sync` 操作只记录本地文件变化，不上传文件，也不执行远程同步。定时运行与消息投递依赖宿主 Agent 提供的能力。

## 文档

- [英文入口技能](SKILL.md) · [中文技能说明](SKILL.zh-CN.md)
- [中文使用手册](references/usage-manual.zh-CN.md)
- [跨 Agent 安装与原生调度](references/agent-adapters.md)
- [内部 JSON 辅助接口](references/helper-api.md)
- [认知生命周期与简报投递](references/cognition.md)
- 操作流程：[摄取](operations/ingest/SKILL.md)、[问答](operations/query/SKILL.md)、[检查](operations/lint/SKILL.md)、[研究](operations/research/SKILL.md)、[简报](operations/briefing/SKILL.md)

## 致谢

目录与操作划分参考 [jackwener/llm-wiki](https://github.com/jackwener/llm-wiki)。知识持续编译的思路源于 [Andrej Karpathy 的 LLM Wiki 模式](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f)。
