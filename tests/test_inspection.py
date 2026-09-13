"""Read-only ergonomics must not weaken evidence or invent source registration."""
import json
import subprocess
import sys
import unittest

import test_contracts as fixtures


class InspectionCase(unittest.TestCase):
    def setUp(self):
        self.fixture = fixtures.VaultCase()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.root, self.base = self.fixture.root, self.fixture.base
        self.call, self.page = self.fixture.call, self.fixture.page

    def source(self, content='Version 2 supports **offline** operation.\n', name='source.md'):
        path = self.base / name
        path.write_bytes(content if isinstance(content, bytes) else content.encode('utf-8'))
        return self.call('source_import', source=str(path))

    def state(self):
        return {p.relative_to(self.root).as_posix(): p.read_bytes()
                for p in self.root.rglob('*') if p.is_file()}

    def test_old_snapshot_and_new_candidates_save_without_guessing(self):
        source = self.source()['sources'][0]
        page = self.page('concepts/offline', 'Version 1 **requires connectivity**.', sources=[source])
        cp = self.call('checkpoint')['id']
        page.write_text(page.read_text().replace('Version 1 **requires connectivity**.', 'Edited live page.'))
        before = self.state()
        old = self.call('quote_find', path='wiki/concepts/offline.md', side='old', checkpoint=cp,
                        query='connectivity')['matches'][0]
        new = self.call('quote_find', path=source, query='offline')['matches'][0]
        self.assertEqual(self.state(), before)
        self.assertEqual(json.loads(new['quote_json']), new['quote'])
        item = self.call('cognition_record', checkpoint=cp, kind='update', topic='Offline',
                         old={**old['record_fields'], 'claim': 'Version 1 needs a connection.'},
                         new={'claim': 'Version 2 supports offline.', 'evidence': [new['record_fields']]},
                         impact='Changes deployment.', question='Retest?', rationale='A version change.')
        self.assertEqual(item['revision'], 1)

    def test_verify_keeps_markdown_unicode_and_crlf_exact(self):
        content = '前言🙂\r\n支持 **离线**，路径 "A"。\r\n结束\r\n'
        source = self.source(content)['sources'][0]
        found = self.call('quote_find', path=source, query='离线')['matches'][0]
        self.assertEqual(found['quote'], '支持 **离线**，路径 "A"。\r\n')
        self.assertEqual(found['line_start'], 2)
        self.assertEqual(content[found['start_char']:found['end_char']], found['quote'])
        self.assertTrue(self.call('quote_verify', path=source, quote=found['quote'])['matched'])
        self.assertFalse(self.call('quote_verify', path=source, quote='支持 离线，路径 "A"。')['matched'])
        self.assertFalse(self.call('quote_verify', path=source, quote=found['quote'].replace('\r\n', '\n'))['matched'])

    def test_find_context_limit_and_multiline_locations(self):
        source = self.source('alpha\nkey key\nomega\nkey\nlast\n')['sources'][0]
        found = self.call('quote_find', path=source, query='key', limit=1)
        self.assertTrue(found['has_more'])
        self.assertEqual(found['matches'][0]['quote'], 'key key\n')
        expanded = self.call('quote_find', path=source, query='key key', context_lines=1)['matches'][0]
        self.assertEqual(expanded['quote'], 'alpha\nkey key\nomega\n')
        verified = self.call('quote_verify', path=source, quote='key key\nomega')['matches'][0]
        self.assertEqual((verified['line_start'], verified['line_end']), (2, 3))

    def test_tampered_sources_views_and_snapshots_are_not_quote_candidates(self):
        imported = self.source()
        source, raw = imported['sources'][0], imported['raw_views'][0]
        self.page('concepts/offline', 'Old claim.', sources=[source])
        cp = self.call('checkpoint')
        snapshot = self.root / cp['pages']['wiki/concepts/offline.md']['snapshot']
        snapshot.write_text('Old claim. forged')
        with self.assertRaisesRegex(ValueError, 'snapshot hash'):
            self.call('quote_find', path='wiki/concepts/offline.md', checkpoint=cp['id'], side='old', query='Old')
        (self.root / raw).write_text((self.root / raw).read_text() + 'forged')
        with self.assertRaisesRegex(ValueError, 'reading copy'):
            self.call('quote_verify', path=raw, quote='offline')
        (self.root / source).write_text('offline forged')
        with self.assertRaisesRegex(ValueError, 'Immutable source changed'):
            self.call('quote_find', path=source, query='offline')

    def test_new_historical_evidence_retains_checkpoint_for_record(self):
        source = self.source()['sources'][0]
        page = self.page('concepts/history', 'Historical interpretation.', sources=[source])
        cp = self.call('checkpoint')['id']
        page.write_text(page.read_text().replace('Historical interpretation.', 'Later interpretation.'))
        found = self.call('quote_find', path='wiki/concepts/history.md', checkpoint=cp,
                          query='Historical')['matches'][0]
        self.assertEqual(found['record_fields']['checkpoint'], cp)
        self.assertTrue(self.call('quote_verify', **found['record_fields'])['matched'])

    def test_quote_paths_parameters_and_binary_input_fail_safely(self):
        source = self.source(b'\xff\x00', 'input.pdf')['sources'][0]
        with self.assertRaisesRegex(ValueError, 'extract a raw_view'):
            self.call('quote_find', path=source, query='test')
        for fields in ({'path': '../outside.md'}, {'side': 'old'}, {'side': 'wrong'},
                       {'query': ''}, {'limit': True}, {'context_lines': 6}):
            with self.assertRaises(ValueError):
                self.call('quote_find', **{'path': source, 'query': 'test', **fields})
        link = self.root / 'sources/link.md'
        link.symlink_to(self.base / 'input.pdf')
        with self.assertRaisesRegex(ValueError, 'Symlink'):
            self.call('quote_find', path='sources/link.md', query='test')

    def test_inventory_exposes_unregistered_missing_and_binary_backlog(self):
        registered = self.source()
        source = registered['sources'][0]
        binary = self.source(b'\xff\x00', 'input.pdf')['sources'][0]
        unregistered = self.root / 'sources/manual-copy.md'
        unregistered.write_text('Not registered.')
        self.page('concepts/citation', 'A sourced page.', sources=[source])
        before = self.state()
        listed = {item['path']: item for item in self.call('source_list')['sources']}
        self.assertEqual(self.state(), before)
        self.assertEqual(listed[source]['reading_copy']['status'], 'verified')
        self.assertEqual(listed[source]['coverage']['status'], 'cited')
        self.assertEqual(listed[binary]['reading_copy']['status'], 'missing')
        self.assertEqual(listed[binary]['coverage']['status'], 'uncovered')
        self.assertEqual(listed['sources/manual-copy.md']['registration'], 'unregistered')
        (self.root / source).unlink()
        missing = self.call('source_list', query='source.md')['sources'][0]
        self.assertEqual(missing['integrity'], 'missing')
        self.assertEqual(missing['reading_copy']['status'], 'invalid_origin')

    def test_inventory_versions_origins_pagination_and_no_page_review(self):
        first = self.source('Version one.\n')['sources'][0]
        second = self.source('Version two.\n')['sources'][0]
        self.call('source_review', source=first, outcome='no_new_knowledge',
                  reason='Reviewed fixture source contains no additional reusable knowledge.')
        start = self.call('source_list', query=str(self.base / 'source.md'), limit=1)
        self.assertEqual(start['total'], 2)
        self.assertEqual(start['next_offset'], 1)
        end = self.call('source_list', limit=1, offset=start['next_offset'])
        self.assertIsNone(end['next_offset'])
        combined = {item['path']: item for item in start['sources'] + end['sources']}
        self.assertEqual(set(combined), {first, second})
        self.assertEqual(combined[first]['coverage']['status'], 'reviewed_no_page')
        self.assertEqual(combined[second]['coverage']['status'], 'uncovered')
        for fields in ({'limit': 0}, {'offset': -1}, {'query': []}):
            with self.assertRaises(ValueError):
                self.call('source_list', **fields)

    def test_inventory_distinguishes_unverified_changed_and_invalid_origin(self):
        imported = self.source()
        source, raw = imported['sources'][0], imported['raw_views'][0]
        manifest = self.root / '.llm-wiki/raw-manifest.json'
        saved = manifest.read_bytes()
        manifest.write_text('{"files": {}}')
        self.assertEqual(self.call('source_list')['sources'][0]['reading_copy']['status'], 'unverified')
        manifest.write_bytes(saved)
        (self.root / raw).write_text('Changed reading copy.')
        self.assertEqual(self.call('source_list')['sources'][0]['reading_copy']['status'], 'changed')
        self.call('raw_view', source=source, text='Re-extracted text.')
        (self.root / source).write_text('Changed original.')
        item = self.call('source_list')['sources'][0]
        self.assertEqual(item['integrity'], 'changed')
        self.assertEqual(item['reading_copy']['status'], 'invalid_origin')

    def test_cli_stdin_and_file_requests_and_readonly_under_writer_lock(self):
        self.source()
        lock = self.root / '.llm-wiki/write.lock'
        lock.mkdir()
        before = self.state()
        self.assertEqual(self.call('source_list')['total'], 1)
        request = json.dumps({'op': 'source_list', 'root': str(self.root)}, ensure_ascii=False)
        command = [sys.executable, str(fixtures.REPO / 'scripts/wiki_tool.py')]
        stdin = subprocess.run(command, input=request, text=True, capture_output=True)
        path = self.base / 'request with spaces.json'
        path.write_text(request)
        from_file = subprocess.run(command + [str(path)], text=True, capture_output=True)
        self.assertEqual(stdin.returncode, 0, stdin.stdout + stdin.stderr)
        self.assertEqual(from_file.returncode, 0, from_file.stdout + from_file.stderr)
        self.assertEqual(json.loads(stdin.stdout), json.loads(from_file.stdout))
        self.assertEqual(self.state(), before)
        self.assertTrue(lock.is_dir())

    def test_empty_digest_does_not_hide_source_only_backlog(self):
        self.call('sync')
        source = self.source()['sources'][0]
        self.call('sync')
        before = self.state()
        self.assertFalse(self.call('review_list')['pending'])
        self.assertTrue(self.call('digest_prepare', target='preview-only', dry_run=True)['empty'])
        inventory = self.call('source_list')['sources']
        self.assertEqual(inventory[0]['path'], source)
        self.assertEqual(inventory[0]['coverage']['status'], 'uncovered')
        self.assertEqual(self.state(), before)


if __name__ == '__main__':
    unittest.main()
