"""Evidence-backed cognition records, delivery receipts and native job handoffs.

The agent supplies semantic judgments. This module validates, snapshots and persists
them; it neither calls a model nor sends messages or schedules operating-system jobs.
"""
from datetime import datetime, timezone
import json
import re
import tomllib
import sys
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
from urllib.parse import quote as urlquote

from wiki_core import (atomic_write, canonical, digest, get_checkpoint, log, now,
                       read_json, safe, snapshot, write_json)
from wiki_evidence import quoted_evidence, verify_frozen

NEW_KINDS = ('new_finding', 'new_concept', 'new_method')


def load(root):
    return read_json(safe(root, ".llm-wiki/cognition.json"),
                     {"items": {}, "digests": {}, "delivered": {}, "schedules": {}})


def save(root, state):
    write_json(safe(root, ".llm-wiki/cognition.json"), state)


def required(value, field):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"Nonempty {field} is required")
    return value.strip()


def aware_time(value):
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("Timestamp must include a timezone offset")
    return parsed.astimezone(timezone.utc)


def verified_text(root, entry):
    data = safe(root, entry["snapshot"]).read_bytes()
    if digest(data) != entry["sha256"]:
        raise ValueError("Evidence snapshot hash mismatch")
    return data.decode("utf-8")


def record(root, checkpoint_id, old, new, topic, kind, impact, question, rationale, ident=None,
           confidence=None, scope=None):
    if kind not in ("conflict", "update", "context_difference", *NEW_KINDS):
        raise ValueError("Unknown cognition kind")
    old_checked = None
    if kind in NEW_KINDS:
        if old is not None:
            raise ValueError('New knowledge must use old: null; use update for an existing claim')
    else:
        cp = get_checkpoint(root, checkpoint_id)
        if not isinstance(old, dict):
            raise ValueError('Old cognition requires a pre-update knowledge page')
        old_entry = cp['pages'].get(old.get('page'))
        if old_entry is None:
            raise ValueError('Old cognition must be a knowledge page in the pre-update checkpoint')
        old_claim = required(old.get('claim'), 'old.claim')
        old_quote = required(old.get('quote'), 'old.quote')
        if old_quote not in verified_text(root, old_entry):
            raise ValueError('Old quotation is absent from the pre-update snapshot')
        old_checked = {'page': old['page'], 'claim': old_claim, 'quote': old_quote, **old_entry}
    if not isinstance(new, dict):
        raise ValueError('new must be an evidence object')
    new_claim = required(new.get("claim"), "new.claim")
    checked = quoted_evidence(root, new.get('evidence'))
    content = {"topic": required(topic, "topic"), "kind": kind,
               "old": old_checked,
               "new": {"claim": new_claim, "evidence": checked},
               "impact": required(impact, "impact"), "question": required(question, "question"),
               "rationale": required(rationale, "rationale")}
    if confidence is not None:
        if confidence not in ('high', 'medium', 'low', 'unknown'):
            raise ValueError('Invalid confidence')
        content['confidence'] = confidence
    if scope is not None:
        content['scope'] = required(scope, 'scope')
    state = load(root)
    key = ([old['page'], old_claim.casefold(), new_claim.casefold()] if old_checked else
           [kind, topic.casefold(), new_claim.casefold()])
    fingerprint = digest(canonical(key).encode())[:24]
    if ident is not None and ident not in state["items"]:
        raise ValueError("Cannot update a nonexistent cognition id")
    ident = ident or fingerprint
    existing = state["items"].get(ident)
    if existing and existing["content"] == content:
        return {"id": ident, "revision": existing["revision"], "duplicate": True}
    state["items"][ident] = {"id": ident, "revision": existing["revision"] + 1 if existing else 1,
                             "content": content, "created": existing["created"] if existing else now(),
                             "updated": now(), "decision": "pending", "read_revision": 0,
                             "defer_until": None,
                             "reminder": existing.get("reminder", 0) if existing else 0,
                             "feedback": existing.get("feedback", []) if existing else [],
                             "history": (existing.get("history", []) + [{"revision": existing["revision"],
                                         "content": existing["content"], "decision": existing["decision"]}]
                                         if existing else [])}
    save(root, state)
    log(root, "cognition", ident + " " + kind)
    return {"id": ident, "revision": state["items"][ident]["revision"], "duplicate": False}


