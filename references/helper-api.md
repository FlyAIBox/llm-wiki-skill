# Internal helper interface

Use a host execution tool (`terminal` in Hermes, its equivalent elsewhere) to run
the detected Python 3.11+ interpreter with `scripts/wiki_tool.py`. Pass one UTF-8 JSON
request file as its single argument, or the JSON object on stdin. Write JSON with the
host's file-writing tool; do not interpolate untrusted text into a shell command.
Paths in the examples are illustrative. A native Python runner may also call `execute`.

```text
python3 /absolute/path/to/llm-wiki/scripts/wiki_tool.py /absolute/path/request.json
```

Responses are `{ "ok": true, "result": ... }`. Errors are `{ "ok": false, "error": ... }`
with exit code 1. Agent/user interfaces should report a meaningful outcome, not expose
the JSON protocol as something the user has to learn. Helpers perform no network calls.

## Paths and concurrency

Supply `root` on all vault operations. Discovery may use `WIKI_PATH` or the nearest
ancestor config, but never a guessed vault. `init` requires an explicit root. Root,
source input and installer targets may be absolute native paths; page/evidence paths
are portable forward-slash paths relative to the vault root, without `..` or symlinks.
Read operations do not create files. All helper writes use a per-vault directory lock
and atomic replacements; agents must serialize their direct page edits as well.
After a crash, inspect the host before removing a stale `.llm-wiki/write.lock` directory.

## Initialization and sources

```json
{"op":"init","root":"/absolute/my-wiki","name":"Research","language":"zh-CN","purpose":"# Wiki Purpose\n\nThis wiki supports my research on agent memory.\n"}
```

Use the purpose template to produce an actual user-specific document. Empty purpose
is rejected. Initialization preserves existing bootstrap text and refuses an existing
knowledge/source layout. Reinitializing a configured vault is a no-op. Interrupted
partial initialization is reported; inspect/recover the partial directory rather than
silently replacing it. By default both requested operation-skill directories are populated.

```json
{"op":"source_import","root":"/absolute/my-wiki","source":"/absolute/staging/article.md","source_url":"https://example.org/article"}
```

`source` can be a file or folder. Hidden directory entries are omitted from folder
capture, symlinks are rejected, and the source folder must not contain the destination.
Each content-addressed batch retains relative filenames under `sources/YYYY-MM-DD/`.
Original SHA256 and actual input paths are recorded in `source-manifest.json`.
Text gets a derived Markdown view; binary/unknown files appear in `extraction_needed`.
Agent synthesis into knowledge pages is still required after this mechanical step.

For a full-folder build, follow the [semantic ingestion playbook](semantic-ingest.md)
and audit source disposition before claiming completion.

```json
{"op":"raw_view","root":"/absolute/my-wiki","source":"sources/2026-09-12/BATCH/report.pdf","text":"# Extracted text\n\nPage 3: actual source content..."}
```

Supply actual host-extracted text, not invented contents. Requires a registered,
unchanged source. Copies use names such as `report.pdf.md` to avoid format collisions.
Derived views may be rebuilt; originals are never overwritten.
`raw_view` records source and output hashes in `raw-manifest.json`. A legacy reading
copy has no verified extraction entry: inspect it and regenerate through `raw_view`
before using it in a new cognition record. Link repair does not certify a legacy extraction.

## Retrieval, graph and health

```json
{"op":"search","root":"/absolute/my-wiki","query":"agent memory","limit":10,"include_raw":false}
```

Returns `mode: local_bm25`, scanned count and ranked path/title/excerpt/source results.
`limit` is 1–100. The host agent performs semantic reading and reranking. CJK text
uses characters and adjacent pairs; English uses case-folded word tokens.
Titles, descriptions, aliases and bodies are indexed.

```json
{"op":"graph","root":"/absolute/my-wiki"}
```

Returns nodes, directed edges, communities, hubs, orphans, wanted pages and ambiguous
links. Excludes raw views, indexes, archives and assets. Recognizes full-path and
unambiguous title/basename/alias links, aliases after `|`, anchors after `#`, and
relative links. Ignores self-links, embedded images, escaped examples and fenced code.
`converged` reports whether label propagation settled before its iteration cap.
`edges` are navigation links. Optional `relations` retain explicit predicates, scope
and quoted evidence; they do not change navigation community calculations.

