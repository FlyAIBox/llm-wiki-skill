"""Vault initialization, immutable source capture and skill installation."""
import json
import os
from pathlib import Path
import re

from wiki_core import (BUNDLE, OPERATIONS, VERSION, atomic_write, canonical, digest,
                       log, now, read_json, safe, write_json)


def template(name, **values):
    text = (BUNDLE / "templates" / name).read_text(encoding="utf-8")
    for key, value in values.items():
        text = text.replace("{{" + key + "}}", str(value))
    return text


def skill_list():
    return {"skills": [{"name": n, "content": f"operations/{n}/SKILL.md"} for n in OPERATIONS]}


def skill_show(name):
    if name not in OPERATIONS:
        raise ValueError("Unknown operation skill: " + name)
    return {"name": name, "content": (BUNDLE / "operations" / name / "SKILL.md").read_text(encoding="utf-8")}


def skill_install(root, targets=None, dry_run=False):
    """Preflight the entire install; never overwrite unowned or modified files."""
    if targets is None:
        targets = [str(safe(root, ".claude/skills")), str(safe(root, ".agents/skills"))]
    if not isinstance(targets, list) or not targets:
        raise ValueError("targets must be a nonempty list of confirmed skill directories")
    runtime = safe(root, ".llm-wiki/runtime")
    proposed = {}
    for folder in ("scripts", "templates", "references", "operations"):
        for p in sorted((BUNDLE / folder).rglob("*")):
            if p.is_file() and not p.is_symlink() and "__pycache__" not in p.parts:
                proposed[safe(root, ".llm-wiki/runtime/" + p.relative_to(BUNDLE).as_posix())] = p.read_bytes()
    for name in ("SKILL.md", "SKILL.zh-CN.md"):
        proposed[safe(root, ".llm-wiki/runtime/" + name)] = (BUNDLE / name).read_bytes()
    resolved_targets = []
    for location in targets:
        target = Path(location).expanduser().absolute()
        if target.is_symlink():
            raise ValueError("Skill installation target is a symlink")
        # Resolve the explicitly selected root (including OS aliases such as /var).
        # Symlinks below that root are rejected before writing operation folders.
        target = target.resolve()
        if target.is_relative_to(runtime):
            raise ValueError("Operation skills cannot be installed inside their runtime")
        resolved_targets.append(str(target))
        for name in OPERATIONS:
            path = target / name / "SKILL.md"
            if path.is_symlink() or path.parent.is_symlink():
                raise ValueError("Skill target is a symlink")
            try:
                link = Path(os.path.relpath(runtime, path.parent)).as_posix()
            except ValueError:  # Windows: different drives need an absolute link.
                link = runtime.as_posix()
            content = skill_show(name)["content"].replace("../../", link + "/")
            content = re.sub(r"\]\(([^)\n]+)\)",
                             lambda m: "](<" + m.group(1) + ">)" if " " in m.group(1) else m.group(0), content)
            proposed[path] = content.encode("utf-8")
    manifest_path = safe(root, ".llm-wiki/install-manifest.json")
    manifest = read_json(manifest_path, {"files": {}})
    planned, conflicts = [], []
    for path, data in proposed.items():
        prior = manifest["files"].get(str(path))
        if path.exists():
            if not path.is_file():
                conflicts.append(str(path))
                continue
            current = digest(path.read_bytes())
            if current == digest(data):
                continue
            if not prior or current != prior:
                conflicts.append(str(path))
                continue
        planned.append(str(path))
    if conflicts:
        raise ValueError("Installation would overwrite user-owned or edited files: " + ", ".join(conflicts))
    if not dry_run:
        for path, data in proposed.items():
            if str(path) in planned:
                atomic_write(path, data)
            manifest["files"][str(path)] = digest(data)
        manifest.update(version=VERSION, targets=resolved_targets)
        write_json(manifest_path, manifest)
    return {"targets": resolved_targets, "skills": list(OPERATIONS),
            "files_to_write": planned, "dry_run": dry_run, "runtime": str(runtime)}