def feedback(root, ident, action, note=None, until=None, revision=None):
    state = load(root)
    item = state["items"].get(ident)
    if item is None:
        raise ValueError("Unknown cognition id")
    if type(revision) is not int or not 1 <= revision <= item['revision']:
        raise ValueError('Feedback requires the exact displayed revision')
    if revision != item['revision']:
        if action not in ('read', 'accepted_new', 'keep_disputed', 'dismissed'):
            raise ValueError('This action requires the current revision; the displayed revision is stale')
        if action != 'read':
            required(note, 'resolution note')
        item['read_revision'] = max(item['read_revision'], revision)
        item.setdefault('feedback', []).append({'action': action, 'note': note, 'at': now(),
                                               'revision': revision, 'historical_only': True})
        save(root, state)
        log(root, 'feedback', f'{ident} revision {revision} {action} (historical only)')
        return item
    if action == "read":
        item["read_revision"] = item["revision"]
        item["defer_until"] = None
    elif action == "unread":
        item["read_revision"] = 0
    elif action == "defer":
        if not until or aware_time(until) <= datetime.now(timezone.utc):
            raise ValueError("Deferral requires a future timestamp with timezone")
        item["defer_until"] = until
        item["reminder"] = item.get("reminder", 0) + 1
    elif action in ("accepted_new", "keep_disputed", "dismissed", "reopen"):
        item["decision"] = "pending" if action == "reopen" else action
        item["resolution_note"] = required(note, "resolution note")
        item["defer_until"] = None
        item["read_revision"] = 0 if action == "reopen" else item["revision"]
    else:
        raise ValueError("Unknown feedback action")
    item.setdefault("feedback", []).append({"action": action, "note": note, "at": now(),
                                             "revision": item["revision"]})
    save(root, state)
    log(root, "feedback", ident + " " + action)
    return item


def cognition_list(root):
    return {"items": list(load(root)["items"].values())}


def digest_text(ident, entries):
    names = {"conflict": "认知冲突", "update": "结论更新", "context_difference": "适用条件差异",
             'new_finding': '新发现', 'new_concept': '新概念', 'new_method': '新方法'}
    lines = ["# 认知更新简报", "", f"简报编号：{ident}", ""]
    for item in entries:
        c = item["content"]
        lines.extend([f"## {c['topic']} · {names[c['kind']]}", "",
                      f"记录：{item['id']} / 第 {item['revision']} 版", ""])
        if c.get('old'):
            lines.extend([f"**已有认知**：{c['old']['claim']}", "",
                      f"原页面：[知识页](../../{urlquote(c['old']['page'], safe='/')})；"
                      f"[更新前证据](../../{c['old']['snapshot']})", "",
                      f"> {c['old']['quote'].replace(chr(10), chr(10) + '> ')}", ""])
        else:
            lines.extend(['**基线**：新增知识，无对应的旧结论。', ''])
        lines.extend([f"**新认知**：{c['new']['claim']}", '',
                      f"**置信度**：{c.get('confidence', 'unknown')}；**适用范围**：{c.get('scope', '见证据与待确认项')}", ''])
        for evidence in c["new"]["evidence"]:
            lines.extend([f"来源：[证据原文](../../{urlquote(evidence['path'], safe='/')}) · "
                          f"[本次证据快照](../../{evidence['snapshot']})", "",
                          f"> {evidence['quote'].replace(chr(10), chr(10) + '> ')}", ""])
        lines.extend([f"**判断依据**：{c['rationale']}", "", f"**影响**：{c['impact']}", "",
                      f"**待确认**：{c['question']}", "",
                      "反馈请指明记录编号和版本：已读 / 接受新观点 / 保留争议 / 稍后处理。", ""])
    return "\n".join(lines)


