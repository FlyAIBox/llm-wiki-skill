---
name: briefing
description: Review cognition changes and deliver wiki briefings.
license: MIT
metadata:
  hermes:
    tags: [wiki, cognition, briefing]
    category: research
    related_skills: [llm-wiki]
---

# Briefing Skill

Surface evidence-backed differences between new and established wiki understanding.
Use the host's scheduler and notifications for user-configured timed delivery.

## When to Use
The user wants cognition updates, a conflict digest, scheduled briefings, or to respond
to a finding. Also use on an already-authorized native scheduled run.

## Prerequisites
Read purpose, schema and [cognition lifecycle](../../references/cognition.md).
For scheduling, discover native tools and the permitted channel using
[agent adaptation](../../references/agent-adapters.md). File tools plus `terminal`
in Hermes, or equivalents elsewhere, support the local half of this workflow.

## How to Run
Use `../../scripts/wiki_tool.py` and the [helper API](../../references/helper-api.md).
All schedule creation and delivery still go through the actual host tools.

## Quick Reference
Reconcile prior delivery → `status` / `source_list` → `sync` → `review_list` → semantic comparison → `cognition_record`
→ `review_complete` → `digest_prepare` → `digest_attempt` → native delivery → verified receipt.

## Procedure
For a question or preview without permission to update/send, use read-only checks and
`dry_run: true` for sync/digest preparation. Answer from saved evidence and disclose
unreviewed changes; do not mutate review, delivery or scheduling state just to answer.
The following write lifecycle applies to authorized maintenance or delivery runs.

1. For setup, gather intended local times, timezone and recipient/channel. Treat 09:00,
   noon and before-work-end as examples; do not guess a user's work-end time. Produce a
   `schedule_plan`, then inspect existing native jobs and update a matching one or create
   it. Bind returned job IDs with `schedule_bind`. Check actual enabled state, file access
   and delivery capability before reporting success. Save unsupported setups as unavailable
   with no job IDs, explain the missing capability and offer on-demand operation. Give
   manual setup guidance only for a verified host mechanism; do not invent scheduler paths.
2. On a run, use the recorded Python executable and reconcile previous deliveries first.
   See the concrete Codex transcript adapter in [agent adaptation](../../references/agent-adapters.md).
   `delivery_pending` lists unknown attempts; `digest_prepare` blocks another push to
   that destination until they are reconciled. A verified failed/not-sent outcome can
   be recorded with `digest_failed`; elapsed time alone is not failure evidence.
   Read `status` and use `source_list` to inspect unregistered, uncovered, missing,
   changed or unverified inputs. Read `source_progress` when section-level work is relevant.
   Source-only changes do not create knowledge-page review batches. Process a backlog
   through ingest only when that material is already authorized; otherwise report the gap.
   Do not turn unread inputs into `source_review: no_new_knowledge` to clear a warning.
   Unchanged non-actionable backlogs do not need a repeated scheduled notification.
   Serialize wiki writes, read purpose and capture local changes with `sync`.
   Inspect every pending review batch. Compare its old and new checkpoint pages, read
   evidence, and search prior pages for additions that revise established understanding.
   Preserve a batch as pending if analysis was interrupted or evidence is insufficient.
3. Classify genuine conflicts, updates, contextual differences, and important new
   findings/concepts/methods. Use `new_finding`, `new_concept` or `new_method` with
   `old: null` when no prior claim exists. Save exact quotations
   and frozen evidence with `cognition_record`; use `quote_find` / `quote_verify` for exact
   excerpts instead of guessing Markdown formatting. Treat first-ingest disagreements as source
   disagreements. Mark batches complete with a substantive note after analysis, even if
   the supported result is that no cognition change was found.
4. Prepare a digest with a stable destination key shared by all its time slots. If empty
   on a scheduled run, use the host's suppression behavior: no routine “nothing new” notification. If the host
   cannot suppress no-change notifications, disclose that limitation during configuration.
   For an explicit request, explain that there are no eligible updates and separately
   mention pending analysis or delivery uncertainty. Never describe a blocked digest as empty.
5. Read `result.text` from preparation and check evidence before sending; no second read
   of the identical report file is needed. Present old/new claims, dates or scope,
   why the difference matters and what needs the user's judgment. Use channel-appropriate
   links; remote recipients need an accessible view or excerpts, not unopenable local paths.
6. Call `digest_attempt` with the native run id before sending through the authorized channel.
   Keep the digest id and record revision labels in the delivered message. For Codex,
   put `简报编号：DIGEST_ID` on its own line. Use the digest id as idempotency key when
   supported. Call `digest_ack` only after an actual send receipt or verified host delivery
   status; never acknowledge merely because the report file exists or the run started.
   For host-managed end-of-run delivery, reconcile the completed run on the next wake.
   Accept genuine late receipts for superseded drafts; acknowledge only their saved revisions.
   An unknown delivery outcome requires reconciliation before retrying.
7. Map user feedback to the exact cognition id and displayed revision: read, defer, accept new, keep disputed or
   dismiss. Preserve both evidence snapshots. If accepting a new claim entails updating
   knowledge, perform and verify that edit before marking it accepted; never equate
   delivered with read. Pause or change native jobs when the user requests it, then update
   the local binding to match.

## Pitfalls
The helper does not independently discover contradictions, run a daemon or send messages.
No-change quietness, persistence during host shutdown and delivery receipts depend on
the host. Do not promise exactly-once delivery when its channel offers no idempotency.

## Verification
Verify no-change suppression, failed-send retry state, revision-specific acknowledgments,
source links and recorded feedback. An unavailable scheduler leaves a usable on-demand
briefing workflow, not a falsely active subscription.
