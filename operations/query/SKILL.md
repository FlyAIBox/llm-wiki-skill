---
name: query
description: Answer wiki questions with traceable evidence.
license: MIT
metadata:
  hermes:
    tags: [wiki, query, evidence]
    category: research
    related_skills: [llm-wiki]
---

# Query Skill

Answer ordinary questions from the selected wiki and preserve useful new synthesis.
State when saved evidence is insufficient or contested.

## When to Use
The user asks what the wiki knows, requests a comparison, or searches its knowledge.

## Prerequisites
Read the vault purpose, schema and index. Map available capabilities through the
[shared skill](../../SKILL.md); Hermes offers `read_file`, `search_files` and `terminal`.

## How to Run
Use `../../scripts/wiki_tool.py` with the [helper API](../../references/helper-api.md).
Run `search` with the user's topic and helpful alternate phrasings.

## Quick Reference
Retrieve → read → follow links → assess evidence → answer → optionally save synthesis.

## Procedure
1. Identify the question and relevant scope. The user may expand scope through dialogue;
   purpose is a relevance guide rather than a reason to refuse their request.
2. Run local BM25 search. Expand synonyms and split complex questions when useful.
   Use `include_raw: true` when knowledge pages lack sufficient detail. Keep raw evidence
   and established claims distinct. Inspect the index and graph for vocabulary mismatches.
3. Read matched pages and neighboring topics, then relevant originals or reading copies.
   Judge semantic relevance after reading; keyword rank is not answer confidence.
4. Answer with clickable paths or unambiguous wikilinks and source references. Identify
   uncertainty and disagreements. Do not fill evidence gaps with unsaved model knowledge;
   if outside information would help, describe that distinction or research when authorized.
5. Save only a substantive, reusable comparison, decision analysis or new synthesis.
   Ordinary lookups need no new page. Take a checkpoint before edits, cite contributing
   knowledge and original sources, update the index and append the query action to the log.
   When maintenance/writeback is authorized, track significant unanswered questions using
   `question` with `open` or `needs_writeback`. Mark `answered` only with an existing saved
   answer page. Do not record ordinary lookups or imply a decision question has been answered
   merely because its supporting sources have been imported.
6. Run `sync` after writeback and review differences using [cognition](../../references/cognition.md).
   Read-only queries do not commit sync state or create knowledge pages.

## Pitfalls
Local retrieval plus agent reasoning is not exhaustive vector search. A zero-hit search
does not establish absence of knowledge. A source's opinion is not the user's belief.

## Verification
Check that citations support the actual answer, acknowledge contradictory evidence,
and verify any saved synthesis is useful beyond repeating a source paragraph.
