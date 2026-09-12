"""Regression: only SKILL.md is required to initialize and install the runtime."""

from pathlib import Path
import sys
import tempfile
import unittest


sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import wiki_setup  # noqa: E402


class InstallEntrypointTest(unittest.TestCase):
    def test_init_with_single_skill_entrypoint(self):
        bundle = Path(__file__).resolve().parents[1]
        self.assertTrue((bundle / "SKILL.md").is_file())
        self.assertFalse((bundle / "SKILL.zh-CN.md").exists())

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "wiki"
            result = wiki_setup.init(root, "# Wiki Purpose\n\nSmoke-test installation.\n")
            self.assertTrue(result["created"])
            self.assertTrue((root / ".llm-wiki/runtime/SKILL.md").is_file())
            self.assertFalse((root / ".llm-wiki/runtime/SKILL.zh-CN.md").exists())
            for host in (".agents", ".claude"):
                for operation in ("ingest", "query", "lint", "research", "briefing"):
                    self.assertTrue((root / host / "skills" / operation / "SKILL.md").is_file())
            preview = wiki_setup.skill_install(root, dry_run=True)
            self.assertEqual(preview["files_to_write"], [])
            moved = Path(directory) / "moved-wiki"
            root.rename(moved)
            self.assertEqual(wiki_setup.skill_install(moved, dry_run=True)["files_to_write"], [])
            operation_text = (moved / ".agents/skills/ingest/SKILL.md").read_text()
            self.assertIn(".llm-wiki/runtime/SKILL.md", operation_text)


if __name__ == "__main__":
    unittest.main()
