"""CLI entrypoint for running the MCP server."""

from __future__ import annotations

import argparse
import sys
import warnings

# Suppress deprecation warnings on stdout/stderr to keep stdio JSON-RPC transport clean
warnings.filterwarnings("ignore", category=DeprecationWarning)

from mcp_server.server import mcp_server


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the chatbot-domain MCP server.")
    parser.add_argument(
        "--transport",
        choices=["stdio", "sse", "streamable-http"],
        default="stdio",
        help="Transport mechanism to use (default: stdio)",
    )
    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="Host for network transports",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port for network transports",
    )

    args = parser.parse_args()

    if args.transport == "stdio":
        mcp_server.run(transport="stdio")
    else:
        mcp_server.run(transport=args.transport, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
