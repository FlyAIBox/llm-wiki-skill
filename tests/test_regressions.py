"""User-workflow regressions from the Chinese wiki and briefing audit."""
import json
import sys
import unittest
from pathlib import Path

sys.dont_write_bytecode = True
import test_contracts as fixtures


class RegressionCase(unittest.TestCase):
    def setUp(self):
        self.fixture = fixtures.VaultCase()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.root, self.base = self.fixture.root, self.fixture.base
        self.call, self.page = self.fixture.call, self.fixture.page

    def source(self, text='A sourced finding.', name='evidence.md'):
        path = self.base / name
        path.write_text(text, encoding='utf-8')
        return self.call('source_import', source=str(path))['sources'][0]

    def finding(self, source=None, claim='A sourced finding.', ident=None):
        source = source or self.source()
        request = dict(kind='new_finding', topic='New knowledge',
                       new={'claim': claim, 'evidence': [{'path': source, 'quote': 'A sourced finding.'}]},
                       impact='Changes an engineering decision.', question='Verify the target version?',
                       rationale='New method supported by the captured source.')
        if ident:
            request['id'] = ident
        return self.call('cognition_record', **request)

    def receipt(self, message='fixture-message'):
        return {'host': 'synthetic-test', 'target': 'test-only', 'message_id': message,
                'delivered_at': '2026-09-13T08:00:00+00:00', 'evidence': 'Fixture only; no native message sent'}

    def test_new_knowledge_needs_no_fabricated_old_claim(self):
        item = self.finding()
        draft = self.call('digest_prepare', target='test-only')
        self.assertIn(item['id'], draft['versions'])
        self.assertIn('新增知识', draft['text'])
        self.assertTrue(draft['notify'])

    def test_source_tampering_blocks_record_and_delivery(self):
        source = self.source()
        item = self.finding(source)
        (self.root / source).write_text('A sourced finding. Altered.', encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'Immutable source changed'):
            self.finding(source, claim='Altered claim')
        with self.assertRaisesRegex(ValueError, 'Immutable source changed'):
            self.call('digest_prepare', target='test-only')
        self.assertEqual(len(self.call('cognition_list')['items']), 1)

    def test_raw_view_ownership_and_source_identity_checked(self):
        source = self.source()
        manifest = json.loads((self.root/'.llm-wiki/source-manifest.json').read_text())['files'][source]
        raw = f"wiki/raw/{manifest['batch']}/{manifest['relative']}.md"
        self.finding(raw)
        path = self.root / raw
        path.write_text(path.read_text() + '\nUnverified addition.\n', encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'reading copy'):
            self.finding(raw, claim='Unverified claim')

    def test_alias_only_query_finds_page(self):
        self.page('concepts/alpha', 'Neutral body.', aliases=['ZXQ987Alias'])
        hits = self.call('search', query='ZXQ987Alias')['results']
        self.assertEqual(hits[0]['path'], 'wiki/concepts/alpha.md')

    def test_legacy_frozen_extraction_survives_current_view_regeneration(self):
        source=self.source()
        manifest=json.loads((self.root/'.llm-wiki/source-manifest.json').read_text())['files'][source]
        raw=f"wiki/raw/{manifest['batch']}/{manifest['relative']}.md"
        item=self.finding(raw)
        path=self.root/'.llm-wiki/cognition.json'
        state=json.loads(path.read_text())
        del state['items'][item['id']]['content']['new']['evidence'][0]['origins']
        path.write_text(json.dumps(state),encoding='utf-8')
        self.call('raw_view',source=source,text='A sourced finding. Re-rendered extraction.')
        self.assertTrue(self.call('digest_prepare',target='test-only')['notify'])

    def test_late_receipt_does_not_acknowledge_new_revision(self):
        source = self.source(); item = self.finding(source)
        old = self.call('digest_prepare', target='test-only')
        self.finding(source, claim='Updated interpretation.', ident=item['id'])
        newest = self.call('digest_prepare', target='test-only')
        self.call('digest_ack', id=old['id'], receipt=self.receipt())
        pending = self.call('digest_prepare', target='test-only')
        self.assertEqual(pending['id'], newest['id'])
        self.assertEqual(pending['versions'][item['id']], 2)

    def test_unknown_dispatch_blocks_retry_until_reconciled(self):
        self.finding()
        draft = self.call('digest_prepare', target='test-only')
        attempt = self.call('digest_attempt', id=draft['id'], host='fixture', run_id='run-1')
        self.assertEqual(self.call('digest_attempt', id=draft['id'], host='fixture', run_id='run-1')['id'], attempt['id'])
        blocked = self.call('digest_prepare', target='test-only', dry_run=True)
        self.assertFalse(blocked['notify'])
        self.assertEqual(blocked['blocked'], 'delivery_unknown')
        self.call('digest_failed', attempt_id=attempt['id'], evidence='Fixture native run confirmed no message sent.')
        self.assertTrue(self.call('digest_prepare', target='test-only')['notify'])

    def test_wrong_target_and_unstructured_receipts_rejected(self):
        self.finding(); draft = self.call('digest_prepare', target='test-only')
        with self.assertRaisesRegex(ValueError, 'Structured'):
            self.call('digest_ack', id=draft['id'], receipt='looks delivered')
        receipt = {**self.receipt(), 'target': 'another-target'}
        with self.assertRaisesRegex(ValueError, 'target mismatch'):
            self.call('digest_ack', id=draft['id'], receipt=receipt)

    def test_old_feedback_keeps_new_revision_unread_and_unresolved(self):
        source=self.source(); item=self.finding(source)
        self.finding(source, claim='Second interpretation.', ident=item['id'])
        with self.assertRaisesRegex(ValueError, 'exact displayed revision'):
            self.call('cognition_feedback', id=item['id'], action='read')
        old = self.call('cognition_feedback', id=item['id'], action='accepted_new', revision=1,
                        note='Accepted the version actually displayed.')
        self.assertEqual(old['read_revision'], 1)
        self.assertEqual(old['decision'], 'pending')
        self.assertEqual(old['feedback'][-1]['revision'], 1)
        self.assertEqual(self.call('digest_prepare', target='test-only')['versions'][item['id']], 2)

    def native_session(self, draft, complete=True, thread='test-thread', marker=True):
        text = 'The briefing\n简报编号：' + draft['id'] if marker else 'Unrelated final output'
        events = [dict(type='session_meta', payload={'id': thread}),
                  dict(type='event_msg', payload={'type': 'task_started', 'turn_id': 'turn-1'}),
                  dict(type='response_item', payload={'role':'assistant', 'phase':'final_answer', 'id':'msg-1',
                                                     'content':[{'type':'output_text','text':text}]})]
        if complete:
            events.append(dict(type='event_msg', timestamp='2099-01-01T09:00:00+08:00',
                               payload={'type':'task_complete','turn_id':'turn-1','last_agent_message':text}))
        path=self.base/'session.jsonl'
        path.write_text(''.join(json.dumps(e)+'\n' for e in events),encoding='utf-8')
        return str(path)

    def test_codex_completed_output_reconciles_once_without_marking_read(self):
        item=self.finding(); draft=self.call('digest_prepare',target='codex-thread:test-thread')
        self.call('digest_attempt',id=draft['id'],host='codex-local-thread',run_id='turn-1')
        incomplete=self.native_session(draft,complete=False)
        self.assertFalse(self.call('digest_reconcile',session_path=incomplete,thread_id='test-thread')['reconciled'])
        self.assertFalse(self.call('digest_prepare',target='codex-thread:test-thread')['notify'])
        complete=self.native_session(draft)
        receipt=self.call('digest_reconcile',session_path=complete,thread_id='test-thread')['reconciled']
        self.assertEqual(receipt[0]['receipt']['message_id'],'msg-1')
        self.assertTrue(self.call('digest_prepare',target='codex-thread:test-thread')['empty'])
        self.assertEqual(self.call('cognition_list')['items'][0]['read_revision'],0)
        self.assertFalse(self.call('digest_reconcile',session_path=complete,thread_id='test-thread')['reconciled'])
        with self.assertRaisesRegex(ValueError,'thread does not match'):
            self.call('digest_reconcile',session_path=complete,thread_id='wrong-thread')

    def test_codex_unrelated_final_is_not_a_receipt(self):
        self.finding(); draft=self.call('digest_prepare',target='codex-thread:test-thread')
        path=self.native_session(draft,marker=False)
        self.assertFalse(self.call('digest_reconcile',session_path=path,thread_id='test-thread')['reconciled'])

    def test_cross_batch_links_repair_and_unimported_gaps_reported(self):
        source_a=self.source('[B](b.md#section) and [outside](missing.md).\n`[code](fake.md)`', 'a.md')
        self.source('# Section\n\nB content.', 'b.md')
        before=(self.root/source_a).read_bytes()
        preview=self.call('links_repair')
        self.assertEqual(preview['links_repaired'],1)
        self.assertEqual(len(self.call('links')['issues']),2)
        self.call('links_repair',dry_run=False)
        remaining=self.call('links')['issues']
        self.assertEqual(len(remaining),1)
        self.assertEqual(remaining[0]['target'],'missing.md')
        self.assertEqual((self.root/source_a).read_bytes(),before)
        self.assertFalse(self.call('status')['navigation']['navigation_complete'])

    def test_ambiguous_source_versions_are_not_silently_selected(self):
        self.source('[B](b.md)', 'a.md')
        self.source('B first.', 'b.md'); self.source('B second.', 'b.md')
        self.assertEqual(self.call('links_repair')['links_repaired'],0)

    def test_footnote_prose_is_not_a_reference_link_destination(self):
        self.source('A fact[^1].\n\n[^1]: Author Name and a prose explanation.\n[real]: missing.md\n')
        issues=self.call('links')['issues']
        self.assertEqual([item['target'] for item in issues],['missing.md'])

    def test_link_repair_cannot_certify_unrelated_raw_edits(self):
        source=self.source('[B](b.md)', 'a.md'); self.source('B.', 'b.md')
        entry=json.loads((self.root/'.llm-wiki/source-manifest.json').read_text())['files'][source]
        raw=self.root/f"wiki/raw/{entry['batch']}/{entry['relative']}.md"
        raw.write_text(raw.read_text()+'\nInjected claim.',encoding='utf-8')
        with self.assertRaisesRegex(ValueError,'outside raw_view'):
            self.call('links_repair',dry_run=False)
        self.assertTrue(any(i['issue']=='reading_copy_changed_or_missing' for i in self.call('status')['issues']))

    def test_dispatch_refuses_a_draft_after_knowledge_changed(self):
        source=self.source(); item=self.finding(source)
        draft=self.call('digest_prepare',target='test-only')
        self.finding(source,claim='Changed interpretation.',ident=item['id'])
        with self.assertRaisesRegex(ValueError,'no longer current'):
            self.call('digest_attempt',id=draft['id'],host='fixture',run_id='late-run')

    def test_report_and_evidence_snapshot_tampering_are_detected(self):
        self.finding(); draft=self.call('digest_prepare',target='test-only')
        report=self.root/draft['path']; report.write_text('Altered report.',encoding='utf-8')
        with self.assertRaisesRegex(ValueError,'digest was modified'):
            self.call('digest_prepare',target='test-only',dry_run=True)
        item=self.call('cognition_list')['items'][0]
        frozen=self.root/item['content']['new']['evidence'][0]['snapshot']
        frozen.write_text('Altered snapshot.',encoding='utf-8')
        with self.assertRaisesRegex(ValueError,'snapshot'):
            self.call('digest_prepare',target='test-only')

    def test_unit_progress_and_question_completion_require_saved_outcomes(self):
        source=self.source()
        self.assertIn(source,self.call('source_progress')['unplanned_sources'])
        self.call('source_progress',source=source,units=[{'id':'section-1','locator':'§1','status':'partial','note':'One method still needs review.'}])
        self.assertFalse(self.call('source_progress')['semantic_review_complete'])
        self.page('concepts/method','A sourced finding.',sources=[source])
        self.call('source_progress',source=source,units=[{'id':'section-1','locator':'§1','status':'complete','note':'Method mapped to page.','pages':['wiki/concepts/method.md']}])
        self.assertTrue(self.call('source_progress')['semantic_review_complete'])
        q=self.call('question',question='Which method?',note='User decision question.')
        with self.assertRaisesRegex(ValueError,'saved answer'):
            self.call('question',id=q['id'],status='answered',note='Done.')
        self.call('question',id=q['id'],status='answered',note='Saved method comparison.',pages=['wiki/concepts/method.md'])
        self.assertFalse(self.call('status')['open_questions'])

    def test_typed_relations_have_retrievable_evidence_and_scope(self):
        source=self.source('A depends on B.')
        self.page('concepts/a','A depends on B.',sources=[source]); self.page('concepts/b','B.',sources=[source])
        rel=self.call('relation',subject='wiki/concepts/a.md',predicate='depends_on',object='wiki/concepts/b.md',
                      scope='Version 1',evidence=[{'path':source,'quote':'A depends on B.'}])
        graph=self.call('graph')
        self.assertEqual(graph['relations'][0]['id'],rel['id'])
        self.assertEqual(graph['relations'][0]['predicate'],'depends_on')

    def test_schedule_binding_distinguishes_configured_from_verified(self):
        plan=self.call('schedule_plan',name='Test',times=['09:00'],timezone='Asia/Shanghai',target='test-only',days=['mon'])
        bound=self.call('schedule_bind',plan=plan,host='fixture',job_ids=['job'])
        self.assertEqual(bound['health'],'unverified')
        self.assertTrue(Path(bound['runtime']['python']).is_absolute())
        verification={'evidence':'Synthetic native inspection','checked_at':'2026-09-13T08:00:00+00:00',
                      'effective_timezone':'Asia/Shanghai','timezone_mode':'host_local','native_rule':'fixture',
                      'next_run_at':'2026-09-14T09:00:00+08:00'}
        self.assertEqual(self.call('schedule_bind',plan=plan,host='fixture',job_ids=['job'],verification=verification)['health'],'partial')
        with self.assertRaisesRegex(ValueError,'next run'):
            self.call('schedule_bind',plan=plan,host='fixture',job_ids=['job'],verification={**verification,'next_run_at':'2026-09-14T10:00:00+08:00'})


if __name__ == '__main__':
    unittest.main()
