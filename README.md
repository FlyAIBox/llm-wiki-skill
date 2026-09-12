# LLM Wiki Skill

English | [简体中文](README.zh-CN.md)

Maintain a local Markdown knowledge base through conversation with your AI agent. Capture sources, connect ideas, answer questions with evidence, and track how conclusions change over time.

The agent reads and synthesizes material; bundled Python helpers handle file operations, retrieval, link analysis, and change tracking. Your wiki stays in ordinary local files that you can open in Obsidian or any text editor.

## Features

- **Source preservation:** keep original files with SHA256 hashes, create Markdown reading copies, and synthesize knowledge across sources.
- **Evidence-backed answers:** search locally with BM25 and CJK tokenization, then let the agent read, follow links, and explain its findings.
- **Knowledge graph and health checks:** inspect linked communities, hubs, orphan pages, unresolved links, and structural issues.
- **Traceable updates:** preserve checkpoints and evidence snapshots before updating knowledge; track additions, modifications, and deletions.
- **Cognition reviews:** distinguish contradictions, revised conclusions, and differences in context, with evidence for both sides.
- **Briefings:** generate on-demand summaries of important changes, or connect them to the host agent's native scheduler and delivery channel.
- **Agent adaptation:** shared wiki rules and operation skills for hosts such as Codex, Claude Code, OpenClaw, and Hermes, subject to their available capabilities.

## Requirements

- An AI agent that can read and write local files and load skills.
- Python **3.11+** for the bundled helpers. Only the Python standard library is required.
- Host-provided extraction tools for webpages, PDFs, images, audio, and other non-text inputs. The helpers automatically read UTF-8 text only.
- For unattended briefings: a native scheduler, access to the local wiki, and an authorized delivery channel.

## Installation

Clone the repository:

```bash
git clone https://github.com/FlyAIBox/llm-wiki-skill.git llm-wiki
```

Install or copy the **entire `llm-wiki/` directory** using your agent's supported skill mechanism. Keep `SKILL.md`, `scripts/`, `templates/`, `references/`, and `operations/` together; copying only `SKILL.md` is insufficient. Confirm the active skill directory for your host and verify that the agent discovers `llm-wiki`.

See [agent installation and scheduling](references/agent-adapters.md) for host-specific considerations.

## Quick start

After loading the skill, tell your agent where to create the wiki and what it is for:

> Create a wiki at `~/my-wiki` for research on AI agent memory and knowledge management. Focus on retrieval, knowledge updates, and use across agents. Write in English for a product manager with a technical background.

The agent creates purpose and behavior documents, an initial index, local operation skills, and a portable helper runtime. Then use ordinary conversation:

| Task | Example request |
| --- | --- |
| Import material | “Add this folder to the wiki, preserve the originals, and connect it to existing concepts.” |
| Ask a question | “What do we know about long-term memory retrieval? Include evidence and uncertainties.” |
| Save an analysis | “Compare these three approaches and save the useful conclusions to the wiki.” |
| Inspect the graph | “Show the main topic groups, hub pages, orphan pages, and missing concepts.” |
| Check quality | “Check the wiki for structural issues, weak evidence, and outdated conclusions.” |
| Review changes | “Preview what has changed since the last recorded state.” |
| Read a briefing | “Give me a briefing on new contradictions and important conclusion updates.” |

To request scheduled briefings, specify the time, timezone, and destination. The agent must create and verify a real host scheduling job; generating a briefing file alone does not enable notifications. Unchanged items are suppressed where the host supports quiet delivery.

## Wiki layout

```text
my-wiki/
├── AGENTS.md / CLAUDE.md     # Host bootstrap instructions
├── wiki-purpose.md          # Goals, audience, scope, and priorities
├── wiki-schema.md           # Page, evidence, and linking conventions
├── wiki-agent.md            # Wiki-specific agent behavior
├── wiki-log.md              # Append-only operation log
├── wiki/
│   ├── index.md
│   ├── raw/                 # Rebuildable Markdown reading copies
│   ├── entities/
│   ├── concepts/
│   ├── comparisons/
│   ├── queries/
│   └── assets/
├── sources/                 # Preserved originals, organized by date and batch
├── .claude/skills/          # Vault-local operation skills
├── .agents/skills/
└── .llm-wiki/               # Configuration, snapshots, review state, and runtime
```

Move the entire wiki directory, including `.llm-wiki/`, to retain its state and portable runtime.

## How it works

Original evidence lives in `sources/`; `wiki/raw/` contains derived reading copies; knowledge pages combine and attribute findings across sources. Before substantive updates, checkpoints preserve earlier knowledge for comparison.

Search uses local lexical retrieval, followed by agent reading and synthesis. It is not a full-corpus vector search, so queries may need synonyms or broader exploration. Graph groups describe link structure; the agent interprets their meaning. A source claim or agent inference is not automatically a user belief.

The helper's `sync` operation tracks local file changes. It does not upload files or synchronize a remote service. Scheduled execution and message delivery depend on the host agent's capabilities.

## Documentation

- [Entry skill](SKILL.md) · [中文技能说明](SKILL.zh-CN.md)
- [Chinese usage manual](references/usage-manual.zh-CN.md)
- [Agent installation and native scheduling](references/agent-adapters.md)
- [Internal JSON helper API](references/helper-api.md)
- [Cognition lifecycle and briefing delivery](references/cognition.md)
- Operation playbooks: [ingest](operations/ingest/SKILL.md), [query](operations/query/SKILL.md), [lint](operations/lint/SKILL.md), [research](operations/research/SKILL.md), [briefing](operations/briefing/SKILL.md)

## Acknowledgments

The directory and operation organization draws on [jackwener/llm-wiki](https://github.com/jackwener/llm-wiki). The continuously compiled knowledge-base approach is inspired by [Andrej Karpathy's LLM Wiki pattern](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f).
