"""Runtime merge/sync invariants on disposable data, with no native client calls."""
import argparse
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import profile_tool as tool


class ProfileToolTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.root = self.base / "personal root"
        self.root.mkdir()
        self.entry = self.base / "codex/AGENTS.md"
        self.entry.parent.mkdir()
        self.entry.write_text("# Other instructions\nKeep this exactly.\n")
        for name in tool.FILES[:-1]:
            out = self.root / name
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text("# " + name + "\nExisting personal data.\n")
        self.config = {"schema_version": 1, "custom": "retain", "agents": {"codex": {
            "global_instructions": str(self.entry), "adaptation_status": "not_adapted",
            "history": {"reader_script": None}}}}
        self.save_config()

    def save_config(self):
        (self.root / "config.json").write_bytes(tool.encode_json(self.config))

    def invoke(self, *argv):
        return tool.run(tool.parser().parse_args(["--root", str(self.root)] + list(argv)))

    def snapshot(self):
        return {str(p): p.read_bytes() for p in self.base.rglob("*") if p.is_file()}

    def test_preview_is_read_only_and_adapt_is_idempotent(self):
        before = self.snapshot()
        preview = self.invoke("adapt", "--agent", "codex")
        self.assertTrue(preview["changes"])
        self.assertEqual(self.snapshot(), before)
        self.invoke("adapt", "--agent", "codex", "--apply")
        first = self.snapshot()
        again = self.invoke("adapt", "--agent", "codex", "--apply")
        self.assertEqual(again["changes"], [])
        self.assertEqual(self.snapshot(), first)
        self.assertTrue(self.entry.read_text().startswith("# Other instructions\nKeep this exactly.\n"))
        self.assertEqual(self.entry.read_text().count(tool.BEGIN), 1)
        cfg = json.loads((self.root / "config.json").read_text())
        self.assertEqual(cfg["custom"], "retain")
        self.assertFalse(cfg["agents"]["codex"]["native_load_verified"])

    def test_update_syncs_active_adapter_and_retains_topic_task_config(self):
        self.invoke("adapt", "--agent", "codex", "--apply")
        self.config = json.loads((self.root / "config.json").read_text())
        self.config["agents"]["codex"].update(adaptation_status="adapted", native_load_verified=True,
                                             verification_method="real-client", verified_at="prior")
        self.save_config()
        cfg = (self.root / "config.json").read_bytes()
        topic = (self.root / "TOPICS.md").read_bytes()
        board = (self.root / "global-task/BOARD.md").read_bytes()
        # Repeated adaptation of byte-identical generation preserves prior evidence.
        self.assertEqual(self.invoke("adapt", "--agent", "codex")["changes"], [])
        self.assertEqual((self.root / "config.json").read_bytes(), cfg)
        candidate = self.base / "new.md"
        candidate.write_text("# SPEC\nNew user preference.\n[entry](CONTEXT.md)\n")
        old = (self.root / "SPEC.md").read_bytes()
        result = self.invoke("update", "--file", "SPEC.md", "--from", str(candidate),
                             "--expect-sha", tool.sha(old), "--apply")
        self.assertIn("New user preference.", self.entry.read_text())
        self.assertIn("<" + str(self.root / "CONTEXT.md") + ">", self.entry.read_text())
        self.assertEqual((self.root / "TOPICS.md").read_bytes(), topic)
        self.assertEqual((self.root / "global-task/BOARD.md").read_bytes(), board)
        updated = json.loads((self.root / "config.json").read_text())
        self.assertEqual(updated["agents"]["codex"]["history"], self.config["agents"]["codex"]["history"])
        self.assertFalse(updated["agents"]["codex"]["native_load_verified"])
        self.assertTrue(Path(result["backup"]).is_dir())

    def test_stale_hash_override_and_duplicate_block_fail_before_any_write(self):
        new = self.base / "proposal.md"
        new.write_text("new text")
        before = self.snapshot()
        with self.assertRaisesRegex(ValueError, "expected hash"):
            self.invoke("update", "--file", "SPEC.md", "--from", str(new), "--expect-sha", "old", "--apply")
        self.assertEqual(self.snapshot(), before)
        override = self.entry.parent / "AGENTS.override.md"
        override.write_text("actual overriding instructions")
        before = self.snapshot()
        with self.assertRaisesRegex(ValueError, "takes precedence"):
            self.invoke("adapt", "--agent", "codex", "--apply")
        self.assertEqual(self.snapshot(), before)
        override.unlink()
        self.entry.write_text("<!-- BEGIN CONTEXT-KIT PROFILE v2 -->\na\n" + tool.END + "\n" +
                              "<!-- BEGIN CONTEXT-KIT PROFILE v2 -->\nb\n" + tool.END)
        before = self.snapshot()
        with self.assertRaisesRegex(ValueError, "duplicate"):
            self.invoke("adapt", "--agent", "codex", "--apply")
        self.assertEqual(self.snapshot(), before)

    def test_init_keeps_existing_data_and_ignores_snapshot_deployment_status(self):
        source = self.base / "selected"
        source.mkdir()
        for name in tool.FILES[:-1]:
            out = source / name
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text("Old snapshot " + name)
        (source / "config.json").write_text('{"agents":{"codex":{"native_load_verified":true}}}')
        before = self.snapshot()
        self.assertEqual(self.invoke("init", "--source", str(source), "--apply")["changes"], [])
        self.assertEqual(self.snapshot(), before)
        self.root = self.base / "fresh"
        self.invoke("init", "--source", str(source), "--apply")
        self.assertEqual(json.loads((self.root / "config.json").read_text()), {"schema_version": 1, "agents": {}})

    def test_topic_task_merge_and_export_do_not_touch_unrelated_runtime(self):
        for action, filename in (("topic", "TOPICS.md"), ("task", "global-task/BOARD.md")):
            current = (self.root / filename).read_bytes()
            candidate = self.base / (action + ".md")
            candidate.write_bytes(current + b"\nExplicitly requested saved item.\n")
            baseline = {name: (self.root / name).read_bytes() for name in tool.FILES if name != filename}
            self.invoke(action, "--from", str(candidate), "--expect-sha", tool.sha(current), "--apply")
            self.assertEqual(self.invoke(action)["text"], candidate.read_text())
            self.assertEqual(baseline, {name: (self.root / name).read_bytes() for name in baseline})
        out = self.base / "export.md"
        exported = self.invoke("export", "--output", str(out))
        self.assertNotIn("Explicitly requested saved item.", out.read_text())
        with self.assertRaises(FileExistsError):
            self.invoke("export", "--output", str(out))
        self.assertEqual(exported["sha256"], tool.sha(out.read_bytes()))

    def test_missing_platform_is_not_recreated_and_symlink_not_followed(self):
        self.config["agents"]["claude_code"] = {"global_instructions": str(self.base / "removed-claude/CLAUDE.md")}
        self.save_config()
        before = self.snapshot()
        with self.assertRaisesRegex(ValueError, "unavailable"):
            self.invoke("adapt", "--agent", "all", "--apply")
        self.assertEqual(self.snapshot(), before)
        self.assertFalse((self.base / "removed-claude").exists())
        original = self.root / "SPEC.md"
        external = self.base / "outside.md"
        original.rename(external)
        original.symlink_to(external)
        with self.assertRaisesRegex(ValueError, "symlink"):
            self.invoke("show")

    def test_fresh_adapter_registration_preserves_other_agents(self):
        other = self.base / "claude/CLAUDE.md"
        other.parent.mkdir()
        other.write_text("Existing Claude project context.\n")
        baseline = self.entry.read_bytes()
        result = self.invoke("adapt", "--agent", "claude_code", "--entry", str(other), "--apply")
        config = json.loads((self.root / "config.json").read_text())
        self.assertEqual(config["agents"]["codex"], self.config["agents"]["codex"])
        self.assertEqual(self.entry.read_bytes(), baseline)
        self.assertTrue(other.read_text().startswith("Existing Claude project context.\n"))
        self.assertFalse(result["adapters"][0]["native_load_verified"])

    def test_plan_detects_concurrent_change_and_rolls_back_partial_write(self):
        p = tool.Plan(self.root)
        a, b = self.root / "SPEC.md", self.entry
        original_a, original_b = a.read_bytes(), b.read_bytes()
        p.put(a, b"new source")
        a.write_bytes(b"concurrent user edit")
        with self.assertRaisesRegex(ValueError, "changed after read"):
            p.apply()
        self.assertEqual(a.read_bytes(), b"concurrent user edit")
        self.assertFalse((self.root / ".profile.lock").exists())
        a.write_bytes(original_a)
        p = tool.Plan(self.root)
        p.put(a, b"new source")
        p.put(b, b"new entry")
        original_writer = tool.atomic_write
        def failing_writer(path, data, mode=0o600):
            if path == b and data == b"new entry":
                raise OSError("simulated write failure")
            return original_writer(path, data, mode)
        with patch.object(tool, "atomic_write", failing_writer), self.assertRaisesRegex(OSError, "simulated"):
            p.apply()
        self.assertEqual(a.read_bytes(), original_a)
        self.assertEqual(b.read_bytes(), original_b)
        manifests = list((self.root / "backups").glob("*/manifest.json"))
        self.assertEqual(json.loads(manifests[-1].read_text())["status"], "rolled_back")


if __name__ == "__main__":
    unittest.main()
