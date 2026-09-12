"""Local retrieval, graph analysis and auditable change tracking."""
from collections import Counter, defaultdict
from datetime import date
import math
from pathlib import PurePosixPath
import re

from wiki_core import (canonical, checkpoint, digest, files, is_knowledge, log,
                       now, pages, read_json, safe, write_json, atomic_write)


def tokens(text):
    result = []
    for word in re.findall(r"[\u3400-\u9fff\u3040-\u30ff\uac00-\ud7af]+|[^\W_]+", text.casefold()):
        if re.match(r"[\u3400-\u9fff\u3040-\u30ff\uac00-\ud7af]", word):
            result.extend(word)
            result.extend(word[i:i + 2] for i in range(len(word) - 1))
        else:
            result.append(word)
    return result


def search(root, query, limit=10, include_raw=False):
    if not str(query).strip() or not 1 <= limit <= 100:
        raise ValueError("A nonempty query and limit between 1 and 100 are required")
    docs = pages(root, include_raw)
    counts = [Counter(tokens(p["title"] + " " + str(p["meta"].get("description", ""))
                            + " " + p["body"])) for p in docs]
    lengths = [sum(c.values()) for c in counts]
    avg = sum(lengths) / len(lengths) if lengths else 1
    df = Counter(t for c in counts for t in c)
    terms = set(tokens(query))
    results = []
    for p, c, length in zip(docs, counts, lengths):
        score = 0.0
        for term in terms:
            freq = c[term]
            if freq:
                idf = math.log(1 + (len(docs) - df[term] + .5) / (df[term] + .5))
                score += idf * freq * 2.2 / (freq + 1.2 * (.25 + .75 * length / (avg or 1)))
        if score:
            lines = p["body"].splitlines()
            best = max(lines, key=lambda s: len(terms & set(tokens(s))), default="")
            results.append({"path": p["path"], "title": p["title"], "score": round(score, 6),
                            "excerpt": best[:400], "sources": p["meta"].get("sources", [])})
    results.sort(key=lambda p: (-p["score"], p["path"]))
    return {"mode": "local_bm25", "semantic_reranking": "agent_required",
            "pages_scanned": len(docs), "results": results[:limit]}


def link_targets(text):
    # Ignore fenced/inline code, comments and escaped literal examples.
    text = re.sub(r"(?ms)^\s*(`{3,}|~{3,})[^\n]*\n.*?^\s*\1\s*$", "", text)
    text = re.sub(r"<!--.*?-->|`[^`\n]*`", "", text, flags=re.S)
    return [m.group(1).split("|", 1)[0].strip()
            for m in re.finditer(r"(?<![\\!])\[\[([^\]\n]+)\]\]", text)]


