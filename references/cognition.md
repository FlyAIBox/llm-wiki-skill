# Cognition and briefing lifecycle

## Meaning and scope

Established cognition consists of attributed claims already saved on this vault's
knowledge pages. Sources and raw reading copies are evidence, not automatically accepted
beliefs. `wiki-purpose.md` controls relevance and priority, not factual truth. Agent-global
memory or another vault enters this baseline only through an explicit, attributed import.

Classify after reading evidence:

| Kind | Judgment | Example |
|---|---|---|
| `conflict` | Incompatible claims about the same subject under comparable conditions | Two studies give incompatible results under the same conditions |
| `update` | New evidence changes a prior recommendation or a time-dependent fact | A later release gains a previously unavailable feature |
| `context_difference` | Apparently conflicting claims concern different versions, dates, populations or assumptions | Cloud and on-device deployments have different constraints |
| `new_finding`, `new_concept`, `new_method` | Important new knowledge without a prior corresponding claim | A newly captured reproducible method |

Confidence in a quoted source is separate from the source's truth. The helper validates
that quotations exist, not that the agent's interpretation is correct. Record the rationale,
impact and open question. Avoid a record for harmless paraphrasing or every tiny edit.
New kinds allow `old: null` and no checkpoint. Source and reading-copy hashes are
validated before new evidence is snapshotted. Read-only hash validation cannot judge
whether an extraction or a source's interpretation is scientifically correct.

## Comparing before and after

Before editing, take a checkpoint. After edits, local sync stores a new checkpoint and
adds a pending review batch. For outside edits, the last sync checkpoint is the baseline.
All pending batches survive later syncs. Reading old snapshot paths allows the agent
to review overwritten pages without reconstructing prior claims from memory.

Review modified pages against the old snapshot. For added pages, search old knowledge
for related claims; new pages alone do not imply a contradiction. Deletions may be an
archive or editorial change. An empty baseline cannot support claims about the user's
previous beliefs; document initial cross-source disagreements as contested knowledge.
Record supported differences before completing the batch. Missing evidence or an
interrupted comparison leaves a batch pending; a no-conflict result gets an explicit note.

Old cognition records embed a checkpoint quotation and immutable snapshot reference.
New evidence is also snapshotted, so later raw-view regeneration cannot change a digest's
supporting text. If a record's content changes, preserve its history and bump its revision.
For repeated evidence about the same issue, reuse its known cognition id rather than
creating loosely paraphrased duplicate records.

## State model

```text
Saved evidence → pre-update checkpoint → updated knowledge → pending review
    → agent comparison → cognition item (revision N) → prepared digest
    → delivery attempt (unknown) → verified native delivery → delivered revision N
    → user feedback (read / accept / dispute / defer)
```

Prepared, delivered and read are different events. Semantic edits increment cognition
revision; reading/deferring is feedback rather than new evidence. Accepting a viewpoint
does not erase old evidence. When accepting entails page changes, the agent performs
and verifies them, records the decision, and tracks those edits through the same lifecycle.

## Delivery behavior

- Prepare drafts only for unread, not-yet-delivered revisions which are not resolved or
  deferred. Use a stable destination key shared by morning, midday and evening jobs.
- No new eligible items means `notify: false`; suppress routine output through the native
  scheduler. Existing unresolved disagreement alone does not cause repeated pushes.
- An explicit “remind me later” is different: deferral creates a reminder generation.
  When due, it may resurface a previously delivered/read item once per destination.
  Its receipt acknowledges that generation separately from the knowledge revision.
- A prepared digest is immutable in intent: its id identifies destination and included
  revisions. Its report links snapshots as well as current pages. New revisions do not
  get acknowledged by a receipt for an old revision.
- On confirmed success, acknowledge the draft with actual receipt evidence. On failure,
  leave it unacknowledged. On an uncertain outcome, inspect host delivery history before
  retrying. Record `digest_attempt` before dispatch; an unknown attempt blocks another
  digest to the target. Mark `digest_failed` only with confirmed failed/not-sent evidence.
  Use the digest id as a channel idempotency key when supported.
- A crash after sending but before acknowledgment can otherwise repeat a message.
  There is no universal exactly-once guarantee across arbitrary agent channels; use
  native receipts/idempotency and disclose missing support during setup.
- If the scheduler sends the final response only after the agent turn finishes, do not
  pre-acknowledge. Reconcile the completed run's verified delivery on the next wake.
- Late receipts remain valid for superseded drafts: they acknowledge only those drafts'
  revisions and reminder generations. Receipt fields bind host, target, message id,
  delivered time and actual native evidence. Codex completed-thread output verification
  is distinct from OS notification delivery and user reading.
- Read local evidence before converting a Markdown report to a channel message. Preserve
  claim attribution and useful excerpts if the recipient cannot open local file links.
- An on-demand request can read any cognition item regardless of prior delivery state.

Feedback requires the exact displayed revision. Historical read/accept/dispute/dismiss
feedback is retained against that version and leaves newer versions eligible. Never
reinterpret an old acceptance as acceptance of the current claim. A stale defer/unread/
reopen request needs the user-visible current context before applying to a newer version.

## Scheduling boundaries

The skill supplies a job prompt; the host creates and runs jobs. Confirm intended times,
timezone and destination. Update matching jobs instead of duplicating them; retain returned
IDs. Pausing, rescheduling and disabling must happen in the native scheduler and then in
the local binding. A saved config is an inventory, not proof the native job still exists.

Templates mentioning 09:00, midday or work-end are not an instruction to start three jobs.
A request to implement this skill's scheduling capability is not a request to subscribe
its author. External-source monitoring needs its own authorization and collection scope.
If no scheduler or channel is available, report the limitation and offer on-demand drafts.
