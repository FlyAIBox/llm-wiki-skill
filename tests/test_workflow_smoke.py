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
            self.assertEqual(request("digest_ack", id=draft["id"], receipt="synthetic-test-receipt")
                             ["user_read"], "not_inferred")
            self.assertFalse(request("digest_prepare", target="test-only")["notify"])
            request("cognition_feedback", id=item["id"], action="read")

            plan = request("schedule_plan", name="Test plan", times=["09:00"],
                           timezone="Asia/Shanghai", target="test-only")
            self.assertEqual(plan["state"], "planned")
            self.assertEqual(request("status")["schedules"], [])


if __name__ == "__main__":
    unittest.main()
