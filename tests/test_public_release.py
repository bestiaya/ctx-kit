"""Release guard tests use synthetic material and isolated Git indexes."""
import importlib.util
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("check_public", ROOT / "scripts/check_public.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

class PublicReleaseTests(unittest.TestCase):
    def test_private_paths_and_synthetic_tokens_are_rejected(self):
        self.assertTrue(module.inspect_entry("cases/private.md", b"local work"))
        self.assertTrue(module.inspect_entry("config.txt", b"sk-ant-" + b"z" * 32))
        self.assertTrue(module.inspect_entry("config.txt", b"-----BEGIN " + b"PRIVATE KEY-----"))
        self.assertEqual(module.inspect_entry(".env.example", b"API_KEY=your-key"), [])

    def test_index_not_working_copy_is_audited(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            subprocess.run(["git", "init", str(root)], check=True, capture_output=True)
            p = root / "sample.txt"
            p.write_bytes(b"sk-ant-" + b"z" * 32)
            subprocess.run(["git", "-C", str(root), "add", "sample.txt"], check=True)
            p.write_text("safe working copy")
            self.assertTrue(module.check(root)[1])
            subprocess.run(["git", "-C", str(root), "add", "sample.txt"], check=True)
            p.write_bytes(b"sk-ant-" + b"z" * 32)
            self.assertEqual(module.check(root)[1], [])

if __name__ == "__main__":
    unittest.main()