```json
{"op":"links","root":"/absolute/my-wiki"}
{"op":"links_repair","root":"/absolute/my-wiki","dry_run":true}
{"op":"links_repair","root":"/absolute/my-wiki","dry_run":false}
```

`links` separately audits ordinary Markdown links/reference definitions and Markdown
heading/HTML anchors under `wiki/`. It ignores code examples. `links_repair` previews by
default, then repairs reading-copy links to captured sources using original full paths
and unambiguous versions. Originals stay unchanged; pre-repair views are snapshotted.
Unimported files and ambiguous versions remain reported gaps. Do not infer complete
navigation from `graph.wanted` or `coverage.traceability_complete`.

```json
{"op":"status","root":"/absolute/my-wiki"}
```

Returns counts, metadata/source/index issues, immutable-source drift, content-review
signals, a coverage summary, graph, tracking changes, pending reviews and locally recorded schedules.
It does not verify live native jobs or the truth of claims. The agent performs those checks.

```json
{"op":"coverage","root":"/absolute/my-wiki"}
{"op":"source_review","root":"/absolute/my-wiki","source":"sources/2026-09-12/BATCH/navigation.md","outcome":"no_new_knowledge","reason":"Only a navigation list; the substantive pages are captured and cited separately."}
```

`coverage` is read-only. It lists registered originals cited directly in knowledge-page
`sources` fields, those with a reasoned no-page review, uncovered sources, per-folder
counts, missing
reading copies, and changed or missing originals. `status.coverage` gives their counts. A source review requires the
registered unchanged original and a specific explanation; it cannot replace evidence
for a substantive source. `traceability_complete` means every original is accounted
for and has a reading copy, not that every entity or relationship was discovered.
Review decisions live in `.llm-wiki/source-coverage.json` and are bound to source SHA256.

## Resumable work and typed relationships

```json
{"op":"source_progress","root":"/absolute/my-wiki"}
{"op":"source_progress","root":"/absolute/my-wiki","source":"sources/DATE/BATCH/paper.pdf","units":[{"id":"methods","locator":"PDF pp. 4–8","status":"partial","note":"Model extracted; parameter choices still need review.","pages":["wiki/methods/model.md"]}]}
{"op":"question","root":"/absolute/my-wiki"}
{"op":"question","root":"/absolute/my-wiki","question":"Which framework supports this research workflow?","status":"open","note":"Requested decision; needs evidence comparison."}
{"op":"question","root":"/absolute/my-wiki","id":"QUESTION_ID","status":"answered","note":"Saved evidence-backed comparison.","pages":["wiki/queries/framework-choice.md"]}
{"op":"relation","root":"/absolute/my-wiki","subject":"wiki/concepts/loader.md","predicate":"depends_on","object":"wiki/entities/service.md","scope":"Documented version 1","evidence":[{"path":"sources/DATE/BATCH/manual.md","quote":"The loader depends on the service."}]}
{"op":"relation","root":"/absolute/my-wiki"}
```

Without write fields, these are read-only. Progress units merge by stable id and bind
to source hashes. Status is `pending`, `partial`, `complete`, or `deferred`; completed
units require mapped existing pages or `no_new_knowledge: true` with a note. Legacy
sources lacking units remain `unplanned_sources`, regardless of file citation coverage.
Question status is `open`, `needs_writeback`, `answered`, or `deferred`; answered requires
a saved page. Relations validate endpoints, scope and quoted source evidence, retaining
history when revised. These ledgers record agent judgments; they do not prove completeness.

## Local tracking and review

```json
{"op":"checkpoint","root":"/absolute/my-wiki"}
```

Returns a stable `id` and `pages` map to SHA256 and immutable snapshot paths. Take
this before rewriting existing knowledge. The same page content reuses snapshots.

```json
{"op":"index","root":"/absolute/my-wiki"}
{"op":"sync","root":"/absolute/my-wiki","dry_run":true}
{"op":"sync","root":"/absolute/my-wiki"}
{"op":"review_list","root":"/absolute/my-wiki"}
{"op":"review_complete","root":"/absolute/my-wiki","id":"REVIEW_ID","note":"Compared old/new claims and saved the supported update; no other differences."}
```

