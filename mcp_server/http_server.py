
"""Taiwan Data Lens remote MCP entrypoint.

Launch: python -m mcp_server.http_server
"""

import os
import uvicorn

# Reuse the exact tools registered by the local stdio server.
from .server import mcp


def main():
    host = "0.0.0.0"
    port = int(os.environ.get("PORT", "8000"))

    # FastMCP streamable HTTP is served at /mcp.
    app = mcp.streamable_http_app()

    uvicorn.run(
        app,
        host=host,
        port=port,
        workers=1,
        log_level="info",
    )


if __name__ == "__main__":
    main()
