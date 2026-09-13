"""Resumable source units, open questions, and optional evidence-bearing relations."""
from wiki_core import canonical, digest, is_knowledge, now, read_json, safe, write_json
from wiki_evidence import quoted_evidence, source_bytes


def required(value, name):
    if not isinstance(value, str) or not value.strip():
        raise ValueError('Nonempty ' + name + ' required')
    return value.strip()


def progress(root, source=None, units=None):
    path = safe(root, '.llm-wiki/source-progress.json')
    state = read_json(path, {'sources': {}})
    if source is not None:
        _, entry = source_bytes(root, source)
        if not isinstance(units, list) or not units:
            raise ValueError('Supply bounded source units with locators and dispositions')
        record = state['sources'].setdefault(source, {'sha256': entry['sha256'], 'units': {}})
        if record['sha256'] != entry['sha256']:
            raise ValueError('Source progress belongs to another source revision')
        for unit in units:
            key = required(unit.get('id'), 'unit id')
            locator = required(unit.get('locator'), 'section/page locator')
            status = unit.get('status', 'pending')
            if status not in ('pending', 'partial', 'complete', 'deferred'):
                raise ValueError('Invalid unit status')
            note = required(unit.get('note'), 'unit note')
            mappings = unit.get('pages', [])
            if not isinstance(mappings, list) or any(not is_knowledge(p) or not safe(root, p).is_file() for p in mappings):
                raise ValueError('Unit mappings must name existing knowledge pages')
            if status == 'complete' and not mappings and not unit.get('no_new_knowledge'):
                raise ValueError('Completed unit needs mapped pages or an explicit no_new_knowledge disposition')
            record['units'][key] = {**unit, 'id': key, 'locator': locator,
                                    'status': status, 'note': note, 'pages': mappings, 'updated': now()}
        write_json(path, state)
    manifest = read_json(safe(root, '.llm-wiki/source-manifest.json'), {'files': {}})['files']
    unplanned = sorted(set(manifest) - set(state['sources']))
    pending = [{'source': s, **u} for s, r in state['sources'].items()
               for u in r['units'].values() if u['status'] != 'complete']
    return {**state, 'unplanned_sources': unplanned, 'pending_units': pending,
            'semantic_review_complete': not unplanned and not pending,
            'meaning': 'Agent-recorded unit dispositions, not proof of exhaustive or correct extraction'}


def question(root, text=None, ident=None, status='open', note=None, pages=None):
    path = safe(root, '.llm-wiki/questions.json')
    state = read_json(path, {'questions': {}})
    if text is None and ident is None:
        return state
    if status not in ('open', 'needs_writeback', 'answered', 'deferred'):
        raise ValueError('Invalid question status')
    if ident is not None and ident not in state['questions']:
        raise ValueError('Unknown question id')
    old = state['questions'].get(ident, {})
    text = required(text or old.get('question'), 'question')
    ident = ident or digest(text.casefold().encode())[:24]
    mappings = pages or []
    if not isinstance(mappings, list) or any(not is_knowledge(p) or not safe(root, p).is_file() for p in mappings):
        raise ValueError('Question mappings must be existing knowledge pages')
    if status == 'answered' and not mappings:
        raise ValueError('Answered questions require a saved answer page')
    item = {'id': ident, 'question': text, 'status': status, 'note': required(note, 'question note'),
            'pages': mappings, 'updated': now()}
    previous = state['questions'].get(ident)
    item['history'] = [*previous.get('history', []), {k: v for k, v in previous.items() if k != 'history'}] if previous else []
    state['questions'][ident] = item
    write_json(path, state)
    return item


def relation(root, subject=None, predicate=None, object_page=None, evidence=None, scope=None):
    path = safe(root, '.llm-wiki/relations.json')
    state = read_json(path, {'relations': {}})
    if subject is None:
        return state
    for page in (subject, object_page):
        if not isinstance(page, str) or not is_knowledge(page) or not safe(root, page).is_file():
            raise ValueError('Relation endpoints must be existing knowledge pages')
    predicate = required(predicate, 'relationship predicate')
    scope = required(scope, 'relationship scope/version')
    checked = quoted_evidence(root, evidence)
    ident = digest(canonical([subject, predicate, object_page, scope]).encode())[:24]
    item = {'id': ident, 'subject': subject, 'predicate': predicate, 'object': object_page,
            'scope': scope, 'evidence': checked, 'updated': now()}
    previous = state['relations'].get(ident)
    item['history'] = [*previous.get('history', []), {k: v for k, v in previous.items() if k != 'history'}] if previous else []
    state['relations'][ident] = item
    write_json(path, state)
    return item
