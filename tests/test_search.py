import unittest
from mcp_server.core.search import search_code

class TestSearch(unittest.TestCase):
    def test_search_code_finds_matches(self):
        results = search_code("create_server", root=".", max_results=5)
        self.assertGreaterEqual(len(results), 1)
        first = results[0]
        self.assertIn("file", first)
        self.assertIn("line", first)
        self.assertIn("snippet", first)
        self.assertIn("create_server", first["matched_line"])

    def test_search_code_with_glob(self):
        results = search_code("FastMCP", root=".", glob_pattern="*.py", max_results=5)
        self.assertGreaterEqual(len(results), 1)
        for r in results:
            self.assertTrue(r["file"].endswith(".py"))

if __name__ == "__main__":
    unittest.main()
