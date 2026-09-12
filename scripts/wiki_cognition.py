"""Evidence-backed cognition records, delivery receipts and native job handoffs.

The agent supplies semantic judgments. This module validates, snapshots and persists
them; it neither calls a model nor sends messages or schedules operating-system jobs.
"""
from datetime import datetime, timezone
import json
import re
import tomllib
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
from urllib.parse import quote as urlquote

from wiki_core import (atomic_write, canonical, digest, get_checkpoint, log, now,
                       read_json, safe, snapshot, write_json)


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


def record(root, checkpoint_id, old, new, topic, kind, impact, question, rationale, ident=None):
    if kind not in ("conflict", "update", "context_difference"):
        raise ValueError("kind must be conflict, update, or context_difference")
    cp = get_checkpoint(root, checkpoint_id)
    if not isinstance(old, dict) or not isinstance(new, dict):
        raise ValueError("old and new must be evidence objects")
    old_entry = cp["pages"].get(old.get("page"))
    if old_entry is None:
        raise ValueError("Old cognition must be a knowledge page in the pre-update checkpoint")
    old_claim = required(old.get("claim"), "old.claim")
    old_quote = required(old.get("quote"), "old.quote")
    if old_quote not in verified_text(root, old_entry):
        raise ValueError("Old quotation is absent from the pre-update snapshot")
    new_claim = required(new.get("claim"), "new.claim")
    evidence = new.get("evidence")
    if not isinstance(evidence, list) or not evidence:
        raise ValueError("New cognition requires quoted, saved evidence")
    checked = []
    for e in evidence:
        path = e.get("path", "")
        if not path.startswith(("sources/", "wiki/")):
            raise ValueError("New evidence must be inside this vault's sources/ or wiki/")
        quote = required(e.get("quote"), "evidence.quote")
        if e.get("checkpoint"):
            frozen = get_checkpoint(root, e["checkpoint"])["pages"].get(path)
            if frozen is None:
                raise ValueError("New evidence page is absent from its checkpoint")
            verified_text(root, frozen)
            data = safe(root, frozen["snapshot"]).read_bytes()
        else:
            data = safe(root, path).read_bytes()
        text = data.decode("utf-8")
        if quote not in text:
            raise ValueError("New quotation is absent from saved evidence: " + path)
        checked.append({"path": path, "quote": quote, **snapshot(root, data)})
    content = {"topic": required(topic, "topic"), "kind": kind,
               "old": {"page": old["page"], "claim": old_claim, "quote": old_quote, **old_entry},
               "new": {"claim": new_claim, "evidence": checked},
               "impact": required(impact, "impact"), "question": required(question, "question"),
               "rationale": required(rationale, "rationale")}
    state = load(root)
    fingerprint = digest(canonical([old["page"], old_claim.casefold(), new_claim.casefold()]).encode())[:24]
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


def feedback(root, ident, action, note=None, until=None):
    state = load(root)
    item = state["items"].get(ident)
    if item is None:
        raise ValueError("Unknown cognition id")
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
    names = {"conflict": "认知冲突", "update": "结论更新", "context_difference": "适用条件差异"}
    lines = ["# 认知更新简报", "", f"简报编号：{ident}", ""]
    for item in entries:
        c = item["content"]
        lines.extend([f"## {c['topic']} · {names[c['kind']]}", "",
                      f"记录：{item['id']} / 第 {item['revision']} 版", "",
                      f"**已有认知**：{c['old']['claim']}", "",
                      f"原页面：[知识页](../../{urlquote(c['old']['page'], safe='/')})；"
                      f"[更新前证据](../../{c['old']['snapshot']})", "",
                      f"> {c['old']['quote'].replace(chr(10), chr(10) + '> ')}", "",
                      f"**新认知**：{c['new']['claim']}", ""])
        for evidence in c["new"]["evidence"]:
            lines.extend([f"来源：[证据原文](../../{urlquote(evidence['path'], safe='/')}) · "
                          f"[本次证据快照](../../{evidence['snapshot']})", "",
                          f"> {evidence['quote'].replace(chr(10), chr(10) + '> ')}", ""])
        lines.extend([f"**判断依据**：{c['rationale']}", "", f"**影响**：{c['impact']}", "",
                      f"**待确认**：{c['question']}", "",
                      "可回复记录编号，并说：已读 / 接受新观点 / 保留争议 / 稍后处理。", ""])
    return "\n".join(lines)


