"""FastMCP server definition and tool registration for McpServer."""

from __future__ import annotations

from fastmcp import FastMCP

from mcp_server.tools.code import register_code_tools


def create_server() -> FastMCP:
    """Creates and configures the McpServer FastMCP server."""
    mcp = FastMCP(
        name="mcpserver",
        instructions=(
            "Servidor MCP agnóstico de contexto de código. "
            "Proporciona herramientas quirúrgicas (repo_map, search_code, get_symbol, get_feature_pack) "
            "para explorar, diagnosticar y resolver tareas sin saturar la ventana de contexto de los modelos."
        ),
    )

    # Register tools
    register_code_tools(mcp)

    return mcp


# Global server instance
mcp_server = create_server()
