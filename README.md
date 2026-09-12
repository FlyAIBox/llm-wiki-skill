**English** | [中文](README.zh-CN.md)

# LLM Wiki

An Agent Skill that turns your documents, links, and conversations into a growing personal knowledge base. Ask your agent to organize what you learn, answer with sources, and show you when new evidence changes an earlier conclusion.

Works with AI agents that support Agent Skills, including Codex, Claude Code, OpenClaw, and Hermes. Your knowledge lives in local Markdown files that you can open in Obsidian or any text editor.

## What You Get

- **An organized wiki:** turn scattered material into connected concepts, entities, comparisons, and answers.
- **Answers with sources:** ask what you already know about a topic and see the evidence behind each conclusion.
- **A history of your knowledge:** preserve original material and earlier conclusions as the wiki grows.
- **Reviews of conflicting evidence:** see what changed, where sources disagree, and which questions remain open.
- **Knowledge briefings:** get important updates on demand, or on a schedule through your agent.
- **A healthier knowledge base:** find missing links, disconnected pages, weak evidence, and outdated conclusions.

## Installation

### Let Your Agent Install It

Send this to your agent:

```text
Install the llm-wiki skill from https://github.com/FlyAIBox/llm-wiki-skill
into your active skills directory. Keep the complete repository, including
scripts, templates, references, and operations, and verify that the skill loads.
```

### Install with the Skills CLI

With Node.js/npm available, run:

```bash
npx skills add FlyAIBox/llm-wiki-skill --skill llm-wiki
```

This installs into the current project. Follow the installer prompts when shown, or choose your agent explicitly. For installation across projects, use one of these commands:

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

See the [Skills CLI documentation](https://github.com/vercel-labs/skills) for other agents and installation options.

### Manual Installation

You can also clone the complete repository into your agent's skills directory. For example, for Claude Code:

```bash
mkdir -p ~/.claude/skills
git clone https://github.com/FlyAIBox/llm-wiki-skill.git ~/.claude/skills/llm-wiki
```

For another agent, replace the destination with its active skills directory. Keep the entire folder together. Start a new agent session or reload skills, then ask it to use `llm-wiki`.

## Quick Start

1. Install the skill using one of the methods above.
2. Tell your agent where to create your wiki and what you want to learn.
3. Add your first document, link, or conversation.

For example:

> Use llm-wiki to create a knowledge base at `~/my-wiki` for my research on AI agent memory. Focus on retrieval, knowledge updates, and product design. Write in English.

Your agent uses the conversation to establish the wiki's purpose, topics, and language, asking for missing details when needed. It creates the initial structure and guides you through adding material. No configuration files to edit by hand.

## Everyday Use

Just tell your agent what you want:

| What you want | What to say |
| --- | --- |
| Add material | “Organize this folder into my wiki. Preserve the originals and update related pages.” |
| Recall knowledge | “What do we know about long-term memory retrieval? Include sources and uncertainties.” |
| Compare approaches | “Compare these three approaches and save the useful conclusions.” |
| Review new evidence | “Does this article change any of our existing conclusions?” |
| Explore connections | “Show the main themes, key pages, and concepts that still need work.” |
| Check quality | “Find weak evidence, broken links, and conclusions that may be outdated.” |
| Read a briefing | “Summarize the important knowledge updates since my last review.” |

## Changing Preferences

You can adjust the wiki through conversation:

- “Also include agent evaluation methods in the scope.”
- “Write new pages in Chinese.”
- “Focus on practical implications for product design.”
- “Keep both sides of this disagreement until we have more evidence.”

For direct editing, `wiki-purpose.md` defines your goals and scope, `wiki-schema.md` defines page conventions, and `wiki-agent.md` defines how the agent maintains this wiki.

## Scheduled Briefings

Tell your agent the time, timezone, and destination:

> Every weekday at 9 a.m. Asia/Shanghai, send me a briefing here on new contradictions and important conclusion updates.

Scheduling uses your agent's native automation and notification tools. It requires an execution environment that can access the local wiki. You can also ask for a briefing at any time without scheduling one.

The skill tracks prepared, delivered, and read states separately, and avoids repeating unchanged items. Quiet runs depend on the host's notification support. To change or stop a schedule, tell your agent.

## Requirements

- An agent that supports Agent Skills and can read/write local files and run Python.
- Python **3.11+**. No third-party Python packages, database, or vector service required.
- For webpages, PDFs, images, or audio: extraction tools provided by your agent.
- For scheduled delivery: the agent's native scheduler and an authorized notification channel.

Node.js/npm is only needed if you choose the Skills CLI installation method.

## How It Works

1. **Capture:** save original material in `sources/` and create readable copies in `wiki/raw/`.
2. **Connect:** the agent combines findings into linked knowledge pages with references to their sources.
3. **Answer:** local keyword search finds relevant pages; the agent reads them and synthesizes an answer.
4. **Review:** snapshots preserve earlier knowledge so the agent can compare it with new evidence and explain changes.

Your wiki contains `wiki/` for knowledge, `sources/` for originals, and `.llm-wiki/` for state and snapshots. Keep the whole directory together when moving it.

## Data and Privacy

Wiki files and helper state stay on your machine. The Python helpers do not make network requests. Content you ask your agent to read may be sent to its model provider under that agent's settings; web extraction and notifications use the tools you configure.

The skill captures material you ask it to save. It does not automatically collect unrelated conversations or import other agents' memory.

## Documentation

- [Entry skill](SKILL.md) · [中文技能说明](SKILL.zh-CN.md)
- [Chinese usage manual](references/usage-manual.zh-CN.md)
- [Agent installation and scheduling details](references/agent-adapters.md)
- [Internal helper API](references/helper-api.md)
- [Knowledge reviews and briefing lifecycle](references/cognition.md)

## Acknowledgments

Inspired by [Andrej Karpathy's LLM Wiki pattern](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f), with directory and operation organization drawing on [jackwener/llm-wiki](https://github.com/jackwener/llm-wiki).
