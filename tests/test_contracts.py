"""Contract checks for installation, evidence, retrieval, tracking and CLI failures."""

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


sys.dont_write_bytecode = True
REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))
from wiki_tool import execute  # noqa: E402


class VaultCase(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.base = Path(self.temporary.name)
        self.root = self.base / "vault"
        self.call("init", purpose="# Wiki Purpose\n\nContract test.\n")

    def call(self, op, **fields):
        return execute({"op": op, "root": str(self.root), **fields})

    def page(self, slug, body, *, sources=None, aliases=None):
        path = self.root / "wiki" / f"{slug}.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        title = slug.rsplit("/", 1)[-1]
        meta = (
            "---\n"
            f'title: "{title}"\n'
            f'description: "Test {title}."\n'
            'type: "concept"\n'
            'tags: ["test"]\n'
            f"sources: {json.dumps(sources or [])}\n"
            'created: "2026-09-12"\n'
            'updated: "2026-09-12"\n'
            f"aliases: {json.dumps(aliases or [])}\n"
            'confidence: "medium"\n'
            'contested: false\n'
            "---\n\n"
        )
        path.write_text(meta + body + "\n", encoding="utf-8")
        return path

    def test_install_preserves_bootstrap_and_rejects_edited_skill(self):
        # A second init is a no-op, not an overwrite of the initialized vault.
        self.assertTrue(self.call("init", purpose="Different purpose")["already_initialized"])
        self.assertEqual((self.root / "wiki-purpose.md").read_text(),
                         "# Wiki Purpose\n\nContract test.\n")
        skill = self.root / ".agents/skills/ingest/SKILL.md"
        modified = skill.read_text() + "\nUser customization.\n"
        skill.write_text(modified, encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "user-owned or edited"):
            self.call("skill_install", dry_run=True)
        with self.assertRaisesRegex(ValueError, "user-owned or edited"):
            self.call("skill_install")
        self.assertEqual(skill.read_text(), modified)

    def test_install_rejects_symlink_in_vault_local_target(self):
        external = self.base / "external-skills"
        external.mkdir()
        (self.root / "redirect").symlink_to(external, target_is_directory=True)
        target = self.root / "redirect" / "skills"
        with self.assertRaisesRegex(ValueError, "symlink"):
            self.call("skill_install", targets=[str(target)], dry_run=True)
        self.assertFalse((external / "skills").exists())

    def test_folder_import_versions_hidden_files_and_relative_links(self):
        folder = self.base / "input"
        folder.mkdir()
        (folder / "a.md").write_text("See [B](b.md).\n", encoding="utf-8")
        (folder / "b.md").write_text("Version one.\n", encoding="utf-8")
        (folder / ".private.md").write_text("Not in scope.\n", encoding="utf-8")
        first = self.call("source_import", source=str(folder), source_url="https://example.test/folder")
        self.assertEqual(len(first["sources"]), 2)
        self.assertEqual(len(first["raw_views"]), 2)
        self.assertTrue(all(".private" not in path for path in first["sources"]))
        view = self.root / next(path for path in first["raw_views"] if path.endswith("a.md.md"))
        self.assertIn("b.md)", view.read_text(encoding="utf-8"))
        self.assertNotIn("[B](b.md)", view.read_text(encoding="utf-8"))
        self.assertTrue(self.call("source_import", source=str(folder))["duplicate"])
        (folder / "b.md").write_text("Version two.\n", encoding="utf-8")
        second = self.call("source_import", source=str(folder))
        self.assertNotEqual(first["batch"], second["batch"])
        self.assertEqual((self.root / next(p for p in first["sources"] if p.endswith("b.md")))
                         .read_text(encoding="utf-8"), "Version one.\n")

    def test_symlink_and_nested_destination_are_rejected(self):
        folder = self.base / "linked"
        folder.mkdir()
        (folder / "ok.md").write_text("ok\n", encoding="utf-8")
        (folder / "alias.md").symlink_to(folder / "ok.md")
        with self.assertRaisesRegex(ValueError, "symlink"):
            self.call("source_import", source=str(folder))
        with self.assertRaisesRegex(ValueError, "contain the destination"):
            self.call("source_import", source=str(self.base))

    def test_source_drift_is_reported_and_blocks_extraction(self):
        original = self.base / "evidence.md"
        original.write_text("Original evidence.\n", encoding="utf-8")
        source = self.call("source_import", source=str(original))["sources"][0]
        (self.root / source).write_text("Tampered evidence.\n", encoding="utf-8")
        issues = self.call("status")["issues"]
        self.assertTrue(any(item["issue"] == "immutable_source_changed_or_missing" for item in issues))
        with self.assertRaisesRegex(ValueError, "registered, unchanged"):
            self.call("raw_view", source=source, text="Tampered evidence.")

    def test_graph_ignores_examples_and_resolves_aliases(self):
        self.page("concepts/alpha", "中文检索。 [[concepts/beta]] [[ghost]]\n"
                  "`[[inline-example]]`\n```md\n[[fenced-example]]\n```\n",
                  aliases=["Alpha Alias"])
        self.page("concepts/beta", "[[Alpha Alias]]")
        self.call("index")
        graph = self.call("graph")
        self.assertEqual(len(graph["nodes"]), 2)
        self.assertEqual(len(graph["edges"]), 2)
        self.assertEqual([item["page"] for item in graph["wanted"]], ["ghost"])
        self.assertEqual(graph["orphans"], [])
        hits = self.call("search", query="中文检索")["results"]
        self.assertEqual(hits[0]["path"], "wiki/concepts/alpha.md")

    def test_sync_detects_same_mtime_edits_and_preserves_pending_batches(self):
        page = self.page("concepts/alpha", "First claim.")
        self.call("index")
        self.call("sync")
        first_review = self.call("review_list")["pending"][0]
        self.call("review_complete", id=first_review["id"], note="Initial baseline checked.")
        prior_state = (self.root / ".llm-wiki/sync-state.json").read_bytes()
        old_mtime = page.stat()
        page.write_text(page.read_text().replace("First claim.", "Second claim."))
        os.utime(page, ns=(old_mtime.st_atime_ns, old_mtime.st_mtime_ns))
        preview = self.call("sync", dry_run=True)
        self.assertEqual(preview["modified"], ["wiki/concepts/alpha.md"])
        self.assertEqual((self.root / ".llm-wiki/sync-state.json").read_bytes(), prior_state)
        self.call("sync")
        self.assertEqual(len(self.call("review_list")["pending"]), 1)
        page.write_text(page.read_text().replace("Second claim.", "Third claim."))
        self.call("sync")
        self.assertEqual(len(self.call("review_list")["pending"]), 2)

    def test_status_flags_missing_source_and_index_entry(self):
        self.page("concepts/unindexed", "A claim.", sources=["sources/not-present.md"])
        issues = self.call("status")["issues"]
        self.assertEqual({item["issue"] for item in issues},
                         {"missing_source", "missing_from_index"})

    def test_schedule_plan_is_read_only_and_binding_requires_job_ids(self):
        config = self.root / ".llm-wiki/config.toml"
        original = config.read_text(encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "HH:MM"):
            self.call("schedule_plan", name="Test", times=["25:00"],
                      timezone="Asia/Shanghai", target="test-only")
        plan = self.call("schedule_plan", name="Test", times=["12:00", "09:00", "09:00"],
                         timezone="Asia/Shanghai", target="test-only", days=["mon", "wed"])
        self.assertEqual(plan["times"], ["09:00", "12:00"])
        self.assertEqual(config.read_text(encoding="utf-8"), original)
        with self.assertRaisesRegex(ValueError, "job ids are required"):
            self.call("schedule_bind", plan=plan, host="synthetic-host", job_ids=[])
        self.assertEqual(config.read_text(encoding="utf-8"), original)
        config.write_text(original + '\n[custom]\nkey = "preserved"\n', encoding="utf-8")
        bound = self.call("schedule_bind", plan=plan, host="synthetic-host",
                          job_ids=["synthetic-job-id"])
        self.assertEqual(bound["state"], "active")
        self.assertIn('key = "preserved"', config.read_text(encoding="utf-8"))
        self.assertIn("synthetic-job-id", config.read_text(encoding="utf-8"))
        self.assertEqual(len(self.call("status")["schedules"]), 1)


class CliCase(unittest.TestCase):
    def test_json_protocol_and_invalid_request(self):
        script = REPO / "scripts/wiki_tool.py"
        good = subprocess.run([sys.executable, str(script)], input='{"op":"skill_list"}',
                              text=True, capture_output=True, check=False)
        self.assertEqual(good.returncode, 0)
        self.assertEqual(len(json.loads(good.stdout)["result"]["skills"]), 5)
        bad = subprocess.run([sys.executable, str(script)], input='{"op":"unknown"}',
                             text=True, capture_output=True, check=False)
        self.assertEqual(bad.returncode, 1)
        self.assertFalse(json.loads(bad.stdout)["ok"])


if __name__ == "__main__":
    unittest.main()