def prepare(root, target, limit=20, dry_run=False):
    target = required(target, "delivery target key")
    if not 1 <= limit <= 100:
        raise ValueError("limit must be between 1 and 100")
    state = load(root)
    pending = [a for a in state.get('attempts', {}).values()
               if a['target'] == target and a['status'] == 'unknown']
    if pending:
        return {'empty': False, 'notify': False, 'target': target,
                'blocked': 'delivery_unknown', 'pending_attempts': pending}
    delivered = state["delivered"].get(target, {})
    reminded = state.get("reminded", {}).get(target, {})
    entries = []
    for item in state["items"].values():
        if item["decision"] in ("accepted_new", "dismissed"):
            continue
        if item.get("defer_until") and aware_time(item["defer_until"]) > datetime.now(timezone.utc):
            continue
        reminder_due = bool(item.get("defer_until")) and item.get("reminder", 0) > reminded.get(item["id"], 0)
        if item["read_revision"] >= item["revision"] and not reminder_due:
            continue
        if delivered.get(item["id"], 0) >= item["revision"] and not reminder_due:
            continue
        if item['content'].get('old'):
            old = item['content']['old']
            if old['quote'] not in verified_text(root, old):
                raise ValueError('Old evidence quotation mismatch')
        for evidence in item['content']['new']['evidence']:
            verify_frozen(root, evidence)
        entries.append(item)
    entries.sort(key=lambda i: (i["updated"], i["id"]))
    entries = entries[:limit]
    if not entries:
        return {"empty": True, "notify": False, "target": target}
    versions = {e["id"]: e["revision"] for e in entries}
    reminders = {e["id"]: e.get("reminder", 0) if e.get("defer_until") else 0 for e in entries}
    ident = digest(canonical([target, versions, reminders]).encode())[:24]
    text = digest_text(ident, entries)
    relative = f".llm-wiki/digests/{ident}.md"
    existing = state['digests'].get(ident)
    if existing:
        text = safe(root, existing['path']).read_text(encoding='utf-8')
        if existing.get('report_sha256') and digest(text.encode()) != existing['report_sha256']:
            raise ValueError('Prepared digest was modified')
    if not dry_run:
        # Supersede unacknowledged obsolete drafts; keep them for audit.
        for draft in state["digests"].values():
            if draft["target"] == target and draft["status"] == "prepared" and draft["id"] != ident:
                draft["status"] = "superseded"
        if not existing:
            atomic_write(safe(root, relative), text)
        if ident not in state["digests"]:
            state["digests"][ident] = {"id": ident, "target": target, "versions": versions,
                                      "reminders": reminders,
                                      "path": relative, "status": "prepared", "created": now(),
                                      'report_sha256': digest(text.encode())}
        else:
            state["digests"][ident]["status"] = "prepared"
        save(root, state)
    return {"id": ident, "target": target, "path": relative, "text": text, "versions": versions,
            "empty": False, "notify": True, "dry_run": dry_run, "status": "prepared"}


def delivery_attempt(root, ident, host, run_id):
    state = load(root)
    draft = state['digests'].get(ident)
    if not draft or draft['status'] != 'prepared':
        raise ValueError('Only a current prepared digest can be dispatched')
    required(host, 'host'); required(run_id, 'native run id')
    key = digest(canonical([ident, host, run_id]).encode())[:24]
    attempts = state.setdefault('attempts', {})
    if key in attempts:
        return attempts[key]
    if any(a['target'] == draft['target'] and a['status'] == 'unknown' for a in attempts.values()):
        raise ValueError('Reconcile the previous unknown delivery before dispatch')
    current = prepare(root, draft['target'], limit=len(draft['versions']), dry_run=True)
    if current.get('id') != ident or not current['notify']:
        raise ValueError('Digest is no longer current; prepare again before dispatch')
    attempts[key] = {'id': key, 'digest_id': ident, 'target': draft['target'],
                     'host': host, 'run_id': run_id, 'versions': draft['versions'],
                     'status': 'unknown', 'created': now()}
    save(root, state)
    return attempts[key]


def delivery_failed(root, attempt_id, evidence):
    required(evidence, 'verified failed/not-sent evidence')
    state = load(root)
    attempt = state.get('attempts', {}).get(attempt_id)
    if not attempt or attempt['status'] != 'unknown':
        raise ValueError('Only an unknown attempt can be resolved as failed')
    attempt.update(status='failed', evidence=evidence, resolved_at=now())
    save(root, state)
    return attempt


