"""Disposable-root tests for the explicitly selected insights knowledge store."""
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import profile_insights as insights
import profile_tool


class ProfileInsightsTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.root = self.base / "knowledge root"

    def invoke(self, *argv):
        args = insights.parser().parse_args(["--root", str(self.root), *argv])
        return insights.run(args)

    def record(self, kind="agent", **updates):
        value = {
            "title": "保留原话",
            "original": "  第一行原文  \n\n第二行\t\n",
            "background": "为什么这句话值得保留。",
            "notes": "用户补充与原文分开。",
            "source": {"kind": kind, "date": "2026-10-11", "platform": "Codex",
                       "agent": "GPT", "session_id": "session-1", "location": "turn 4"},
        }
        value.update(updates)
        return value

    def write_record(self, value, name="entry.json"):
        path = self.base / name
        path.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")
        return path

    def snapshot(self, root=None):
        root = root or self.root
        return {str(path.relative_to(root)): path.read_bytes()
                for path in root.rglob("*") if path.is_file()}

    def test_init_and_add_preview_do_not_write_until_apply(self):
        init_preview = self.invoke("init")
        self.assertFalse(init_preview["applied"])
        self.assertFalse(self.root.exists())

        source = self.write_record(self.record())
        add_preview = self.invoke("add", "--from", str(source))
        self.assertFalse(add_preview["applied"])
        self.assertTrue(add_preview["changes"])
        self.assertFalse(self.root.exists())

        result = self.invoke("add", "--from", str(source), "--apply")
        self.assertTrue(result["applied"])
        self.assertTrue((self.root / insights.TOPIC / "entries" /
                         (result["entry_id"] + ".md")).is_file())

    def test_original_whitespace_and_provenance_are_kept_separate(self):
        value = self.record("agent")
        rendered = insights.render(insights.normalize(value)).decode()
        quoted = rendered.split("## 核心原文\n\n", 1)[1].split("\n\n## 必要背景", 1)[0]
        recovered = "\n".join(line[2:] if line.startswith("> ") else line for line in quoted.split("\n"))
        self.assertEqual(recovered, value["original"])
        self.assertIn("## 必要背景\n\n" + value["background"], rendered)
        self.assertIn("## 我的补充\n\n" + value["notes"], rendered)
        self.assertIn("- 来源：agent\n- 平台：Codex\n- Agent：GPT", rendered)
        user = self.record("user")
        user_rendered = insights.render(insights.normalize(user)).decode()
        self.assertIn("- 来源：用户\n", user_rendered)
        self.assertNotIn("- 来源：agent\n", user_rendered)

    def test_add_is_idempotent_and_index_links_all_saved_entries(self):
        first_record = self.record("agent")
        first_path = self.write_record(first_record, "agent.json")
        first = self.invoke("add", "--from", str(first_path), "--apply")
        after_first = self.snapshot()
        again = self.invoke("add", "--from", str(first_path), "--apply")
        self.assertEqual(again["entry_id"], first["entry_id"])
        self.assertEqual(again["changes"], [])
        self.assertEqual(self.snapshot(), after_first)

        second_record = self.record("user", title="用户自己的想法",
                                    original="我希望这个想法留下。")
        second_path = self.write_record(second_record, "user.json")
        second = self.invoke("add", "--from", str(second_path), "--apply")
        index = (self.root / "knowledge/INDEX.md").read_text(encoding="utf-8")
        topic = (self.root / insights.TOPIC / "README.md").read_text(encoding="utf-8")
        for result in (first, second):
            link = "(entries/" + result["entry_id"] + ".md)"
            self.assertIn(link, topic)
            self.assertTrue((self.root / insights.TOPIC / "entries" /
                             (result["entry_id"] + ".md")).is_file())
        self.assertIn("(topics/" + insights.TOPIC.name + "/README.md)", index)
        self.assertEqual(topic.count("| 日期 | 论断或表达 | 来源 |"), 1)

    def test_read_queries_are_read_only_and_filter_entries(self):
        source = self.write_record(self.record())
        self.invoke("add", "--from", str(source), "--apply")
        before = self.snapshot()
        found = self.invoke("list", "--query", "第二行")
        missing = self.invoke("list", "--query", "not present")
        shown = self.invoke("show", found["entries"][0]["id"])
        self.assertEqual(len(found["entries"]), 1)
        self.assertEqual(missing["entries"], [])
        self.assertIn("第二行", shown["text"])
        self.assertEqual(self.snapshot(), before)

    def test_existing_unrelated_knowledge_files_remain_byte_identical(self):
        index = self.root / "knowledge/INDEX.md"
        index.parent.mkdir(parents=True)
        index.write_text("# Existing index\n\n| 主题 | 一句话摘要 |\n|---|---|\n| Keep | untouched legacy row |\n",
                         encoding="utf-8")
        protected = self.root / "knowledge/topics/002-existing/README.md"
        protected.parent.mkdir(parents=True)
        protected.write_bytes(b"# Existing topic\n\nDo not rewrite.\n")
        original_protected = protected.read_bytes()
        source = self.write_record(self.record())
        self.invoke("add", "--from", str(source), "--apply")
        self.assertIn(b"| Keep | untouched legacy row |", index.read_bytes())
        self.assertIn(b"# Existing index", index.read_bytes())
        self.assertEqual(protected.read_bytes(), original_protected)

    def test_conflicting_id_and_invalid_records_fail_without_writes(self):
        fixed = self.record()
        fixed["id"] = "20261011-fixed"
        path = self.write_record(fixed)
        self.invoke("add", "--from", str(path), "--apply")
        before = self.snapshot()
        changed = dict(fixed, original="different text")
        self.write_record(changed, "conflict.json")
        with self.assertRaisesRegex(FileExistsError, "different text"):
            self.invoke("add", "--from", str(self.base / "conflict.json"), "--apply")
        self.assertEqual(self.snapshot(), before)

        invalids = []
        unknown = self.record(); unknown["unexpected"] = "no"
        invalids.append(unknown)
        bad_date = self.record(); bad_date["source"] = dict(bad_date["source"], date="2026-02-30")
        invalids.append(bad_date)
        bad_kind = self.record(); bad_kind["source"] = dict(bad_kind["source"], kind="system")
        invalids.append(bad_kind)
        bad_id = self.record(); bad_id["id"] = "../escape"
        invalids.append(bad_id)
        for number, value in enumerate(invalids):
            bad_path = self.write_record(value, "bad-%d.json" % number)
            with self.subTest(number=number):
                with self.assertRaises((ValueError, OSError)):
                    self.invoke("add", "--from", str(bad_path), "--apply")
                self.assertEqual(self.snapshot(), before)

    def test_symlink_entry_path_is_rejected(self):
        self.root.mkdir()
        topic = self.root / insights.TOPIC
        topic.mkdir(parents=True)
        outside = self.base / "outside"
        outside.mkdir()
        (topic / "entries").symlink_to(outside, target_is_directory=True)
        before = self.snapshot()
        with self.assertRaisesRegex(ValueError, "symlink"):
            self.invoke("show", "20261011-safe")
        self.assertEqual(self.snapshot(), before)
        self.assertEqual(list(outside.iterdir()), [])

    def test_plan_rejects_concurrent_index_change_before_writing(self):
        plan, _ = insights.prepare(self.root, self.record())
        index = self.root / "knowledge/INDEX.md"
        index.parent.mkdir(parents=True)
        index.write_text("# concurrent edit\n", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "changed after read"):
            plan.apply()
        self.assertEqual(index.read_text(encoding="utf-8"), "# concurrent edit\n")
        self.assertFalse((self.root / ".profile.lock").exists())
        self.assertFalse((self.root / insights.TOPIC).exists())

    def test_partial_write_failure_restores_prior_files(self):
        source = self.write_record(self.record())
        plan, entry = insights.prepare(self.root, json.loads(source.read_text(encoding="utf-8")))
        before = self.snapshot()
        real_write = profile_tool.atomic_write

        def fail_entry(path, data, mode=0o600):
            if Path(path) == entry:
                raise OSError("simulated entry write failure")
            return real_write(path, data, mode)

        with patch.object(profile_tool, "atomic_write", side_effect=fail_entry):
            with self.assertRaisesRegex(OSError, "simulated"):
                plan.apply()
        after = self.snapshot()
        for path, contents in before.items():
            self.assertEqual(after[path], contents)
        self.assertNotIn("knowledge/INDEX.md", after)
        self.assertNotIn(str((self.root / insights.TOPIC / "README.md").relative_to(self.root)), after)
        self.assertNotIn(str(entry.relative_to(self.root)), after)
        backups = list((self.root / "backups").glob("*/manifest.json"))
        self.assertEqual(len(backups), 1)
        manifest = json.loads(backups[0].read_text(encoding="utf-8"))
        self.assertEqual(manifest["status"], "rolled_back")
        self.assertFalse((self.root / ".profile.lock").exists())


if __name__ == "__main__":
    unittest.main()
