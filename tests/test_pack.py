import unittest
from mcp_server.core.pack import build_repo_map, build_feature_pack

class TestPack(unittest.TestCase):
    def test_build_repo_map(self):
        map_text = build_repo_map(".")
        self.assertIn("Mapa del repo", map_text)
        self.assertIn("mcp_server", map_text)

    def test_build_feature_pack(self):
        pack = build_feature_pack(
            task="Configurar el servidor MCP de dominio",
            root=".",
            budget=8000,
            symbols=["create_server"],
            files=["mcp_server/server.py"],
        )
        self.assertIn("# Context pack:", pack)
        self.assertIn("create_server", pack)
        self.assertIn("server.py", pack)

if __name__ == "__main__":
    unittest.main()