def pending_deliveries(root, target=None):
    return {'attempts': [a for a in load(root).get('attempts', {}).values()
                         if a['status'] == 'unknown' and (target is None or a['target'] == target)]}


def acknowledge(root, ident, receipt):
    if not isinstance(receipt, dict):
        raise ValueError('Structured native delivery receipt is required')
    for field in ('host', 'target', 'message_id', 'delivered_at', 'evidence'):
        required(receipt.get(field), 'receipt.' + field)
    aware_time(receipt['delivered_at'])
    state = load(root)
    draft = state["digests"].get(ident)
    if draft is None:
        raise ValueError("Unknown digest id")
    if receipt['target'] != draft['target']:
        raise ValueError('Delivery receipt target mismatch')
    if draft['status'] == 'delivered':
        return {'id': ident, 'status': 'delivered', 'duplicate': True, 'user_read': 'not_inferred'}
    # A late receipt confirms only this immutable draft, even when it was superseded.
    delivered = state["delivered"].setdefault(draft["target"], {})
    for item, revision in draft["versions"].items():
        delivered[item] = max(delivered.get(item, 0), revision)
    reminded = state.setdefault("reminded", {}).setdefault(draft["target"], {})
    for item, reminder in draft.get("reminders", {}).items():
        reminded[item] = max(reminded.get(item, 0), reminder)
    draft.update(status="delivered", receipt=receipt, delivered_at=now())
    for attempt in state.get('attempts', {}).values():
        if attempt['digest_id'] == ident and attempt['status'] == 'unknown':
            attempt.update(status='delivered', receipt=receipt, resolved_at=now())
    save(root, state)
    return {"id": ident, "status": "delivered", "user_read": "not_inferred"}


def schedule_plan(root, name, times, timezone_name, target, days=None):
    required(name, "schedule name")
    required(target, "delivery target key")
    required(timezone_name, "IANA timezone")
    if not isinstance(times, list) or not times or any(
            not isinstance(t, str) or not re.fullmatch(r"(?:[01]\d|2[0-3]):[0-5]\d", t) for t in times):
        raise ValueError("times must be local HH:MM values")
    if timezone_name != "UTC" and not re.fullmatch(r"[A-Za-z_+-]+(?:/[A-Za-z0-9_+.-]+)+", timezone_name):
        raise ValueError("Use an IANA timezone, for example Asia/Shanghai")
    try:
        ZoneInfo(timezone_name)
        zone_validation = "validated"
    except ZoneInfoNotFoundError:
        zone_validation = "native_scheduler_must_validate"
    days = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"] if days is None else days
    if not isinstance(days, list) or not days or any(not isinstance(d, str) for d in days) or not set(days) <= {"mon", "tue", "wed", "thu", "fri", "sat", "sun"}:
        raise ValueError("Invalid weekdays")
    ident = digest(canonical([str(root), name, target]).encode())[:24]
    prompt = (
        f"Maintain the cognition briefing for the LLM Wiki at {root}. "
        "Read wiki-purpose.md, wiki-schema.md and the installed briefing skill at "
        ".llm-wiki/runtime/operations/briefing/SKILL.md. Use this vault only. "
        f"Run helpers with the verified interpreter {Path(sys.executable).absolute()}. "
        "Before preparing a digest, reconcile prior native completed deliveries and unknown attempts. "
        "Run local sync, then inspect all pending review batches and their before/after checkpoints. "
        "Read saved evidence and use semantic judgment to distinguish contradictions, updates, "
        "differences in date, version or scope, and substantive new findings/concepts/methods without an old claim. Preserve old quotations and source snapshots; "
        "record evidence-backed cognition items before completing each review batch. "
        f"Prepare a digest for delivery target {target!r}. "
        "Stay quiet if there is no new actionable material. Do not emit a routine success report. "
        "Deliver through the user's configured native channel only. A generated digest is not a delivery: "
        "acknowledge it only with an actual delivery receipt or verified native run delivery status. "
        "Record digest_attempt before dispatch; retain the exact digest ID and item revisions in the final message. "
        "For Codex thread delivery, include a separate line 简报编号：DIGEST_ID and reconcile the completed "
        "native session with digest_reconcile on the next wake. A failed/unknown turn is not a receipt. "
        "Reuse its digest id for idempotent retries. Do not infer that the user has read it. "
        "Do not fetch external sources or create additional jobs without user authorization. "
        "Report material failures or required user action through the configured channel."
    )
    return {"id": ident, "name": name, "times": sorted(set(times)), "timezone": timezone_name,
            "timezone_validation": zone_validation, "days": days, "target": target, "prompt": prompt,
            "state": "planned", "requires": ["native_scheduler", "authorized_delivery_channel",
                                                 "no_change_suppression", "delivery_confirmation"]}


