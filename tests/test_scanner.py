import unittest
from mcp_server.core.scanner import is_secret, is_excluded, collect_files

class TestScanner(unittest.TestCase):
    def test_is_secret(self):
        self.assertTrue(is_secret(".env"))
        self.assertTrue(is_secret(".env.production"))
        self.assertTrue(is_secret("id_rsa"))
        self.assertTrue(is_secret("secret.key"))
        self.assertFalse(is_secret(".env.example"))
        self.assertFalse(is_secret("main.py"))

    def test_is_excluded(self):
        self.assertTrue(is_excluded("node_modules/package/index.js"))
        self.assertTrue(is_excluded(".venv/lib/python3.10/site.py"))
        self.assertTrue(is_excluded("__pycache__/main.cpython-310.pyc"))
        self.assertTrue(is_excluded("file.min.js"))
        self.assertFalse(is_excluded("src/components/App.tsx"))

    def test_collect_files(self):
        files = collect_files(".")
        self.assertGreater(len(files), 0)
        for f in files:
            self.assertFalse(is_secret(f))
            self.assertFalse(is_excluded(f))

if __name__ == "__main__":
    unittest.main()
