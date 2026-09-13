# Corpus-level semantic ingestion

Use this playbook when the user asks to build a wiki from a folder, or to improve
the breadth of an existing wiki. It is a semantic workflow for the host agent, not
an LLM service inside the Python helper. The helper's source capture and raw views
alone are not a completed ingestion.

## Inventory before synthesis

Run `coverage` after capture. Group sources by topic, language pair, version and
format; inspect the whole folder before choosing batches. Keep a per-source working
list that can be resumed after interruption. A large corpus may be processed in
bounded batches, but every in-scope source needs a disposition. Do not silently
omit later files because the first batch already produced a plausible overview.

For each source (or each section of a long source), first analyze, then write:

1. Identify central and supporting named entities (people, organizations,
   packages, interfaces, services, files), concepts and mechanisms, claims and
   findings, procedures and decisions, constraints, failure modes, and open
   questions relevant to the wiki purpose. These are candidate categories, not
   quotas. Record exact source paths and section/page/line locators or short
   quotations for consequential candidates.
2. Map candidates to existing pages and aliases before creating pages. Preserve
   the exact subject, version, date and conditions of each claim. Distinguish
   source statements from agent inference. Note genuine contradictions and
   translation/version differences without automatically choosing a winner.
3. Identify relationships as triples: subject, meaningful predicate, object.
   Examples include `provides`, `depends on`, `configures`, `implements`,
   `contradicts`, `supersedes` and `fails under`. The predicate and its evidence
   belong in readable prose; a bare wikilink or shared tag does not establish
   the relationship. Label an unsupported but useful connection as a candidate,
   not a confirmed edge.

## Write a navigable knowledge network

Create or update one focused page per reusable entity, concept or comparison that
has enough evidence and independent retrieval value. Do not create pages for every
passing mention; do not collapse distinct subsystems, APIs or failure modes into
one broad page merely to keep the page count small. Treat a source summary or raw
view as evidence, not as a substitute for knowledge pages.

- Entity pages state identity, role, important interfaces or responsibilities,
  boundaries, and supported relationships. Concept pages explain definition,
  mechanism, applicability and limitations. Findings record source-scoped
  observations or incidents; methods capture reusable procedures. Use the vault's
  defined types, and add custom types only when they clarify a real distinction.
- Use canonical names, aliases and explicit disambiguation. Merge bilingual
  duplicates and repeated mentions; keep version-specific identities separate
  where conflation would change the claim. Check existing pages before every
  new filename.
- Put every contributing original source in the page's `sources` frontmatter.
  Cite the relevant section/page or a short exact excerpt near important claims.
  A page may cite several sources; one source may support several pages.
- Add `[[wikilinks]]` where the page explains a real relation. Say what the
  relation is and why it holds. Use reciprocal links only if both directions aid
  navigation. Shared source, tag, or co-occurrence may suggest a relation to
  inspect, but must not silently become a factual edge.

After a batch, compare its candidate list with the pages actually written:
central candidates must be represented, merged into an identified existing page,
or explicitly deferred with a reason. Search the resulting wiki for several
source-specific terms and traverse representative links; correct missing pages,
misattributed claims, duplicates and dangling targets before calling that batch
integrated. Run `index`, `sync` and semantic review after page edits.

## Coverage and completion

`coverage` reports which registered originals are cited by knowledge pages,
which have a justified `source_review` decision, which lack a reading copy, and
which remain unaccounted for. A file that adds no reusable knowledge can be
marked `no_new_knowledge` only after reading it and supplying a specific reason;
do not use this to hide unprocessed, failed or merely inconvenient sources.

For a full-folder request, do not report the knowledge build as complete while
`coverage.uncovered` or `coverage.missing_raw_views` is nonempty. If time, budget,
extractor capability or source ambiguity interrupts the work, report a partial
build with exact remaining paths and a resumable next batch. Even when
`traceability_complete` is true, inspect important dimensions and a sample of
low- and high-link pages against originals: coverage counts cannot establish
that the analysis found every meaningful concept or that any claim is true.
Never set an arbitrary entity/page/edge-count target to imitate another tool.