Each line is a separate request. `index` rebuilds the catalog; `sync` detects additions,
modifications and deletions using mtime, size and full SHA256, even if mtime is preserved.
Preview changes nothing. Actual sync stores current metadata and a knowledge checkpoint,
then enqueues changed knowledge pages for semantic comparison. Old pending batches survive
later syncs and include `before`/`after` checkpoint IDs. A first sync has no old baseline.
`review_complete` requires a real completion note; tracking does not imply semantic review.
Source changes are tracked and reported but never overwrite original evidence hashes.

## Cognition records and feedback

```json
{
  "op":"cognition_record", "root":"/absolute/my-wiki",
  "checkpoint":"PRE_UPDATE_CHECKPOINT_ID",
  "topic":"Offline support", "kind":"update",
  "old":{"page":"wiki/concepts/offline.md","claim":"Version 1 requires connectivity.","quote":"Version 1 requires connectivity."},
  "new":{"claim":"Version 2 supports offline operation.","evidence":[{"path":"wiki/raw/BATCH/release.md.md","quote":"Version 2 supports offline operation."}]},
  "impact":"Deployment can be reconsidered for disconnected environments.",
  "question":"Should the deployment recommendation be updated?",
  "rationale":"This is a version change, not incompatible claims about the same release."
}
```

