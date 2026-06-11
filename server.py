"""
Entry point for the Confluence MCP server.

Run with:
    python server.py
or via MCP client configuration pointing to this file.
"""
from __future__ import annotations

import os
import sys

import confluence_mcp.tools  # noqa: F401 -- imports all modules to register MCP tools
from confluence_mcp.app import mcp

if __name__ == "__main__":
    missing = [v for v in ("CONFLUENCE_URL", "CONFLUENCE_PAT") if not os.environ.get(v)]
    if missing:
        print(
            f"ERROR: required environment variable(s) not set: {', '.join(missing)}",
            file=sys.stderr,
        )
        sys.exit(1)

    port = os.environ.get("PORT")
    if port:
        mcp.run(transport="streamable-http", host="0.0.0.0", port=int(port))
    else:
        mcp.run(transport="stdio")
