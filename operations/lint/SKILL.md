---
name: lint
description: Audit wiki structure, evidence and knowledge health.
license: MIT
metadata:
  hermes:
    tags: [wiki, lint, evidence]
    category: research
    related_skills: [llm-wiki]
---

# Lint Skill

Audit structural integrity and the quality of saved knowledge. Distinguish computed
findings from semantic conclusions that require reading and judgment.

## When to Use
The user asks about wiki health, statistics, broken links, missing pages or stale claims.

## Prerequisites
Read purpose and schema; use the host's file and execution tools. In Hermes use
`read_file`, `search_files`, `terminal` and `patch` as appropriate.

## How to Run
Use `../../scripts/wiki_tool.py` with `status`, `graph` or `sync` in preview mode.
See the [helper API](../../references/helper-api.md).

## Quick Reference
Structural report → evidence audit → severity and suggested fixes → authorized repairs.

## Procedure
1. Use `status` for page/source counts, metadata, index, original hashes and pending
   reviews. Use `graph` for communities, hubs, zero-inbound orphans, wanted pages and
   ambiguous links. Keep requested JSON intact; explain findings in prose otherwise.
2. Inspect orphan and wanted pages in context. A wanted page may be an intentional
   research gap; an orphan may simply need a useful relationship. Do not fabricate links.
3. Read low-confidence or contested pages, high-impact claims and stale evidence.
   Check citations, taxonomy consistency, contradictions, outdated versions and scope.
   Structural status cannot prove factual correctness or semantic freshness.
4. Inspect pending cognition reviews and scheduling state. A local config saying
   active must be checked against the native scheduler before claiming a job is healthy.
5. If asked for repairs, apply reversible structural fixes supported by evidence,
   checkpoint before knowledge edits, rebuild index, log and track changes. Preserve
   disputed claims and record evidence; do not settle them merely to obtain a clean report.
6. For a pure audit, report issues without editing pages or committing tracking state.

## Pitfalls
Do not count indexes, raw views, images or archives as knowledge nodes. Never repair a
source hash mismatch by silently accepting a new hash; investigate the changed original.

## Verification
Recheck the affected findings after repairs. Keep unresolved semantic concerns visible
even when all structural checks pass. Follow [cognition](../../references/cognition.md)
for findings that belong in future briefings.