The agent supplies the judgment. Changes use `conflict`, `update`, or `context_difference`.
Old evidence must exist in the indicated checkpoint; new quoted evidence must exist in
saved sources or wiki pages. Quotations are mechanically checked against snapshots.
For a past review batch whose new page has since changed again, an evidence entry may
include its `checkpoint` (the batch's `after` id); the quote is checked against that
checkpoint rather than the latest file. This prevents losing intermediate updates.
Save the returned `id`. Repeated identical records are no-ops. To revise a known record,
pass its `id`; material content changes increment its revision and make it reviewable again.
Important first-time knowledge uses `new_finding`, `new_concept`, or `new_method`, with
`old: null` and no required checkpoint. Never fabricate an old belief to fit the schema.
Optional `confidence` is `high`, `medium`, `low`, or `unknown`; `scope` records version,
date or applicability. Source hashes, reading-copy hashes, and origin references are
validated before quotation snapshots are created, and frozen evidence is rechecked
before preparation. Knowledge-page evidence must lead to registered immutable origins.

```json
{"op":"cognition_list","root":"/absolute/my-wiki"}
{"op":"cognition_feedback","root":"/absolute/my-wiki","id":"COGNITION_ID","revision":1,"action":"read"}
{"op":"cognition_feedback","root":"/absolute/my-wiki","id":"COGNITION_ID","revision":1,"action":"defer","until":"2027-01-02T09:00:00+08:00"}
{"op":"cognition_feedback","root":"/absolute/my-wiki","id":"COGNITION_ID","revision":1,"action":"accepted_new","note":"User accepted the version-specific update; corresponding knowledge page updated and verified."}
```

Other actions: `unread`, `keep_disputed`, `dismissed`, `reopen`. Decisions require a note;
deferrals require a future offset-qualified timestamp. Acknowledging user feedback does
not automatically rewrite wiki content. `reopen` does not erase delivery receipts;
on-demand reading is always possible, and a new evidence revision can trigger a new push.
Explicit deferral can resurface a delivered item at the requested time; its reminder
generation is acknowledged independently to avoid repeating it at every later time slot.
`revision` is required and must match the version actually shown. Historical read or
decision feedback is retained without resolving or suppressing newer unseen versions.

## Digest delivery

```json
{"op":"digest_prepare","root":"/absolute/my-wiki","target":"personal-wiki-inbox","limit":20,"dry_run":true}
{"op":"digest_prepare","root":"/absolute/my-wiki","target":"personal-wiki-inbox"}
{"op":"digest_attempt","root":"/absolute/my-wiki","id":"DIGEST_ID","host":"native-host","run_id":"ACTUAL_RUN_ID"}
{"op":"delivery_pending","root":"/absolute/my-wiki","target":"personal-wiki-inbox"}
{"op":"digest_ack","root":"/absolute/my-wiki","id":"DIGEST_ID","receipt":{"host":"native-host","target":"personal-wiki-inbox","message_id":"ACTUAL_MESSAGE_ID","delivered_at":"2026-09-13T09:00:00+08:00","evidence":"Actual native send response or verified delivery record"}}
{"op":"digest_failed","root":"/absolute/my-wiki","attempt_id":"ATTEMPT_ID","evidence":"Actual native confirmation that the message was not sent"}
```

An empty digest returns `empty: true, notify: false`. A draft contains a stable ID, text,
relative report path and exact item revisions. Repeated preparation reuses that ID.
Prepared content is not marked sent or read. `digest_ack` requires actual receipt evidence
after successful native delivery; it acknowledges only the included revisions for that
destination. Updated cognition after preparation remains eligible. Superseded drafts
must not be sent. See [delivery edge cases](cognition.md).
An unknown dispatch returns `notify: false, blocked: delivery_unknown` until reconciled;
this is not an empty digest. `digest_attempt` must precede dispatch, including final
responses sent when a host turn ends. The same run id is idempotent; a confirmed failed
attempt can be retried with a new native run id. Genuine late receipts for superseded
drafts are accepted and acknowledge only their saved revisions. Receipt fields require
actual host evidence; the generic adapter validates structure, not an external service.

```json
{"op":"digest_reconcile","root":"/absolute/my-wiki","session_path":"/actual/codex/session.jsonl","thread_id":"ACTUAL_THREAD_ID"}
```

The Codex adapter reads an explicitly selected local native transcript. It requires
matching session identity, an assistant final message, matching completed-turn output,
and a separate final line `简报编号：DIGEST_ID`. It snapshots the confirmed message and
stores its native message/turn identifiers. It verifies completed thread output, not
OS notification delivery or reading. For a reviewed legacy message without the marker,
supply both `id` (exact digest) and `legacy_message_id` (exact native assistant message);
all included cognition ids must occur in that completed message. Use this migration
only after confirming the delivered claims and versions from the original conversation.

## Native scheduling and skill management

```json
{"op":"schedule_plan","root":"/absolute/my-wiki","name":"Cognition briefing","times":["09:00","12:00"],"timezone":"Asia/Shanghai","target":"personal-wiki-inbox","days":["mon","tue","wed","thu","fri"]}
```

Returns a proposed native job prompt and normalized local schedule; writes nothing.
Default weekdays are all seven. If Python has no IANA timezone data, the plan reports
`native_scheduler_must_validate`; the host must validate the timezone before job creation.
After the host confirms jobs, pass this returned object as `plan` to `schedule_bind`,
with `host`, the actual `job_ids` list and `status` (`active`, `paused`, `unavailable`).
Only unavailable bindings may have no job IDs. The helper saves bindings and a dedicated
`[[briefings]]` block in config while preserving unrelated TOML. It does not create jobs.
Bindings record the tested absolute Python executable. Native `state: active` is separate
from `health: unverified/partial/verified`. Optional `verification` contains actual inspection
fields `evidence`, `checked_at`, `effective_timezone`, `timezone_mode` (`explicit` or
`host_local`), `native_rule`, optional offset-qualified `next_run_at`, and booleans
`delivery_confirmed`, `quiet_success_confirmed`. A next run must match the intended local
weekday and time. Host-local timing is conditional on the machine timezone and never
qualifies as an explicit-timezone guarantee. Preserve unknown checks as unknown/false.

```json
{"op":"skill_list"}
{"op":"skill_show","name":"briefing","format":"text"}
{"op":"skill_install","root":"/absolute/my-wiki","dry_run":true}
{"op":"skill_install","root":"/absolute/my-wiki","targets":["/confirmed/agent/workspace/skills"]}
```

List/show do not require a vault. Text show prints the operation instructions to stdout.
Install defaults to the vault's `.claude/skills` and `.agents/skills`. An explicit target
is a skill directory, not an agent name. Preview checks all collisions without writes.
The helper rejects unowned/edited file collisions and preserves bootstrap edits.
Move a whole vault with its runtime; default installed relative references remain valid.
Custom targets outside the vault need reinstallation if their relative location changes.
