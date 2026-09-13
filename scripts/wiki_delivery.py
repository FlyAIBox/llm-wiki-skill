"""Codex local-thread receipt adapter; confirms completed chat output, not OS push/read."""
import json
from pathlib import Path

from wiki_core import digest, snapshot
from wiki_cognition import acknowledge, aware_time, load


def completed_messages(path, thread_id):
    path = Path(path).expanduser()
    if path.is_symlink() or not path.is_file():
        raise ValueError('Select a regular native session transcript')
    session_id = None
    turn_id = None
    finals = {}
    completed = []
    with path.open(encoding='utf-8') as stream:
        for number, line in enumerate(stream, 1):
            try:
                event = json.loads(line)
            except ValueError:
                if not line.endswith('\n'):  # The live writer may have an incomplete tail.
                    break
                raise ValueError('Invalid native transcript JSON') from None
            payload = event.get('payload', {})
            if event.get('type') == 'session_meta':
                session_id = payload.get('id')
            if event.get('type') == 'event_msg' and payload.get('type') == 'task_started':
                turn_id = payload.get('turn_id')
            if (event.get('type') == 'response_item' and payload.get('role') == 'assistant'
                    and (payload.get('phase') == 'final_answer' or payload.get('channel') == 'final')):
                key = payload.get('internal_chat_message_metadata_passthrough', {}).get('turn_id', turn_id)
                text = ''.join(c.get('text', '') for c in payload.get('content', [])
                               if c.get('type') in ('output_text', 'text'))
                finals[key] = {'text': text, 'message_id': payload.get('id')}
            if event.get('type') == 'event_msg' and payload.get('type') == 'task_complete':
                key = payload.get('turn_id')
                message = finals.get(key)
                if message and message['message_id'] and message['text'] == payload.get('last_agent_message'):
                    completed.append({**message, 'turn_id': key, 'at': event['timestamp'], 'line': number})
    if session_id != thread_id:
        raise ValueError('Native transcript thread does not match delivery target')
    return completed


def reconcile_codex(root, session_path, thread_id, digest_id=None, legacy_message_id=None):
    state = load(root)
    target = 'codex-thread:' + thread_id
    if legacy_message_id and not digest_id:
        raise ValueError('Legacy reconciliation requires an exact digest and message id')
    if digest_id and digest_id not in state['digests']:
        raise ValueError('Unknown digest id')
    messages = completed_messages(session_path, thread_id)
    reconciled = []
    for ident, draft in state['digests'].items():
        if draft['target'] != target or draft['status'] == 'delivered' or (digest_id and ident != digest_id):
            continue
        for message in messages:
            if aware_time(message['at']) < aware_time(draft['created']):
                continue
            marker = '简报编号：' + ident
            matched = marker in [line.strip() for line in message['text'].splitlines()]
            if legacy_message_id:
                matched = (message['message_id'] == legacy_message_id
                           and all(item in message['text'] for item in draft['versions']))
            if not matched:
                continue
            frozen = snapshot(root, message['text'].encode())
            receipt = {'host': 'codex-local-thread', 'target': target,
                       'message_id': message['message_id'], 'delivered_at': message['at'],
                       'turn_id': message['turn_id'], 'evidence': f'{session_path}:{message["line"]}',
                       'message_sha256': digest(message['text'].encode()), 'snapshot': frozen['snapshot'],
                       'confirmation': 'completed_thread_output', 'user_read': 'not_inferred'}
            acknowledge(root, ident, receipt)
            reconciled.append({'digest_id': ident, 'receipt': receipt})
            break
    return {'reconciled': reconciled, 'confirmation': 'completed_thread_output',
            'os_notification': 'not_verified', 'user_read': 'not_inferred'}