def prepare(root, target, limit=20, dry_run=False):
    target = required(target, "delivery target key")
    if not 1 <= limit <= 100:
        raise ValueError("limit must be between 1 and 100")
    state = load(root)
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
    if not dry_run:
        # Supersede unacknowledged obsolete drafts; keep them for audit.
        for draft in state["digests"].values():
            if draft["target"] == target and draft["status"] == "prepared" and draft["id"] != ident:
                draft["status"] = "superseded"
        atomic_write(safe(root, relative), text)
        if ident not in state["digests"]:
            state["digests"][ident] = {"id": ident, "target": target, "versions": versions,
                                      "reminders": reminders,
                                      "path": relative, "status": "prepared", "created": now()}
        else:
            state["digests"][ident]["status"] = "prepared"
        save(root, state)
    return {"id": ident, "target": target, "path": relative, "text": text, "versions": versions,
            "empty": False, "notify": True, "dry_run": dry_run, "status": "prepared"}


def acknowledge(root, ident, receipt):
    required(receipt, "native delivery receipt or verified delivery evidence")
    state = load(root)
    draft = state["digests"].get(ident)
    if draft is None:
        raise ValueError("Unknown digest id")
    if draft["status"] == "superseded":
        raise ValueError("Draft was superseded; prepare a current digest before delivery")
    delivered = state["delivered"].setdefault(draft["target"], {})
    for item, revision in draft["versions"].items():
        delivered[item] = max(delivered.get(item, 0), revision)
    reminded = state.setdefault("reminded", {}).setdefault(draft["target"], {})
    for item, reminder in draft.get("reminders", {}).items():
        reminded[item] = max(reminded.get(item, 0), reminder)
    draft.update(status="delivered", receipt=receipt, delivered_at=now())
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
    days = days or ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
    if not isinstance(days, list) or not set(days) <= {"mon", "tue", "wed", "thu", "fri", "sat", "sun"}:
        raise ValueError("Invalid weekdays")
    ident = digest(canonical([str(root), name, target]).encode())[:24]
    prompt = (
        f"Maintain the cognition briefing for the LLM Wiki at {root}. "
        "Read wiki-purpose.md, wiki-schema.md and the installed briefing skill at "
        ".llm-wiki/runtime/operations/briefing/SKILL.md. Use this vault only. "
        "Run local sync, then inspect all pending review batches and their before/after checkpoints. "
        "Read saved evidence and use semantic judgment to distinguish contradictions, updates, "
        "and differences in date, version or scope. Preserve old quotations and source snapshots; "
        "record evidence-backed cognition items before completing each review batch. "
        f"Prepare a digest for delivery target {target!r}. "
        "Stay quiet if there is no new actionable material. Do not emit a routine success report. "
        "Deliver through the user's configured native channel only. A generated digest is not a delivery: "
        "acknowledge it only with an actual delivery receipt or verified native run delivery status. "
        "Reuse its digest id for idempotent retries. Do not infer that the user has read it. "
        "Do not fetch external sources or create additional jobs without user authorization. "
        "Report material failures or required user action through the configured channel."
    )
    return {"id": ident, "name": name, "times": sorted(set(times)), "timezone": timezone_name,
            "timezone_validation": zone_validation, "days": days, "target": target, "prompt": prompt,
            "state": "planned", "requires": ["native_scheduler", "authorized_delivery_channel",
                                                 "no_change_suppression", "delivery_confirmation"]}


def bind_schedule(root, plan, host, job_ids, status="active"):
    if status not in ("active", "paused", "unavailable"):
        raise ValueError("status must be active, paused, or unavailable")
    checked = schedule_plan(root, plan["name"], plan["times"], plan["timezone"], plan["target"], plan.get("days"))
    required(host, "native scheduler identity")
    if status != "unavailable" and (not isinstance(job_ids, list) or not job_ids or
                                   any(not isinstance(j, str) or not j.strip() for j in job_ids)):
        raise ValueError("Native scheduler job ids are required; a plan is not a running job")
    state = load(root)
    checked.update(host=host, job_ids=job_ids, state=status, updated=now())
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
