import unittest
from mcp_server.core.symbols import find_symbol, python_definitions

class TestSymbols(unittest.TestCase):
    def test_python_definitions(self):
        code = """
class MyClass:
    def method(self):
        pass

def top_function(x: int) -> int:
    return x * 2
"""
        defs = python_definitions(code)
        names = [d[0] for d in defs]
        self.assertIn("MyClass", names)
        self.assertIn("method", names)
        self.assertIn("top_function", names)

    def test_find_symbol(self):
        results = find_symbol("create_server", root=".")
        self.assertGreaterEqual(len(results), 1)
        match = results[0]
        self.assertIn("create_server", match["symbol"])
        self.assertIn("server.py", match["file"])
        self.assertGreater(match["start_line"], 0)

if __name__ == "__main__":
    unittest.main()
