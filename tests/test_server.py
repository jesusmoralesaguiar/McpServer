import unittest
import asyncio
from mcp_server.server import create_server

class TestServer(unittest.TestCase):
    def test_server_creation_and_tools(self):
        server = create_server()
        self.assertEqual(server.name, "mcpserver")
        
        tool_names = [t.name for t in asyncio.run(server.list_tools())]
        self.assertIn("repo_map", tool_names)
        self.assertIn("search_code", tool_names)
        self.assertIn("get_symbol", tool_names)
        self.assertIn("get_feature_pack", tool_names)

    def test_tool_execution(self):
        async def _run():
            server = create_server()
            tool = await server.get_tool("repo_map")
            self.assertIsNotNone(tool)
            result = await tool.run(arguments={"path": "."})
            return result.content[0].text

        text = asyncio.run(_run())
        self.assertIn("Mapa del repo", text)
        self.assertIn("mcp_server", text)

if __name__ == "__main__":
    unittest.main()
