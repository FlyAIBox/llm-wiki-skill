[English](README.md) | **中文**

# LLM Wiki

一个把文档、链接和对话变成个人知识库的 Agent Skill。让 Agent 帮你整理学到的内容、带着来源回答问题，并在新证据改变旧结论时告诉你。

适用于支持 Agent Skills 的 AI Agent，包括 Codex、Claude Code、OpenClaw、Hermes 等。知识保存在本地 Markdown 文件中，可以用 Obsidian 或任意文本编辑器打开。

## 你能得到什么

- **持续积累的知识库**：把零散资料整理成互相关联的概念、实体、比较和问答。
- **有来源的回答**：询问自己已经知道什么，同时看到结论背后的依据。
- **知识变化的历史**：保留原始资料和旧结论，方便回看认识是如何变化的。
- **新旧证据的比较**：看清哪些结论更新了、哪些来源存在分歧、还有什么问题没有答案。
- **认知简报**：随时查看重要更新，也可以让 Agent 定时推送。
- **知识库健康检查**：找出缺失链接、孤立页面、薄弱证据和可能过时的结论。

## 安装

### 让 Agent 帮你安装

把下面这段话发给你的 Agent：

```text
帮我从 https://github.com/FlyAIBox/llm-wiki-skill 安装 llm-wiki 技能，
放到你当前使用的技能目录。保留完整仓库，包括 scripts、templates、references
和 operations，并确认技能已加载。
```

### 使用 Skills CLI 安装

已安装 Node.js/npm 时，运行：

```bash
npx skills add FlyAIBox/llm-wiki-skill --skill llm-wiki
```

默认安装到当前项目。出现交互提示时按提示选择，也可以直接指定 Agent。需要在不同项目中使用时，选择对应的全局安装命令：

```bash
# Codex
npx skills add FlyAIBox/llm-wiki-skill --skill llm-wiki -g -a codex

# Claude Code
npx skills add FlyAIBox/llm-wiki-skill --skill llm-wiki -g -a claude-code

# OpenClaw
npx skills add FlyAIBox/llm-wiki-skill --skill llm-wiki -g -a openclaw

# Hermes
npx skills add FlyAIBox/llm-wiki-skill --skill llm-wiki -g -a hermes-agent
```

其他 Agent 和安装选项见 [Skills CLI 文档](https://github.com/vercel-labs/skills)。

### 手动安装

也可以把完整仓库克隆到 Agent 的技能目录。例如，Claude Code：

```bash
mkdir -p ~/.claude/skills
git clone https://github.com/FlyAIBox/llm-wiki-skill.git ~/.claude/skills/llm-wiki
```

使用其他 Agent 时，将目标路径替换为其当前启用的技能目录。保留整个文件夹，安装后开启新会话或重新加载技能，再让 Agent 使用 `llm-wiki`。

## 快速开始

1. 用上面任意一种方式安装技能。
2. 告诉 Agent 知识库放在哪里，以及你想积累什么知识。
3. 加入第一份文档、链接或对话。

例如：

> 用 llm-wiki 在 `~/my-wiki` 建立一个知识库，积累 AI Agent 记忆相关研究，重点关注检索、知识更新和产品设计。内容用中文。

Agent 会根据对话明确建库目的、关注主题和语言，必要时补问缺失信息，然后创建初始结构，带你加入资料。无需手动编辑配置文件。

## 日常使用

直接告诉 Agent 你想做什么：

| 你想做什么 | 可以这样说 |
| --- | --- |
| 整理资料 | “把这个文件夹整理进知识库，保留原件，更新相关页面。” |
| 回顾知识 | “我们对长期记忆检索有哪些结论？附上来源和不确定的地方。” |
| 比较方案 | “比较这三种方案，把值得保留的结论写下来。” |
| 审视新证据 | “这篇文章会改变我们已有的哪些判断？” |
| 探索关联 | “看看主要有哪些主题、关键页面和待补充的概念。” |
| 检查质量 | “找出薄弱证据、失效链接和可能过时的结论。” |
| 阅读简报 | “总结自上次审查以来的重要认知更新。” |

## 调整偏好

通过对话修改知识库的关注方向和整理方式：

- “把 Agent 评测方法也纳入关注范围。”
- “以后的新页面用英文写。”
- “多关注对产品设计的实际影响。”
- “这个分歧先保留双方观点，等有更多证据再判断。”

如果想直接编辑文件，`wiki-purpose.md` 定义目标和范围，`wiki-schema.md` 定义页面约定，`wiki-agent.md` 定义 Agent 如何维护这个知识库。

## 定时简报

告诉 Agent 时间、时区和接收位置：

> 每个工作日北京时间早上九点，在这里给我推送新增认知冲突和重要结论更新的简报。

定时推送使用 Agent 自带的自动化和通知工具，运行环境需要能访问本地知识库。也可以随时要求“现在给我一份简报”，无需配置定时任务。

技能分别记录简报的已生成、已投递和已读状态，避免重复推送没有变化的内容。无更新时能否保持静默取决于宿主的通知能力。需要调整或停止推送时，直接告诉 Agent。

## 环境要求

- 支持 Agent Skills，能够读写本地文件并运行 Python 的 Agent。
- **Python 3.11+**。无需 Python 第三方依赖、数据库或向量服务。
- 处理网页、PDF、图片或音频时，需要 Agent 提供相应的提取工具。
- 定时投递需要 Agent 的原生调度器和已授权的通知渠道。

只有选择 Skills CLI 安装方式时才需要 Node.js/npm。

## 工作方式

1. **保存资料**：原件放入 `sources/`，阅读副本放入 `wiki/raw/`。
2. **连接知识**：Agent 综合不同来源，生成互相链接、注明依据的知识页。
3. **回答问题**：本地关键词检索找到相关页面，Agent 阅读后组织答案。
4. **审查变化**：通过快照保留旧知识，Agent 将其与新证据比较，说明结论如何变化。

知识库中，`wiki/` 保存知识页，`sources/` 保存原件，`.llm-wiki/` 保存状态和快照。迁移时保留整个目录。

## 数据与隐私

知识库文件和辅助脚本的状态保存在本地，Python 辅助脚本不发起网络请求。交给 Agent 阅读的内容可能按该 Agent 的设置发送给模型服务商；网页提取和通知使用你配置的工具。

技能只整理你要求保存的资料，不会自动收集无关对话或导入其他 Agent 的记忆。

## 文档

- [入口技能](SKILL.md)
- [中文使用手册](references/usage-manual.zh-CN.md)
- [Agent 安装与调度细节](references/agent-adapters.md)
- [内部辅助接口](references/helper-api.md)
- [认知审查与简报生命周期](references/cognition.md)

## 致谢

知识持续编译的思路源于 [Andrej Karpathy 的 LLM Wiki 模式](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f)。