def bind_schedule(root, plan, host, job_ids, status="active", verification=None):
    if status not in ("active", "paused", "unavailable"):
        raise ValueError("status must be active, paused, or unavailable")
    checked = schedule_plan(root, plan["name"], plan["times"], plan["timezone"], plan["target"], plan.get("days"))
    required(host, "native scheduler identity")
    if status != "unavailable" and (not isinstance(job_ids, list) or not job_ids or
                                   any(not isinstance(j, str) or not j.strip() for j in job_ids)):
        raise ValueError("Native scheduler job ids are required; a plan is not a running job")
    state = load(root)
    checked.update(host=host, job_ids=job_ids, state=status, updated=now())
    checked['runtime'] = {'python': str(Path(sys.executable).absolute()), 'version': sys.version.split()[0],
                          'file_access': safe(root, 'wiki-purpose.md').is_file(), 'checked_at': now()}
    checked['health'] = 'unverified'
    if verification is not None:
        if not isinstance(verification, dict):
            raise ValueError('verification must contain actual native inspection results')
        for field in ('evidence', 'checked_at', 'effective_timezone', 'timezone_mode', 'native_rule'):
            required(verification.get(field), 'verification.' + field)
        aware_time(verification['checked_at'])
        if verification['effective_timezone'] != checked['timezone']:
            raise ValueError('Native effective timezone differs from intended timezone')
        if verification['timezone_mode'] not in ('explicit', 'host_local'):
            raise ValueError('timezone_mode must be explicit or host_local')
        if verification.get('next_run_at'):
            local = aware_time(verification['next_run_at']).astimezone(ZoneInfo(checked['timezone']))
            weekday = ('mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun')[local.weekday()]
            if local.strftime('%H:%M') not in checked['times'] or weekday not in checked['days']:
                raise ValueError('Native next run does not match the intended local schedule')
        checked['verification'] = verification
        checked['health'] = 'verified' if (verification['timezone_mode'] == 'explicit'
                    and all(verification.get(k) is True for k in ('delivery_confirmed', 'quiet_success_confirmed'))
                    and verification.get('next_run_at')) else 'partial'
    # Native ACTIVE describes configuration, not a passed end-to-end delivery test.
    state["schedules"][checked["id"]] = checked
    # Preserve all user TOML outside the helper's dedicated block.
    path = safe(root, ".llm-wiki/config.toml")
    text = path.read_text(encoding="utf-8")
    start, end = "# llm-wiki briefings:begin", "# llm-wiki briefings:end"
    if (start in text) != (end in text):
        raise ValueError("Malformed managed briefing block")
    if start in text:
        prefix, tail = text.split(start, 1)
        _, suffix = tail.split(end, 1)
        base = prefix + suffix
    else:
        base = text
    if "briefings" in tomllib.loads(base):
        raise ValueError("Unmanaged briefings config exists; reconcile it without overwriting user settings")
    lines = [start]
    for schedule in state["schedules"].values():
        lines.append("[[briefings]]")
        for key in ("id", "name", "times", "timezone", "days", "target", "host", "job_ids", "state"):
            lines.append(key + " = " + json.dumps(schedule[key], ensure_ascii=False))
        lines.append("")
    lines.append(end)
    rendered = base.rstrip() + "\n\n" + "\n".join(lines) + "\n"
    tomllib.loads(rendered)
    atomic_write(path, rendered)
    save(root, state)
    return checked
