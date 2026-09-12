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

```json
{"op":"raw_view","root":"/absolute/my-wiki","source":"sources/2026-09-12/BATCH/report.pdf","text":"# Extracted text\n\nPage 3: actual source content..."}
```

Supply actual host-extracted text, not invented contents. Requires a registered,
unchanged source. Copies use names such as `report.pdf.md` to avoid format collisions.
Derived views may be rebuilt; originals are never overwritten.

## Retrieval, graph and health

```json
{"op":"search","root":"/absolute/my-wiki","query":"agent memory","limit":10,"include_raw":false}
```

Returns `mode: local_bm25`, scanned count and ranked path/title/excerpt/source results.
`limit` is 1–100. The host agent performs semantic reading and reranking. CJK text
uses characters and adjacent pairs; English uses case-folded word tokens.

```json
{"op":"graph","root":"/absolute/my-wiki"}
```

Returns nodes, directed edges, communities, hubs, orphans, wanted pages and ambiguous
links. Excludes raw views, indexes, archives and assets. Recognizes full-path and
unambiguous title/basename/alias links, aliases after `|`, anchors after `#`, and
relative links. Ignores self-links, embedded images, escaped examples and fenced code.
`converged` reports whether label propagation settled before its iteration cap.

```json
{"op":"status","root":"/absolute/my-wiki"}
```

Returns counts, metadata/source/index issues, immutable-source drift, content-review
signals, graph, tracking changes, pending reviews and locally recorded schedules.
It does not verify live native jobs or the truth of claims. The agent performs those checks.

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

The agent supplies the judgment. `kind` is `conflict`, `update`, or `context_difference`.
Old evidence must exist in the indicated checkpoint; new quoted evidence must exist in
saved sources or wiki pages. Quotations are mechanically checked against snapshots.
For a past review batch whose new page has since changed again, an evidence entry may
include its `checkpoint` (the batch's `after` id); the quote is checked against that
checkpoint rather than the latest file. This prevents losing intermediate updates.
Save the returned `id`. Repeated identical records are no-ops. To revise a known record,
pass its `id`; material content changes increment its revision and make it reviewable again.

```json
{"op":"cognition_list","root":"/absolute/my-wiki"}
{"op":"cognition_feedback","root":"/absolute/my-wiki","id":"COGNITION_ID","action":"read"}
{"op":"cognition_feedback","root":"/absolute/my-wiki","id":"COGNITION_ID","action":"defer","until":"2027-01-02T09:00:00+08:00"}
{"op":"cognition_feedback","root":"/absolute/my-wiki","id":"COGNITION_ID","action":"accepted_new","note":"User accepted the version-specific update; corresponding knowledge page updated and verified."}
```

Other actions: `unread`, `keep_disputed`, `dismissed`, `reopen`. Decisions require a note;
deferrals require a future offset-qualified timestamp. Acknowledging user feedback does
not automatically rewrite wiki content. `reopen` does not erase delivery receipts;
on-demand reading is always possible, and a new evidence revision can trigger a new push.
Explicit deferral can resurface a delivered item at the requested time; its reminder
generation is acknowledged independently to avoid repeating it at every later time slot.

## Digest delivery

```json
{"op":"digest_prepare","root":"/absolute/my-wiki","target":"personal-wiki-inbox","limit":20,"dry_run":true}
{"op":"digest_prepare","root":"/absolute/my-wiki","target":"personal-wiki-inbox"}
{"op":"digest_ack","root":"/absolute/my-wiki","id":"DIGEST_ID","receipt":"ACTUAL_NATIVE_DELIVERY_RECEIPT"}
```

An empty digest returns `empty: true, notify: false`. A draft contains a stable ID, text,
relative report path and exact item revisions. Repeated preparation reuses that ID.
Prepared content is not marked sent or read. `digest_ack` requires actual receipt evidence
after successful native delivery; it acknowledges only the included revisions for that
destination. Updated cognition after preparation remains eligible. Superseded drafts
must not be sent. See [delivery edge cases](cognition.md).

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
