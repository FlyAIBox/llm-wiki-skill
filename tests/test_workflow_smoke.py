"""Exercise the helper lifecycle in an isolated fixture, without native delivery."""

from pathlib import Path
import sys
import tempfile
import unittest


sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from wiki_tool import execute  # noqa: E402


class WorkflowSmokeTest(unittest.TestCase):
    def test_capture_review_digest_and_plan(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            root = base / "vault"
            request = lambda op, **kwargs: execute({"op": op, "root": str(root), **kwargs})
            request("init", name="Smoke", purpose="# Wiki Purpose\n\nTest only.\n")

            first = base / "version-1.md"
            first.write_text("Version 1 requires a network connection.\n", encoding="utf-8")
            imported = request("source_import", source=str(first))
            self.assertFalse(imported["duplicate"])
            self.assertTrue(request("source_import", source=str(first))["duplicate"])
            old_source = imported["sources"][0]

            page = root / "wiki/concepts/connectivity.md"
            def content(claim, sources):
                return (
                    '---\n'
                    'title: "Connectivity"\n'
                    'description: "Version-specific network support."\n'
                    'type: "concept"\n'
                    'tags: ["test"]\n'
                    f'sources: {sources}\n'
                    'created: "2026-09-12"\n'
                    'updated: "2026-09-12"\n'
                    'aliases: []\n'
                    'confidence: "medium"\n'
                    'contested: false\n'
                    '---\n\n'
                    f'# Connectivity\n\n{claim}\n'
                )
            old_claim = "Version 1 requires a network connection."
            page.write_text(content(old_claim, f'["{old_source}"]'), encoding="utf-8")
            request("index")
            before = request("sync")["checkpoint"]
            initial_review = request("review_list")["pending"][0]
            request("review_complete", id=initial_review["id"],
                    note="Initial page has no earlier knowledge baseline.")

            second = base / "version-2.md"
            new_claim = "Version 2 runs offline."
            second.write_text(new_claim + "\n", encoding="utf-8")
            new_source = request("source_import", source=str(second))["sources"][0]
            page.write_text(content(new_claim, f'["{old_source}", "{new_source}"]'), encoding="utf-8")
            request("index")
            request("sync")
            pending = request("review_list")["pending"]
            self.assertEqual(len(pending), 1)

            item = request(
                "cognition_record", checkpoint=before, topic="Connectivity",
                kind="context_difference", old={"page": "wiki/concepts/connectivity.md",
                                                 "claim": old_claim, "quote": old_claim},
                new={"claim": new_claim, "evidence": [{"path": new_source, "quote": new_claim}]},
                impact="Check version before deploying.", question="Which version is in use?",
                rationale="The claims refer to different versions.",
            )
            self.assertFalse(item["duplicate"])
            self.assertTrue(request(
                "cognition_record", checkpoint=before, topic="Connectivity",
                kind="context_difference", old={"page": "wiki/concepts/connectivity.md",
                                                 "claim": old_claim, "quote": old_claim},
                new={"claim": new_claim, "evidence": [{"path": new_source, "quote": new_claim}]},
                impact="Check version before deploying.", question="Which version is in use?",
                rationale="The claims refer to different versions.",
            )["duplicate"])
            request("review_complete", id=pending[0]["id"], note="Compared old and new version-scoped claims.")

            draft = request("digest_prepare", target="test-only", dry_run=True)
            self.assertTrue(draft["notify"])
            self.assertEqual(request("digest_prepare", target="test-only")["id"], draft["id"])
            # A failed or uncertain send must leave the same prepared draft eligible.
            self.assertEqual(request("digest_prepare", target="test-only")["id"], draft["id"])
            self.assertEqual(request("cognition_list")["items"][0]["read_revision"], 0)
            with self.assertRaisesRegex(ValueError, "receipt"):
                request("digest_ack", id=draft["id"], receipt="")
            self.assertTrue(request("digest_prepare", target="test-only")["notify"])

            third = base / "version-3.md"
            newest_claim = "Version 3 runs offline without setup."
            third.write_text(newest_claim + "\n", encoding="utf-8")
            newest_source = request("source_import", source=str(third))["sources"][0]
            revised = request(
                "cognition_record", id=item["id"], checkpoint=before, topic="Connectivity",
                kind="context_difference", old={"page": "wiki/concepts/connectivity.md",
                                                 "claim": old_claim, "quote": old_claim},
                new={"claim": newest_claim,
                     "evidence": [{"path": newest_source, "quote": newest_claim}]},
                impact="Check version before deploying.", question="Which version is in use?",
                rationale="The latest source describes another version.",
            )
            self.assertEqual(revised["revision"], 2)
            current_draft = request("digest_prepare", target="test-only")
            self.assertNotEqual(current_draft["id"], draft["id"])
            receipt = lambda message: {'host': 'synthetic-test-host', 'target': 'test-only',
                'message_id': message, 'delivered_at': '2026-09-13T08:00:00+00:00',
                'evidence': 'Synthetic fixture; no real delivery'}
            request("digest_ack", id=draft["id"], receipt=receipt('old-message'))
            self.assertTrue(request('digest_prepare', target='test-only')['notify'])
            self.assertEqual(request("digest_ack", id=current_draft["id"],
                                     receipt=receipt('new-message'))["user_read"], "not_inferred")
            self.assertFalse(request("digest_prepare", target="test-only")["notify"])
            self.assertEqual(request("cognition_list")["items"][0]["read_revision"], 0)

            # Delivery acknowledges one revision, not every future revision.
            fourth = base / "version-4.md"
            latest_claim = "Version 4 runs offline with local data."
            fourth.write_text(latest_claim + "\n", encoding="utf-8")
            latest_source = request("source_import", source=str(fourth))["sources"][0]
            delivered_revision = request(
                "cognition_record", id=item["id"], checkpoint=before, topic="Connectivity",
                kind="context_difference", old={"page": "wiki/concepts/connectivity.md",
                                                 "claim": old_claim, "quote": old_claim},
                new={"claim": latest_claim,
                     "evidence": [{"path": latest_source, "quote": latest_claim}]},
                impact="Check version before deploying.", question="Which version is in use?",
                rationale="The most recent source describes a newer version.",
            )
            self.assertEqual(delivered_revision["revision"], 3)
            next_draft = request("digest_prepare", target="test-only")
            self.assertTrue(next_draft["notify"])
            self.assertNotEqual(next_draft["id"], current_draft["id"])
            self.assertEqual(request("cognition_list")["items"][0]["read_revision"], 0)
            request("cognition_feedback", id=item["id"], action="read", revision=3)

            plan = request("schedule_plan", name="Test plan", times=["09:00"],
                           timezone="Asia/Shanghai", target="test-only")
            self.assertEqual(plan["state"], "planned")
            self.assertEqual(request("status")["schedules"], [])


if __name__ == "__main__":
    unittest.main()
