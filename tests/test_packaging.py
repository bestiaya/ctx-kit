"""Behavior checks for movable bundles and boundaries; no account or model calls."""
import hashlib
import importlib.util
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from build_package import build_package
from check_kit import PROFILE_SCRIPTS, WORKFLOWS, link_errors, source_errors


def copy_publication_source(destination):
    """Independent fixture boundary: no live project records or generated bundles."""
    destination.mkdir()
    for name in ("README.md", "README.zh-CN.md", "LICENSE"):
        shutil.copyfile(ROOT / name, destination / name)
    for directory in ("docs", "workflows", "templates", "claude", "codex"):
        shutil.copytree(ROOT / directory, destination / directory,
                        ignore=shutil.ignore_patterns("__pycache__"))
    (destination / "scripts").mkdir()
    for name in PROFILE_SCRIPTS:
        shutil.copyfile(ROOT / "scripts" / name, destination / "scripts" / name)


class PackagingTests(unittest.TestCase):
    def test_both_platforms_survive_relocation_and_individual_skill_copy(self):
        with tempfile.TemporaryDirectory(prefix="context-kit-test-") as tmp:
            tmp = Path(tmp).resolve()
            for platform in ("claude", "codex"):
                original = tmp / f"original-{platform}"
                manifest = build_package(platform, original)
                moved = tmp / f"moved {platform}"
                original.rename(moved)
                self.assertEqual(link_errors(moved), [])
                self.assertEqual(json.loads((moved / "manifest.json").read_text()), manifest)
                for name, digest in manifest["files"].items():
                    self.assertEqual(hashlib.sha256((moved / name).read_bytes()).hexdigest(), digest)
                for name in WORKFLOWS:
                    alone = tmp / f"standalone-{platform}-{name}"
                    shutil.copytree(moved / "skills" / f"ctx-{name}", alone)
                    self.assertEqual(link_errors(alone), [])
                    if platform == "codex":
                        metadata = Path("agents/openai.yaml")
                        source = ROOT / "codex/setup/skills" / f"ctx-{name}" / metadata
                        self.assertEqual((alone / metadata).read_bytes(), source.read_bytes())
                    for path in alone.rglob("*.md"):
                        self.assertNotIn(str(ROOT), path.read_text())
                    if name == "profile":
                        for script_name in PROFILE_SCRIPTS:
                            self.assertEqual((alone / "scripts" / script_name).read_bytes(),
                                             (ROOT / "scripts" / script_name).read_bytes())
                        # Run an individually relocated skill against only a temporary root.
                        # Only the explicit fixture root is available to this invocation.
                        profile_root = tmp / f"profile-{platform}"
                        profile_root.mkdir()
                        (profile_root / "CONTEXT.md").write_text("# Relocation fixture\n")
                        (profile_root / "SPEC.md").write_text("# Fixture preferences\n")
                        (profile_root / "TOOLS.md").write_text("# Fixture tools\n")
                        (profile_root / "config.json").write_text(json.dumps({"schema_version": 1, "agents": {}}))
                        before = {p.name: p.read_bytes() for p in profile_root.iterdir()}
                        script = alone / "scripts/profile_tool.py"
                        result = subprocess.run([sys.executable, str(script), "--root", str(profile_root), "show"],
                                                cwd=tmp, env={}, capture_output=True, text=True)
                        self.assertEqual(result.returncode, 0, result.stderr)
                        self.assertIn("Relocation fixture", result.stdout)
                        self.assertEqual({p.name: p.read_bytes() for p in profile_root.iterdir()}, before)
                        history = subprocess.run([sys.executable, str(alone / "scripts/profile_history.py"), "--help"],
                                                 cwd=tmp, env={}, capture_output=True, text=True)
                        self.assertEqual(history.returncode, 0, history.stderr)
                if platform == "claude":
                    self.assertFalse((moved / "agents").exists())
                    self.assertIn("PreCompact", json.loads((moved / "hooks.json").read_text())["hooks"])
                    script = moved / "skills/ctx-checkup/scripts/cache-audit.py"
                    empty_logs = tmp / "empty-logs"
                    empty_logs.mkdir(exist_ok=True)
                    result = subprocess.run([sys.executable, str(script), "--project", str(empty_logs), "--all"], capture_output=True, text=True)
                    self.assertEqual(result.returncode, 0, result.stderr)
                    self.assertIn("项目目录", result.stdout)
                else:
                    self.assertFalse(list(moved.rglob("cache-audit.py")))
                    self.assertFalse((moved / "hooks.json").exists())
                    script = moved / "skills/ctx-checkup/scripts/token-audit.py"
                    self.assertTrue(script.is_file())
                    result = subprocess.run([sys.executable, str(script), "--help"],
                                            cwd=tmp, env={}, capture_output=True, text=True)
                    self.assertEqual(result.returncode, 0, result.stderr)
                    self.assertIn("--profile", result.stdout)

    def test_existing_output_and_symlink_are_never_overwritten(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "existing"
            output.mkdir()
            sentinel = output / "keep.txt"
            sentinel.write_text("existing user data")
            with self.assertRaises(FileExistsError):
                build_package("codex", output)
            self.assertEqual(sentinel.read_text(), "existing user data")
            link = Path(tmp) / "linked"
            link.symlink_to(output, target_is_directory=True)
            with self.assertRaises(FileExistsError):
                build_package("codex", link)
            self.assertTrue(link.is_symlink())
            dangling = Path(tmp) / "dangling"
            dangling.symlink_to(Path(tmp) / "absent")
            with self.assertRaises(FileExistsError):
                build_package("codex", dangling)

    def test_broken_source_is_rejected_before_output_creation(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "source"
            copy_publication_source(root)
            (root / "templates/CASE.md").unlink()
            output = Path(tmp) / "package"
            with self.assertRaisesRegex(ValueError, "source validation"):
                build_package("codex", output, root)
            self.assertFalse(output.exists())

    def test_private_records_and_partial_snapshots_do_not_block_or_enter_packages(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "source"
            copy_publication_source(root)
            for directory in ("_ops/DELIVERIES", "_ops/DELIVERIES/draft/docs", "cases", ".context-kit-uat", ".context-kit", ".context-kit/global-task"):
                path = root / directory / "private.md"
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("PRIVATE-REGRESSION-SENTINEL\n[personal](/outside/private.txt)\n[partial](missing.md)\n")
            self.assertEqual(source_errors(root), [])
            for platform in ("claude", "codex"):
                output = Path(tmp) / platform
                manifest = build_package(platform, output, root)
                for filename in manifest["files"]:
                    self.assertTrue(set(Path(filename).parts).isdisjoint({"_ops", "cases", ".context-kit-uat", ".context-kit"}))
                for path in output.rglob("*"):
                    if path.is_file():
                        self.assertNotIn(b"PRIVATE-REGRESSION-SENTINEL", path.read_bytes())
                        self.assertNotRegex(path.read_bytes(), rb"/(?:Users|home)/[A-Za-z0-9_.-]+/")

    def test_publication_links_still_reject_missing_escape_and_private_dependencies(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "source"
            copy_publication_source(root)
            private = root / "_ops/private.md"
            private.parent.mkdir()
            private.write_text("existing private evidence")
            outside = Path(tmp) / "outside.md"
            outside.write_text("existing outside evidence")
            original = (root / "docs/METHOD.md").read_text()
            for link, error in (("absent.md", "missing link"),
                                ("../../outside.md", "link escapes package"),
                                ("../_ops/private.md", "outside publication source")):
                with self.subTest(link=link):
                    (root / "docs/METHOD.md").write_text(original + f"\n[regression]({link})\n")
                    errors = source_errors(root)
                    self.assertTrue(any(error in item for item in errors), errors)
                    output = Path(tmp) / "rejected"
                    with self.assertRaisesRegex(ValueError, error):
                        build_package("codex", output, root)
                    self.assertFalse(output.exists())

    def test_all_shared_resource_copies_match_each_other_and_source(self):
        with tempfile.TemporaryDirectory() as tmp:
            copies = []
            for platform in ("claude", "codex"):
                output = Path(tmp) / platform
                build_package(platform, output)
                for name in WORKFLOWS:
                    reference = output / "skills" / f"ctx-{name}" / "references/context-kit"
                    files = {str(p.relative_to(reference)): p.read_bytes()
                             for p in reference.rglob("*") if p.is_file()}
                    copies.append(files)
                    for path, body in files.items():
                        self.assertEqual(body, (ROOT / path).read_bytes(), path)
            for files in copies[1:]:
                self.assertEqual(files, copies[0])
            self.assertIn("docs/METHOD.md", copies[0])

    def test_package_checks_do_not_exempt_record_named_directories(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            record = root / "_ops/DELIVERIES/private.md"
            record.parent.mkdir(parents=True)
            record.write_text("[missing](absent.md)\n[escape](../../../outside.md)\n")
            errors = link_errors(root)
            self.assertEqual(len(errors), 2)
            self.assertTrue(any("missing link" in e for e in errors))
            self.assertTrue(any("escapes" in e for e in errors))

    def test_link_checker_catches_missing_and_escaping_dependencies(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "skill"
            root.mkdir()
            (Path(tmp) / "outside.md").write_text("outside")
            (root / "SKILL.md").write_text("[missing](missing.md)\n[escape](../outside.md)\n")
            errors = link_errors(root)
            self.assertEqual(len(errors), 2)
            self.assertTrue(any("missing link" in error for error in errors))
            self.assertTrue(any("escapes" in error for error in errors))


class ClaudeAuditCompatibility(unittest.TestCase):
    def test_duplicate_events_new_material_and_rewrite_are_distinct(self):
        spec = importlib.util.spec_from_file_location("claude_audit", ROOT / "claude/setup/scripts/cache-audit.py")
        audit = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(audit)
        def event(mid, minute, read, write, out):
            return {"type": "assistant", "timestamp": f"2026-08-18T00:{minute:02}:00Z", "message": {"id": mid, "usage": {
                "input_tokens": 10, "cache_read_input_tokens": read,
                "cache_creation_input_tokens": write, "output_tokens": out}}}
        rows = [event("a", 0, 0, 200000, 100), event("a", 0, 0, 200000, 200),
                event("b", 1, 200000, 160000, 100), event("c", 2, 1000, 360000, 100)]
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "sample.jsonl"
            path.write_text("\n".join(json.dumps(row) for row in rows))
            result = audit.audit(str(path))
        self.assertEqual(result["n"], 3)
        self.assertEqual(result["rewrites"], 1)
        # Historical weights, not a current bill: one initial write, one expansion,
        # one cold rewrite, and deduplicated output counts.
        self.assertAlmostEqual(result["eq_m"], 1.46213)


if __name__ == "__main__":
    unittest.main()
