"""Portable file primitives for the agent-operated LLM Wiki (Python 3.11+)."""
from __future__ import annotations

import contextlib
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import tempfile
import tomllib
from datetime import datetime, timezone

BUNDLE = Path(__file__).resolve().parent.parent
VERSION = "3.1.0"
OPERATIONS = ("ingest", "query", "lint", "research", "briefing")


def now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def digest(data):
    return hashlib.sha256(data).hexdigest()


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def safe(root, relative):
    """Only portable vault-relative paths; never follow symlinks."""
    root = Path(root).resolve()
    rel = PurePosixPath(str(relative))
    if rel.is_absolute() or not rel.parts or any(p in ("..", "") for p in rel.parts):
        raise ValueError(f"Expected a vault-relative path: {relative}")
    if "\\" in str(relative) or ":" in str(relative):
        raise ValueError(f"Use portable forward-slash paths: {relative}")
    result = root
    for part in rel.parts:
        result = result / part
        if result.is_symlink():
            raise ValueError(f"Symlink is outside this helper's file contract: {relative}")
    if not result.resolve().is_relative_to(root):
        raise ValueError(f"Path leaves vault: {relative}")
    return result


def atomic_write(path, content):
    path = Path(path)
    if path.is_symlink():
        raise ValueError(f"Refusing symlink: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    data = content.encode("utf-8") if isinstance(content, str) else content
    fd, tmp = tempfile.mkstemp(prefix=".wiki-", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def read_json(path, default=None):
    if not Path(path).exists():
        return {} if default is None else default
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write_json(path, value):
    atomic_write(path, json.dumps(value, ensure_ascii=False, indent=2) + "\n")


@contextlib.contextmanager
def writer(root):
    lock = safe(root, ".llm-wiki/write.lock")
    lock.parent.mkdir(parents=True, exist_ok=True)
    try:
        lock.mkdir()
    except FileExistsError:
        raise ValueError("Another writer holds .llm-wiki/write.lock. Retry after it finishes; "
                         "after a crash, verify no writer remains before removing the lock.") from None
    try:
        yield
    finally:
        lock.rmdir()


def vault_root(value=None):
    if value:
        root = Path(value).expanduser().resolve()
    elif os.environ.get("WIKI_PATH", "").strip():
        root = Path(os.environ["WIKI_PATH"]).expanduser().resolve()
    else:
        root = next((p for p in (Path.cwd(), *Path.cwd().parents)
                     if (p / ".llm-wiki/config.toml").is_file()), None)
        if root is None:
            raise ValueError("No vault selected. Supply root or WIKI_PATH; never guess another vault.")
    config = safe(root, ".llm-wiki/config.toml")
    if not config.is_file():
        raise ValueError(f"No initialized LLM Wiki at {root}")
    tomllib.loads(config.read_text(encoding="utf-8"))
    return root


def files(root, subtree):
    base = safe(root, subtree)
    if not base.exists():
        return []
    found = []
    for directory, dirs, names in os.walk(base, followlinks=False):
        for name in dirs + names:
            p = Path(directory) / name
            if p.is_symlink():
                raise ValueError(f"Symlink in scanned tree: {p.relative_to(root)}")
        dirs[:] = sorted(d for d in dirs if not d.startswith("."))
        found.extend(Path(directory) / n for n in sorted(names) if not n.startswith("."))
    return sorted(found)


def scalar(value):
    value = value.strip()
    if not value:
        return ""
    try:
        return json.loads(value)
    except ValueError:
        pass
    if value.startswith("[") and value.endswith("]"):
        return [scalar(v) for v in value[1:-1].split(",") if v.strip()]
    if len(value) >= 2 and value[0] == value[-1] == "'":
        return value[1:-1].replace("''", "'")
    return value


def frontmatter(text):
    """Read the deliberately small schema subset, flag unsupported YAML."""
    lines = text.lstrip("\ufeff").splitlines()
    if not lines or lines[0] != "---":
        return {}, text, ["missing_frontmatter"]
    try:
        end = lines.index("---", 1)
    except ValueError:
        return {}, text, ["unclosed_frontmatter"]
    meta, issues, current = {}, [], None
    for line in lines[1:end]:
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if line.startswith("  - ") and current and isinstance(meta[current], list):
            meta[current].append(scalar(line[4:]))
            continue
        match = re.fullmatch(r"([A-Za-z_][\w-]*):\s*(.*)", line)
        if not match:
            issues.append("unsupported_frontmatter: " + line)
            continue
        current, value = match.groups()
        if current in meta:
            issues.append("duplicate_frontmatter: " + current)
        if value in ("|", ">", "|-", ">-") or value.startswith(("&", "*", "!", "{")):
            issues.append("unsupported_frontmatter: " + current)
        meta[current] = scalar(value) if value else []
    return meta, "\n".join(lines[end + 1:]), issues


def is_knowledge(relative):
    p = PurePosixPath(relative)
    return (p.suffix.lower() == ".md" and p.parts[0] == "wiki"
            and p.name != "index.md" and len(p.parts) > 1
            and p.parts[1] not in ("raw", "assets", "_archive", "digests", "conflicts"))


def pages(root, include_raw=False):
    result = []
    for p in files(root, "wiki"):
        relative = p.relative_to(root).as_posix()
        if not (is_knowledge(relative) or (include_raw and relative.startswith("wiki/raw/")
                                         and p.suffix.lower() == ".md")):
            continue
        text = p.read_text(encoding="utf-8")
        meta, body, issues = frontmatter(text)
        result.append({"path": relative, "slug": relative[5:-3], "meta": meta,
                       "title": str(meta.get("title", p.stem)), "body": body,
                       "text": text, "issues": issues})
    return result


def log(root, action, subject):
    p = safe(root, "wiki-log.md")
    # The runner serializes all writes with writer().
    with p.open("a", encoding="utf-8") as stream:
        stream.write(f"\n## [{now()}] {action} | {str(subject).replace(chr(10), ' ')}\n")


def snapshot(root, data):
    sha = digest(data)
    p = safe(root, f".llm-wiki/snapshots/{sha}.md")
    if not p.exists():
        atomic_write(p, data)
    elif digest(p.read_bytes()) != sha:
        raise ValueError(f"Corrupt snapshot: {sha}")
    return {"sha256": sha, "snapshot": p.relative_to(root).as_posix()}


def checkpoint(root):
    entries = {p["path"]: snapshot(root, safe(root, p["path"]).read_bytes()) for p in pages(root)}
    ident = digest(canonical(entries).encode())[:24]
    target = safe(root, f".llm-wiki/checkpoints/{ident}.json")
    if not target.exists():
        write_json(target, {"id": ident, "created": now(), "pages": entries})
    return {"id": ident, "pages": entries}


def get_checkpoint(root, ident):
    if not re.fullmatch(r"[0-9a-f]{24}", ident):
        raise ValueError("Invalid checkpoint id")
    p = safe(root, f".llm-wiki/checkpoints/{ident}.json")
    if not p.is_file():
        raise ValueError("Checkpoint does not exist")
    return read_json(p)
