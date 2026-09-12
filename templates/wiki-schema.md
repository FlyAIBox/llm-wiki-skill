# Wiki Schema

## Page types

Knowledge: `entity`, `concept`, `comparison`, `query`. Reading copies: `raw`.
Keep each knowledge page focused on a topic. Merge repeated coverage. Split pages
when different topics or excessive length make evidence hard to follow.

## Paths and links

- Knowledge lives in `wiki/entities/`, `wiki/concepts/`, `wiki/comparisons/`, `wiki/queries/`.
- Use descriptive lowercase hyphenated filenames; Chinese names are also supported.
- Wiki links use full paths relative to `wiki/`, e.g. `[[concepts/agent-memory]]`.
  Display aliases and anchors: `[[concepts/agent-memory#Evidence|Memory]]`.
- `sources` frontmatter uses vault-root-relative paths, with the `sources/` or `wiki/`
  prefix. Claims cite excerpts, page numbers or headings in their body.
- Originals in `sources/` are immutable; extracted reading copies go in `wiki/raw/`.
- Open the whole vault root in Obsidian to browse originals and root documents too.

## Required frontmatter

Use single-line scalars and arrays with JSON-style double-quoted strings (valid YAML),
or two-space `-` list entries. Avoid nested mappings, anchors, custom tags and multiline
scalars; the dependency-free reader flags unsupported syntax rather than guessing.

```yaml
---
title: "Page title"
description: "One-line summary"
type: "concept"
tags: ["memory"]
sources: ["sources/2026-09-12/batch/document.md"]
created: "2026-09-12"
updated: "2026-09-12"
aliases: []
confidence: "medium"
contested: false
---
```

## Page body

Explain what is known, evidence, applicability (date/version/conditions), open questions
and related pages. Distinguish source claims, agent inferences and saved user judgments.
Synthesis may cite other knowledge pages, but citations must lead back to original evidence.

## Tags

Define a small domain vocabulary here during initialization and evolve it as needed.
Reconcile synonyms before adding tags. Agent lint checks domain taxonomy; the structural
helper verifies that tags are a list.

## Updates and cognition

Read the prior page and checkpoint before substantive edits. Preserve conflicting claims
and evidence. Record conflicts, updates or context differences with exact quotations.
An empty wiki has no previous user cognition: label cross-source disagreements as such.
Refresh `updated`, rebuild `wiki/index.md`, append `wiki-log.md`, and track local changes.
Review pending batches after synthesis; a sync commit alone is not semantic review.

## Archiving

On an archive request, move superseded pages to `wiki/_archive/`, update links and index,
preserve evidence and log the change. Never silently delete sources or snapshots.