def init(root, purpose, name="My Wiki", language="zh-CN", targets=None):
    if not isinstance(purpose, str) or not purpose.strip():
        raise ValueError("Supply a purpose written from the user's stated goals")
    config_path = safe(root, ".llm-wiki/config.toml")
    if config_path.exists():
        return {"root": str(root), "already_initialized": True,
                "message": "Existing vault preserved; use skill_install to refresh operation skills."}
    for name_in_root in ("wiki-purpose.md", "wiki-schema.md", "wiki-agent.md", "wiki-log.md", "wiki", "sources"):
        if safe(root, name_in_root).exists():
            raise ValueError(f"Initialization target already contains {name_in_root}; choose an empty vault")
    # Install preflight happens before creating any user-visible vault files.
    skill_install(root, targets, True)
    for folder in ("wiki/raw", "wiki/entities", "wiki/concepts", "wiki/comparisons",
                   "wiki/queries", "wiki/assets", "sources", ".llm-wiki/digests"):
        safe(root, folder).mkdir(parents=True, exist_ok=True)
    atomic_write(safe(root, "wiki-purpose.md"), purpose.rstrip() + "\n")
    atomic_write(safe(root, "wiki-schema.md"), template("wiki-schema.md"))
    atomic_write(safe(root, "wiki-agent.md"), template("wiki-agent.md"))
    atomic_write(safe(root, "wiki-log.md"), "# Wiki Log\n\nAppend-only operation history.\n")
    atomic_write(safe(root, "wiki/index.md"), "# Wiki Index\n\nNo knowledge pages yet.\n")
    for bootstrap in ("CLAUDE.md", "AGENTS.md"):
        target = safe(root, bootstrap)
        block = template("bootstrap.md")
        existing = target.read_text(encoding="utf-8") if target.exists() else ""
        if "<!-- llm-wiki:begin -->" not in existing:
            atomic_write(target, existing.rstrip() + ("\n\n" if existing else "") + block)
    skill_install(root, targets)
    write_json(safe(root, ".llm-wiki/source-manifest.json"), {"files": {}})
    # Config is the final initialized-vault marker.
    atomic_write(config_path, "[vault]\nname = " + json.dumps(name, ensure_ascii=False)
                 + "\nlanguage = " + json.dumps(language) + '\nschema_version = "3"\n'
                 + "\n# Briefing schedules appear only after a native scheduler confirms them.\n")
    log(root, "init", name)
    return {"root": str(root), "created": True, "skills": list(OPERATIONS),
            "scheduling": "not_configured"}


def source_import(root, source, source_url=None):
    original = Path(source).expanduser().absolute()
    if original.is_symlink():
        raise ValueError("Source input must not be a symlink")
    original = original.resolve()
    if not original.exists():
        raise ValueError("Source input does not exist")
    if original.is_dir() and root.is_relative_to(original):
        raise ValueError("Source folder cannot contain the destination vault")
    if any(original.is_relative_to(root / p) for p in ("sources", "wiki", ".llm-wiki")):
        raise ValueError("Source already inside vault storage; reuse its registered path")
    inputs = []
    if original.is_file():
        inputs = [(original.name, original)]
    else:
        for directory, dirs, names in os.walk(original, followlinks=False):
            dirs[:] = sorted(d for d in dirs if not d.startswith("."))
            for n in dirs + names:
                if (Path(directory) / n).is_symlink():
                    raise ValueError("Source folder contains a symlink; select regular files explicitly")
            for n in sorted(names):
                if not n.startswith("."):
                    p = Path(directory) / n
                    inputs.append((p.relative_to(original).as_posix(), p))
    if not inputs:
        raise ValueError("No regular non-hidden source files found")
    content = {relative: p.read_bytes() for relative, p in inputs}
    batch = digest(canonical({k: digest(v) for k, v in content.items()}).encode())[:24]
    manifest_path = safe(root, ".llm-wiki/source-manifest.json")
    manifest = read_json(manifest_path, {"files": {}})
    previous = {e["relative"]: path for path, e in manifest["files"].items() if e["batch"] == batch}
    if set(previous) == set(content):
        for rel, path in previous.items():
            if digest(safe(root, path).read_bytes()) != digest(content[rel]):
                raise ValueError("Registered immutable source was modified: " + path)
            origin = {"original_path": str(dict(inputs)[rel]), "source_url": source_url}
            entry = manifest["files"][path]
            origins = entry.setdefault("origins", [{"original_path": entry["original_path"],
                                                     "source_url": entry.get("source_url")}])
            if origin not in origins:
                origins.append(origin)
        write_json(manifest_path, manifest)
        captured = list(previous.values())
        raw_views, extraction_needed = reading_copies(root, captured, manifest)
        return {"duplicate": True, "sources": captured, "batch": batch,
                "raw_views": raw_views, "extraction_needed": extraction_needed}
    base = f"sources/{now()[:10]}/{batch}"
    captured = []
    for rel in content:
        safe(root, f"{base}/{rel}")
        safe(root, f"wiki/raw/{batch}/{rel}.md")
    for rel, p in inputs:
        relative = f"{base}/{rel}"
        target = safe(root, relative)
        data = content[rel]
        if target.exists() and target.read_bytes() != data:
            raise ValueError("Immutable source collision: " + relative)
        if not target.exists():
            atomic_write(target, data)
        manifest["files"][relative] = {"sha256": digest(data), "size": len(data), "batch": batch,
                                      "relative": rel, "original_path": str(p), "captured": now(),
                                      "source_url": source_url}
        captured.append(relative)
    write_json(manifest_path, manifest)
    raw_views, extraction_needed = reading_copies(root, captured, manifest)
    log(root, "capture", f"{len(captured)} originals, batch {batch}")
    return {"batch": batch, "sources": captured, "raw_views": raw_views,
            "extraction_needed": extraction_needed, "duplicate": False}


