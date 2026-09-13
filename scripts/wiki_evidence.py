"""Validate saved evidence against immutable origins, including derived views."""
from wiki_core import digest, frontmatter, get_checkpoint, read_json, safe, snapshot


def source_bytes(root, path):
    entry = read_json(safe(root, '.llm-wiki/source-manifest.json'), {'files': {}})['files'].get(path)
    if entry is None:
        raise ValueError('Evidence requires a registered source: ' + path)
    data = safe(root, path).read_bytes()
    if digest(data) != entry['sha256']:
        raise ValueError('Immutable source changed: ' + path)
    return data, entry


def origin_hashes(root, path, data=None, seen=None):
    seen = set() if seen is None else seen
    if path in seen:
        raise ValueError('Cyclic evidence references: ' + path)
    if path.startswith('sources/'):
        _, entry = source_bytes(root, path)
        if data is not None and digest(data) != entry['sha256']:
            raise ValueError('Evidence bytes differ from immutable source: ' + path)
        return {path: entry['sha256']}
    if not path.startswith('wiki/'):
        raise ValueError('Evidence must be a source or wiki page')
    seen = seen | {path}
    data = safe(root, path).read_bytes() if data is None else data
    meta, _, _ = frontmatter(data.decode('utf-8'))
    refs = meta.get('sources', [])
    if not isinstance(refs, list) or not refs:
        raise ValueError('Evidence page has no origin references: ' + path)
    if path.startswith('wiki/raw/'):
        view = read_json(safe(root, '.llm-wiki/raw-manifest.json'), {'files': {}})['files'].get(path)
        if not view or view['sha256'] != digest(data):
            raise ValueError('Unverified or changed reading copy; regenerate with raw_view: ' + path)
        if len(refs) != 1 or meta.get('source_sha256') != source_bytes(root, refs[0])[1]['sha256']:
            raise ValueError('Reading copy source identity mismatch: ' + path)
    origins = {}
    for ref in refs:
        origins.update(origin_hashes(root, ref, seen=seen))
    return origins


def quoted_evidence(root, evidence):
    if not isinstance(evidence, list) or not evidence:
        raise ValueError('Quoted saved evidence is required')
    checked = []
    for entry in evidence:
        path, quote = entry.get('path', ''), entry.get('quote')
        if not isinstance(quote, str) or not quote.strip():
            raise ValueError('Nonempty evidence.quote is required')
        if entry.get('checkpoint'):
            frozen = get_checkpoint(root, entry['checkpoint'])['pages'].get(path)
            if frozen is None:
                raise ValueError('Evidence page absent from checkpoint')
            data = safe(root, frozen['snapshot']).read_bytes()
            if digest(data) != frozen['sha256']:
                raise ValueError('Evidence snapshot hash mismatch')
        else:
            data = safe(root, path).read_bytes()
        origins = origin_hashes(root, path, data)
        if quote not in data.decode('utf-8'):
            raise ValueError('New quotation is absent from saved evidence: ' + path)
        checked.append({'path': path, 'quote': quote, 'origins': origins, **snapshot(root, data)})
    return checked


def verify_frozen(root, entry):
    data = safe(root, entry['snapshot']).read_bytes()
    if digest(data) != entry['sha256'] or entry['quote'] not in data.decode('utf-8'):
        raise ValueError('Evidence snapshot or quotation mismatch')
    origins = entry.get('origins')
    if origins is None:  # Legacy records retain valid snapshots; validate their origin chain.
        path = entry.get('path', entry.get('page'))
        if path.startswith('wiki/raw/'):
            # The frozen legacy extraction can outlive a regenerated current reading copy.
            meta, _, _ = frontmatter(data.decode('utf-8'))
            refs = meta.get('sources', [])
            if not isinstance(refs, list) or len(refs) != 1:
                raise ValueError('Legacy extraction has no unique origin')
            original = source_bytes(root, refs[0])[1]
            if meta.get('source_sha256') != original['sha256']:
                raise ValueError('Legacy extraction origin mismatch')
            origins = {refs[0]: original['sha256']}
        else:
            origins = origin_hashes(root, path, data)
    for path, expected in origins.items():
        if source_bytes(root, path)[1]['sha256'] != expected:
            raise ValueError('Evidence origin identity changed: ' + path)
    return data.decode('utf-8')
