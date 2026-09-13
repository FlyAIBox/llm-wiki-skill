"""Internal JSON request adapter, invoked by an agent; no installed CLI command.

Read one request from stdin, or from the single supplied UTF-8 JSON file. Return
one JSON response (or text for skill_show). No network, model or scheduler calls.
"""
from pathlib import Path
import json
import sys

sys.dont_write_bytecode = True  # Read-only invocations must not create runtime caches.
if sys.version_info < (3, 11):
    print(json.dumps({"ok": False, "error": "Python 3.11+ is required; select an available compatible interpreter."}))
    sys.exit(1)

from wiki_core import vault_root, writer, checkpoint
import wiki_analysis as analysis
import wiki_cognition as cognition
import wiki_setup as setup
import wiki_links as links
import wiki_ledger as ledger
import wiki_delivery as delivery


def execute(request):
    if not isinstance(request, dict):
        raise ValueError("Request must be a JSON object")
    op = request.get("op")
    if op == "skill_list":
        return setup.skill_list()
    if op == "skill_show":
        return setup.skill_show(request["name"])
    if op == "init":
        if not request.get("root"):
            raise ValueError("An explicit destination root is required for initialization")
        root = Path(request["root"]).expanduser().resolve()
        with writer(root):
            return setup.init(root, request["purpose"], request.get("name", "My Wiki"),
                              request.get("language", "zh-CN"), request.get("targets"))
    root = vault_root(request.get("root"))
    functions = {
        "search": lambda: analysis.search(root, request["query"], request.get("limit", 10), request.get("include_raw", False)),
        "graph": lambda: analysis.graph(root),
        "status": lambda: analysis.status(root),
        "coverage": lambda: analysis.source_coverage(root),
        'links': lambda: links.audit(root),
        'links_repair': lambda: links.repair(root, request.get('dry_run', True)),
        'source_progress': lambda: ledger.progress(root, request.get('source'), request.get('units')),
        'question': lambda: ledger.question(root, request.get('question'), request.get('id'),
                                            request.get('status', 'open'), request.get('note'), request.get('pages')),
        'relation': lambda: ledger.relation(root, request.get('subject'), request.get('predicate'),
                                            request.get('object'), request.get('evidence'), request.get('scope')),
        "source_review": lambda: analysis.source_review(root, request["source"],
                                                        request["outcome"], request["reason"]),
        "sync": lambda: analysis.sync(root, request.get("dry_run", False)),
        "index": lambda: analysis.rebuild_index(root),
        "checkpoint": lambda: checkpoint(root),
        "review_list": lambda: analysis.review(root),
        "review_complete": lambda: analysis.review(root, request["id"], request["note"]),
        "skill_install": lambda: setup.skill_install(root, request.get("targets"), request.get("dry_run", False)),
        "source_import": lambda: setup.source_import(root, request["source"], request.get("source_url")),
        "raw_view": lambda: setup.raw_view(root, request["source"], request["text"]),
        "cognition_list": lambda: cognition.cognition_list(root),
        "cognition_record": lambda: cognition.record(root, request.get("checkpoint"), request.get("old"), request["new"],
                                                     request["topic"], request["kind"], request["impact"],
                                                     request["question"], request["rationale"], request.get("id"),
                                                     request.get('confidence'), request.get('scope')),
        "cognition_feedback": lambda: cognition.feedback(root, request["id"], request["action"], request.get("note"), request.get("until"), request.get('revision')),
        "digest_prepare": lambda: cognition.prepare(root, request["target"], request.get("limit", 20), request.get("dry_run", False)),
        "digest_ack": lambda: cognition.acknowledge(root, request["id"], request["receipt"]),
        'digest_attempt': lambda: cognition.delivery_attempt(root, request['id'], request['host'], request['run_id']),
        'digest_failed': lambda: cognition.delivery_failed(root, request['attempt_id'], request['evidence']),
        'delivery_pending': lambda: cognition.pending_deliveries(root, request.get('target')),
        'digest_reconcile': lambda: delivery.reconcile_codex(root, request['session_path'], request['thread_id'],
                                                            request.get('id'), request.get('legacy_message_id')),
        "schedule_plan": lambda: cognition.schedule_plan(root, request["name"], request["times"], request["timezone"],
                                                         request["target"], request.get("days")),
        "schedule_bind": lambda: cognition.bind_schedule(root, request["plan"], request["host"], request.get("job_ids", []), request.get("status", "active"), request.get('verification')),
    }
    if op not in functions:
        raise ValueError("Unknown helper operation: " + str(op))
    readonly = op in ("search", "graph", "status", "coverage", "review_list", "cognition_list", "schedule_plan")
    readonly |= op in ("sync", "skill_install", "digest_prepare") and request.get("dry_run", False)
    readonly |= op in ('links', 'delivery_pending')
    readonly |= op == 'links_repair' and request.get('dry_run', True)
    readonly |= op == 'source_progress' and request.get('source') is None
    readonly |= op == 'question' and request.get('question') is None and request.get('id') is None
    readonly |= op == 'relation' and request.get('subject') is None
    if readonly:
        return functions[op]()
    with writer(root):
        return functions[op]()


def main():
    for stream in (sys.stdin, sys.stdout):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    try:
        if len(sys.argv) > 2:
            raise ValueError("Supply one JSON request file or a JSON object on stdin")
        payload = Path(sys.argv[1]).read_text(encoding="utf-8") if len(sys.argv) == 2 else sys.stdin.read()
        request = json.loads(payload)
        result = execute(request)
        if request.get("format") == "text" and request.get("op") == "skill_show":
            print(result["content"], end="")
        else:
            print(json.dumps({"ok": True, "result": result}, ensure_ascii=False, indent=2))
        return 0
    except (ValueError, KeyError, TypeError, OSError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False))
        return 1


if __name__ == "__main__":
    sys.exit(main())