def reading_copies(root, captured, manifest):
    """Recover missing derived views after interruption; preserve existing ones."""
    raw_views, extraction_needed = [], []
    for relative in captured:
        source_path = safe(root, relative)
        entry = manifest["files"][relative]
        output = f"wiki/raw/{entry['batch']}/{entry['relative']}.md"
        if safe(root, output).is_file():
            raw_views.append(output)
            continue
        if source_path.suffix.lower() in (".md", ".txt", ".markdown"):
            try:
                text = source_path.read_text(encoding="utf-8")
            except UnicodeError:
                extraction_needed.append(relative)
                continue
            if not text.strip():
                extraction_needed.append(relative)
                continue
            raw_views.append(raw_view(root, relative, text)["path"])
        else:
            extraction_needed.append(relative)
    return raw_views, extraction_needed


def raw_view(root, source, text):
    manifest = read_json(safe(root, ".llm-wiki/source-manifest.json"), {"files": {}})
    entry = manifest["files"].get(source)
    if entry is None or digest(safe(root, source).read_bytes()) != entry["sha256"]:
        raise ValueError("Raw view requires a registered, unchanged source")
    if not isinstance(text, str) or not text.strip():
        raise ValueError("Extraction must contain actual text")
    # A full extension is kept (x.pdf.md / x.md.md) to avoid colliding formats.
    output = f"wiki/raw/{entry['batch']}/{entry['relative']}.md"
    target = safe(root, output)
    def link(match):
        value = match.group(1)
        if re.match(r"[a-zA-Z][\w+.-]*:", value) or value.startswith(("#", "/")):
            return match.group(0)
        original_target = (safe(root, source).parent / value).resolve()
        if original_target.is_relative_to(root / "sources") and original_target.is_file():
            return "](" + Path(os.path.relpath(original_target, target.parent)).as_posix() + ")"
        return match.group(0)
    text = re.sub(r"\]\(([^\s)]+)\)", link, text)
    head = {"title": Path(source).name, "description": "Extracted reading copy; see immutable source.",
            "type": "raw", "sources": [source], "source_sha256": entry["sha256"],
            "tags": [], "created": now()[:10], "updated": now()[:10]}
    document = "---\n" + "\n".join(k + ": " + json.dumps(v, ensure_ascii=False) for k, v in head.items())
    document += "\n---\n\n" + text.rstrip() + "\n"
    atomic_write(target, document)
    return {"path": output, "source": source, "sha256": digest(document.encode("utf-8"))}