def graph(root):
    docs = pages(root)
    slugs = {p["slug"] for p in docs}
    aliases = defaultdict(set)
    for p in docs:
        candidates = p["meta"].get("aliases", [])
        if not isinstance(candidates, list):
            candidates = []
        for name in [p["slug"], PurePosixPath(p["slug"]).name, p["title"], *candidates]:
            aliases[str(name).casefold()].add(p["slug"])
    edges, wanted, ambiguous = set(), defaultdict(set), []
    for p in docs:
        for target in link_targets(p["body"]):
            target = target.split("#", 1)[0].strip()
            if not target:
                continue  # In-page anchor.
            if target.endswith(".md"):
                target = target[:-3]
            if target.startswith("wiki/"):
                target = target[5:]
            target = target.removeprefix("/")
            if target.startswith(("raw/", "assets/", "_archive/")) or target == "index":
                continue
            # Normalize a relative wikilink without letting it escape wiki/.
            if target.startswith("."):
                parts = list(PurePosixPath(p["slug"]).parent.parts)
                valid = True
                for part in PurePosixPath(target).parts:
                    if part == "..":
                        if not parts:
                            valid = False
                            break
                        parts.pop()
                    elif part != ".":
                        parts.append(part)
                target = "/".join(parts) if valid else target
            choices = {target} if target in slugs else aliases.get(target.casefold(), set())
            if len(choices) == 1:
                other = next(iter(choices))
                if p["slug"] != other:
                    edges.add((p["slug"], other))
            elif len(choices) > 1:
                ambiguous.append({"from": p["slug"], "target": target, "candidates": sorted(choices)})
            else:
                wanted[target].add(p["slug"])
    incoming, outgoing = Counter(b for a, b in edges), Counter(a for a, b in edges)
    neighbors = {s: set() for s in slugs}
    for a, b in edges:
        neighbors[a].add(b)
        neighbors[b].add(a)
    # Deterministic asynchronous label propagation; retain labels on ties.
    labels = {s: s for s in slugs}
    rounds, changed = 0, True
    while changed and rounds < 100:
        changed = False
        rounds += 1
        for s in sorted(slugs):
            votes = Counter(labels[n] for n in neighbors[s])
            if not votes:
                continue
            highest = max(votes.values())
            best = sorted(k for k, v in votes.items() if v == highest)
            label = labels[s] if labels[s] in best else best[0]
            changed |= labels[s] != label
            labels[s] = label
    groups = defaultdict(list)
    for s in sorted(slugs):
        groups[labels[s]].append(s)
    hubs = [{"page": s, "incoming": incoming[s], "outgoing": outgoing[s],
             "degree": incoming[s] + outgoing[s]} for s in slugs]
    hubs.sort(key=lambda h: (-h["degree"], h["page"]))
    return {"nodes": sorted(slugs), "edges": [list(e) for e in sorted(edges)],
            "communities": sorted(groups.values(), key=lambda g: (-len(g), g)),
            "community_method": "deterministic_label_propagation", "converged": not changed,
            "hubs": hubs[:10], "orphans": sorted(s for s in slugs if not incoming[s]),
            "wanted": [{"page": k, "referenced_by": sorted(v)} for k, v in sorted(wanted.items())],
            "ambiguous_links": ambiguous}


def sync(root, dry_run=False):
    state_path = safe(root, ".llm-wiki/sync-state.json")
    state = read_json(state_path, {"entries": {}, "reviews": []})
    current = {}
    for subtree in ("wiki", "sources"):
        for p in files(root, subtree):
            data = p.read_bytes()
            stat = p.stat()
            current[p.relative_to(root).as_posix()] = {
                "mtime_ns": stat.st_mtime_ns, "size": len(data), "sha256": digest(data)}
    before = state.get("entries", {})
    added = sorted(current.keys() - before.keys())
    deleted = sorted(before.keys() - current.keys())
    modified = sorted(p for p in current.keys() & before.keys()
                      if current[p]["sha256"] != before[p]["sha256"])
    result = {"added": added, "modified": modified, "deleted": deleted,
              "unchanged": len(current) - len(added) - len(modified), "dry_run": dry_run,
              "previous_checkpoint": state.get("checkpoint"), "remote_sync": False}
    if not dry_run:
        cp = checkpoint(root)
        if any(path not in current or entry["sha256"] != current[path]["sha256"]
               for path, entry in cp["pages"].items()) or any(
                   is_knowledge(path) and path not in cp["pages"] for path in current):
            raise ValueError("Knowledge changed during sync; retry after other writers finish")
        changed_pages = [p for p in added + modified + deleted if is_knowledge(p)]
        reviews = state.get("reviews", [])
        if changed_pages:
            key = digest(canonical([state.get("checkpoint"), cp["id"], sorted(changed_pages)]).encode())[:24]
            if not any(r["id"] == key for r in reviews):
                reviews.append({"id": key, "before": state.get("checkpoint"), "after": cp["id"],
                                "pages": sorted(changed_pages), "status": "pending", "created": now()})
        write_json(state_path, {"entries": current, "checkpoint": cp["id"],
                                "reviews": reviews, "last_sync": now()})
        result["checkpoint"] = cp["id"]
        result["pending_reviews"] = sum(r["status"] == "pending" for r in reviews)
    return result


def review(root, ident=None, note=None):
    path = safe(root, ".llm-wiki/sync-state.json")
    state = read_json(path, {"reviews": []})
    if ident:
        batch = next((r for r in state["reviews"] if r["id"] == ident), None)
        if batch is None or not note or not note.strip():
            raise ValueError("Existing review id and a substantive completion note are required")
        batch.update(status="reviewed", note=note, reviewed=now())
        write_json(path, state)
    return {"pending": [r for r in state.get("reviews", []) if r["status"] == "pending"]}


