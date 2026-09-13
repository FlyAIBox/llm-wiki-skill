"""Audit ordinary Markdown navigation and repair captured cross-batch reading links."""
import os
import re
from pathlib import Path
from urllib.parse import quote, unquote, urlsplit

from wiki_core import atomic_write, digest, files, frontmatter, read_json, safe, snapshot, write_json
from wiki_evidence import source_bytes


def links(text):
    # Mask examples while retaining positions and line numbers for surgical edits.
    masked = re.sub(r'(?ms)^\s*(`{3,}|~{3,})[^\n]*\n.*?^\s*\1\s*$|<!--.*?-->|`[^`\n]*`',
                    lambda m: re.sub(r'[^\n]', ' ', m.group()), text)
    patterns = [r'!?\[[^\]\n]*\]\(\s*(<[^>\n]+>|(?:\\.|[^\\()\s]|\([^()\n]*\))+)(?:\s+[^\n)]*)?\)',
                r'(?m)^\s{0,3}\[(?!\^)[^\]\n]+\]:\s*(<[^>\n]+>|\S+)']
    found = []
    for pattern in patterns:
        for match in re.finditer(pattern, masked):
            value = text[match.start(1):match.end(1)].strip('<>')
            if urlsplit(value).scheme or value.startswith('//'):
                continue
            found.append({'target': value, 'start': match.start(1), 'end': match.end(1),
                          'line': text.count('\n', 0, match.start()) + 1})
    return sorted(found, key=lambda item: item['start'])


def anchors(text):
    result = set(re.findall(r'(?:id|name)=["\']([^"\']+)["\']', text))
    counts = {}
    for line in text.splitlines():
        match = re.match(r'^\s{0,3}#{1,6}\s+(.+?)\s*#*$', line)
        if match:
            title = re.sub(r'\[([^\]]+)\]\([^)]*\)', r'\1', match[1]).strip().lower()
            slug = re.sub(r'[^\w\- ]', '', title).replace(' ', '-')
            number = counts.get(slug, 0)
            result.add(slug + (f'-{number}' if number else ''))
            counts[slug] = number + 1
    return result


def view_manifest(root, path, source, document, **extra):
    _, entry = source_bytes(root, source)
    manifest_path = safe(root, '.llm-wiki/raw-manifest.json')
    manifest = read_json(manifest_path, {'files': {}})
    manifest['files'][path] = {'source': source, 'source_sha256': entry['sha256'],
                             'sha256': digest(document.encode()), **extra}
    write_json(manifest_path, manifest)


def origin_matches(root, source, value, manifest):
    """Match original full paths, never a coincidentally matching basename."""
    entry = manifest[source]
    expected = {(Path(origin['original_path']).parent / value).resolve()
                for origin in [entry, *entry.get('origins', [])]}
    candidates = []
    for captured, other in manifest.items():
        if any(Path(origin['original_path']).resolve() in expected
               for origin in [other, *other.get('origins', [])]):
            candidates.append(captured)
    same_batch = [p for p in candidates if manifest[p]['batch'] == entry['batch']]
    candidates = same_batch or candidates
    if len({manifest[p]['sha256'] for p in candidates}) > 1:
        return None  # Multiple captured versions: agent must select the intended version.
    return sorted(candidates)[0] if candidates else None


def repair(root, dry_run=True):
    manifest = read_json(safe(root, '.llm-wiki/source-manifest.json'), {'files': {}})['files']
    changes = []
    for source, entry in manifest.items():
        relative = f"wiki/raw/{entry['batch']}/{entry['relative']}.md"
        path = safe(root, relative)
        if not path.is_file():
            continue
        source_bytes(root, source)
        text = path.read_text(encoding='utf-8')
        owned = read_json(safe(root, '.llm-wiki/raw-manifest.json'), {'files': {}})['files'].get(relative)
        if owned and owned['sha256'] != digest(text.encode()):
            raise ValueError('Reading copy changed outside raw_view; review it before repairing links: ' + relative)
        replacements = []
        for link in links(text):
            split = urlsplit(link['target'])
            value = unquote(split.path)
            if not value or value.startswith('/'):
                continue
            current = (path.parent / value).resolve()
            if current.is_relative_to(root) and current.is_file():
                continue
            captured = origin_matches(root, source, value, manifest)
            if captured:
                other = manifest[captured]
                reading = safe(root, f"wiki/raw/{other['batch']}/{other['relative']}.md")
                target = reading if reading.is_file() else safe(root, captured)
                destination = quote(Path(os.path.relpath(target, path.parent)).as_posix(), safe='/')
                if split.fragment:
                    destination += '#' + split.fragment
                replacements.append((link, destination))
        if replacements:
            updated = text
            for link, destination in reversed(replacements):
                updated = updated[:link['start']] + destination + updated[link['end']:]
            changes.append({'path': relative, 'links_repaired': len(replacements)})
            if not dry_run:
                backup = snapshot(root, text.encode())
                atomic_write(path, updated)
                if owned:
                    view_manifest(root, relative, source, updated, before_link_repair=backup)
    return {'dry_run': dry_run, 'changes': changes,
            'links_repaired': sum(item['links_repaired'] for item in changes)}


def audit(root):
    issues = []
    total = 0
    for path in files(root, 'wiki'):
        if path.suffix.lower() != '.md':
            continue
        relative = path.relative_to(root).as_posix()
        text = path.read_text(encoding='utf-8')
        for link in links(text):
            split = urlsplit(link['target'])
            value = unquote(split.path)
            total += 1
            target = (path.parent / value).resolve() if value else path
            issue = None
            if not target.is_relative_to(root):
                issue = 'outside_vault'
            elif not target.is_file():
                issue = 'missing_file'
            elif split.fragment and target.suffix.lower() == '.md':
                if unquote(split.fragment) not in anchors(target.read_text(encoding='utf-8')):
                    issue = 'missing_anchor'
            if issue:
                issues.append({'path': relative, 'line': link['line'], 'target': link['target'], 'issue': issue})
    return {'links_checked': total, 'issues': issues, 'navigation_complete': not issues,
            'scope': 'wiki Markdown inline/reference links and heading anchors; sources remain immutable'}
