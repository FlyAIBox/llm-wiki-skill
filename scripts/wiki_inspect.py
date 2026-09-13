"""Read-only source inventory and exact quotation assistance."""
from bisect import bisect_right
import json

from wiki_core import digest, files, get_checkpoint, read_json, safe
from wiki_evidence import origin_hashes


def bounded_int(value, name, minimum, maximum):
    if type(value) is not int or not minimum <= value <= maximum:
        raise ValueError(f'{name} must be an integer from {minimum} to {maximum}')
    return value


def quote_document(root, path, checkpoint=None, side='new'):
    if side not in ('old', 'new'):
        raise ValueError('side must be old or new')
    safe(root, path)
    info = {'path': path, 'side': side, 'checkpoint': checkpoint}
    if side == 'old' and not checkpoint:
        raise ValueError('Old quotations require the pre-update checkpoint')
    if checkpoint:
        entry = get_checkpoint(root, checkpoint)['pages'].get(path)
        if entry is None:
            raise ValueError('Quotation page absent from checkpoint')
        data = safe(root, entry['snapshot']).read_bytes()
        if digest(data) != entry['sha256']:
            raise ValueError('Evidence snapshot hash mismatch')
        info['snapshot'] = entry['snapshot']
    else:
        data = safe(root, path).read_bytes()
    # Match the record API: old claims need an intact checkpoint; new evidence
    # additionally needs a verified chain to registered, unchanged origins.
    if side == 'new':
        info['origins'] = origin_hashes(root, path, data)
    info['sha256'] = digest(data)
    info['validation_scope'] = 'checkpoint_integrity' if side == 'old' else 'evidence_origins'
    try:
        return data.decode('utf-8'), info
    except UnicodeError as exc:
        raise ValueError('Quotation input is not UTF-8 text; extract a raw_view first') from exc


def quote_lookup(root, path, needle, checkpoint=None, side='new', limit=10,
                 context_lines=0, verify=False):
    if not isinstance(needle, str) or not needle.strip():
        raise ValueError('Nonempty quote or query is required')
    bounded_int(limit, 'limit', 1, 100)
    bounded_int(context_lines, 'context_lines', 0, 5)
    text, info = quote_document(root, path, checkpoint, side)
    # Keep decoded original line endings and Unicode unchanged, including Markdown.
    starts = [0] + [i + 1 for i, char in enumerate(text) if char == '\n']
    matches, seen, cursor, more = [], set(), 0, False
    while (position := text.find(needle, cursor)) >= 0:
        cursor = position + 1
        first = bisect_right(starts, position) - 1
        last = bisect_right(starts, position + len(needle) - 1) - 1
        if verify:
            begin, end = position, position + len(needle)
        else:
            first, last = max(0, first - context_lines), min(len(starts) - 1, last + context_lines)
            begin = starts[first]
            end = starts[last + 1] if last + 1 < len(starts) else len(text)
        if (begin, end) in seen:
            continue
        seen.add((begin, end))
        if len(matches) == limit:
            more = True
            break
        quote = text[begin:end]
        fields = {'page' if side == 'old' else 'path': path, 'quote': quote}
        if side == 'new' and checkpoint:
            fields['checkpoint'] = checkpoint
        matches.append({'quote': quote, 'quote_json': json.dumps(quote, ensure_ascii=False),
                        'line_start': first + 1, 'line_end': last + 1,
                        'start_char': begin, 'end_char': end, 'record_fields': fields})
    return {**info, 'matched': bool(matches), 'matches': matches, 'has_more': more,
            'offset_unit': 'unicode_codepoints', 'end_exclusive': True,
            'match_mode': 'exact_substring',
            'hint': None if matches else 'Use quote_find with a shorter literal keyword; preserve Markdown and line endings.'}


def source_list(root, query='', limit=50, offset=0):
    from wiki_analysis import source_coverage

    if not isinstance(query, str):
        raise ValueError('query must be a string')
    bounded_int(limit, 'limit', 1, 100)
    bounded_int(offset, 'offset', 0, 2**31 - 1)
    manifest = read_json(safe(root, '.llm-wiki/source-manifest.json'), {'files': {}})['files']
    actual = {p.relative_to(root).as_posix() for p in files(root, 'sources')}
    coverage = source_coverage(root)
    views = read_json(safe(root, '.llm-wiki/raw-manifest.json'), {'files': {}})['files']
    items = []
    for path in sorted(set(manifest) | actual):
        entry = manifest.get(path)
        origins = [] if entry is None else entry.get('origins', [
            {'original_path': entry.get('original_path'), 'source_url': entry.get('source_url')}])
        if query.casefold() not in json.dumps([path, origins], ensure_ascii=False).casefold():
            continue
        item = {'path': path, 'registration': 'registered' if entry else 'unregistered',
                'origins': origins, 'sha256': entry['sha256'] if entry else None}
        original = safe(root, path)
        item['integrity'] = ('missing' if not original.is_file() else
                             'unregistered' if entry is None else
                             'unchanged' if digest(original.read_bytes()) == entry['sha256'] else 'changed')
        cited = coverage['cited_pages'].get(path, [])
        item['coverage'] = {'status': 'unregistered' if entry is None else 'cited' if cited else
                            'reviewed_no_page' if path in coverage['reviewed_no_page_sources'] else 'uncovered',
                            'pages': cited}
        item['reading_copy'] = None
        if entry:
            raw = f"wiki/raw/{entry['batch']}/{entry['relative']}.md"
            reading = {'path': raw, 'status': 'missing', 'error': None}
            if safe(root, raw).is_file():
                data = safe(root, raw).read_bytes()
                reading['status'] = ('unverified' if raw not in views else
                                     'changed' if digest(data) != views[raw]['sha256'] else 'verified')
                if reading['status'] == 'verified':
                    try:
                        origin_hashes(root, raw, data)
                    except (ValueError, OSError) as exc:
                        reading.update(status='invalid_origin', error=str(exc))
            item['reading_copy'] = reading
        items.append(item)
    return {'sources': items[offset:offset + limit], 'total': len(items),
            'total_in_vault': len(set(manifest) | actual),
            'next_offset': offset + limit if offset + limit < len(items) else None,
            'scope': 'Registered originals and non-hidden files inside sources/; external inputs are not scanned.',
            'semantic_audit': 'agent_required'}