def rebuild_index(root):
    docs = pages(root)
    lines = ["# Wiki Index", "", "> Generated catalog; page bodies remain agent-maintained.", ""]
    groups = defaultdict(list)
    for p in docs:
        groups[str(p["meta"].get("type", "other"))].append(p)
    for group, members in sorted(groups.items()):
        lines.extend(["## " + group, ""])
        for p in members:
            description = str(p["meta"].get("description", "")).replace("\n", " ")
            lines.append(f"- [[{p['slug']}|{p['title']}]] — {description}")
        lines.append("")
    atomic_write(safe(root, "wiki/index.md"), "\n".join(lines))
    log(root, "index", f"Cataloged {len(docs)} knowledge pages")
    return {"pages": len(docs), "path": "wiki/index.md"}


def status(root):
    docs = pages(root)
    g = graph(root)
    issues, signals = [], []
    for name in ("CLAUDE.md", "AGENTS.md", "wiki-purpose.md", "wiki-schema.md", "wiki-log.md", "wiki/index.md"):
        if not safe(root, name).is_file():
            issues.append({"path": name, "issue": "missing_file"})
    index = safe(root, "wiki/index.md")
    index_links = {t.split("#", 1)[0].removesuffix(".md") for t in
                   link_targets(index.read_text(encoding="utf-8"))} if index.exists() else set()
    types = Counter()
    for p in docs:
        meta = p["meta"]
        types[str(meta.get("type", "unknown"))] += 1
        for error in p["issues"]:
            issues.append({"path": p["path"], "issue": error})
        for key in ("title", "description", "type", "tags", "sources", "created", "updated"):
            if key not in meta:
                issues.append({"path": p["path"], "issue": "missing_" + key})
        for key in ("title", "description", "type"):
            if key in meta and (not isinstance(meta[key], str) or not meta[key].strip()):
                issues.append({"path": p["path"], "issue": "invalid_" + key})
        for key in ("created", "updated"):
            if key in meta:
                try:
                    date.fromisoformat(meta[key])
                except (ValueError, TypeError):
                    issues.append({"path": p["path"], "issue": "invalid_date_" + key})
        for key in ("tags", "sources", "aliases"):
            if key in meta and not isinstance(meta[key], list):
                issues.append({"path": p["path"], "issue": "expected_list_" + key})
            elif key in meta and any(not isinstance(v, str) or not v.strip() for v in meta[key]):
                issues.append({"path": p["path"], "issue": "expected_string_items_" + key})
        refs = meta.get("sources", [])
        if isinstance(refs, list):
            for ref in refs:
                try:
                    valid = safe(root, str(ref)).is_file()
                except ValueError:
                    valid = False
                if not valid:
                    issues.append({"path": p["path"], "issue": "missing_source", "source": ref})
            if not refs:
                signals.append({"path": p["path"], "signal": "no_evidence"})
        if p["slug"] not in index_links:
            issues.append({"path": p["path"], "issue": "missing_from_index"})
        if meta.get("confidence") == "low" or meta.get("contested") is True:
            signals.append({"path": p["path"], "signal": "needs_content_review"})
        if len(p["body"].splitlines()) > 200:
            signals.append({"path": p["path"], "signal": "consider_split"})
    source_manifest = read_json(safe(root, ".llm-wiki/source-manifest.json"), {"files": {}})
    registered = source_manifest.get("files", {})
    for path, entry in registered.items():
        source = safe(root, path)
        if not source.is_file() or digest(source.read_bytes()) != entry["sha256"]:
            issues.append({"path": path, "issue": "immutable_source_changed_or_missing"})
    source_files = files(root, "sources")
    for path in source_files:
        rel = path.relative_to(root).as_posix()
        if rel not in registered:
            signals.append({"path": rel, "signal": "unregistered_source"})
    cognition = read_json(safe(root, ".llm-wiki/cognition.json"), {"items": {}})
    return {"knowledge_pages": len(docs), "source_files": len(source_files), "types": dict(types),
            "raw_views": len(pages(root, True)) - len(docs), "issues": issues, "signals": signals,
            "graph": g, "changes": sync(root, True), "reviews": review(root),
            "open_conflicts": sum(i.get("decision") not in ("accepted_new", "dismissed")
                                  for i in cognition["items"].values()),
            "schedules": list(cognition.get("schedules", {}).values()),
            "semantic_audit": "agent_required"}
