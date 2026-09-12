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
`sync` → `review_list` → semantic comparison → `cognition_record` → `review_complete`
→ `digest_prepare` → native delivery → `digest_ack` after verified delivery.

## Procedure
1. For setup, gather intended local times, timezone and recipient/channel. Treat 09:00,
   noon and before-work-end as examples; do not guess a user's work-end time. Produce a
   `schedule_plan`, then inspect existing native jobs and update a matching one or create
   it. Bind returned job IDs with `schedule_bind`. Check actual enabled state, file access
   and delivery capability before reporting success. Save unsupported setups as unavailable.
2. On a run, serialize wiki writes, read purpose and capture local changes with `sync`.
   Inspect every pending review batch. Compare its old and new checkpoint pages, read
   evidence, and search prior pages for additions that revise established understanding.
   Preserve a batch as pending if analysis was interrupted or evidence is insufficient.
3. Classify genuine conflicts, updates and contextual differences. Save exact quotations
   and frozen evidence with `cognition_record`. Treat first-ingest disagreements as source
   disagreements. Mark batches complete with a substantive note after analysis, even if
   the supported result is that no cognition change was found.
4. Prepare a digest with a stable destination key shared by all its time slots. If empty,
   use the host's suppression behavior: no routine “nothing new” notification. If the host
   cannot suppress no-change notifications, disclose that limitation during configuration.
5. Read the draft and evidence before sending. Present old/new claims, dates or scope,
   why the difference matters and what needs the user's judgment. Use channel-appropriate
   links; remote recipients need an accessible view or excerpts, not unopenable local paths.
6. Send through the authorized native channel. Use the digest id as idempotency key when
   supported. Call `digest_ack` only after an actual send receipt or verified host delivery
   status; never acknowledge merely because the report file exists or the run started.
   For host-managed end-of-run delivery, reconcile the completed run on the next wake.
   An unknown delivery outcome requires reconciliation before retrying.
7. Map user feedback to the exact cognition id: read, defer, accept new, keep disputed or
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
