"""Launch: python -m mcp_server.server (local stdio MCP)."""

# Preload pandas before MCP tools run. This avoids a reproducible first-query
# initialization stall observed in the local MCP stdio integration tests.
import pandas  # noqa: F401

from mcp.server.fastmcp import FastMCP
from .service import LensService


mcp = FastMCP("Taiwan Data Lens")
service = LensService()


@mcp.tool()
def discover_data() -> dict:
    """Discover supported Taiwan public-data topics, metrics, and limitations; no query executed."""
    return service.discover_data()


@mcp.tool()
def get_story(stop_id: str | None = None) -> dict:
    """Get the curated Grand Tour or a stop by ID. Titles are not numeric evidence."""
    return service.get_story(stop_id)


@mcp.tool()
def explore_data(plan: dict) -> dict:
    """Execute a controlled semantic plan (operation, metric, scope, periods, filters).

    Never supply SQL, formula, joins, arbitrary expressions or unsupported claims.
    Every plan is checked by the canonical SemanticPlanValidator before execution.
    Do not treat BLOCK/REFRAME or empty results as factual observations.
    """
    return service.explore_data(plan)


if __name__ == "__main__":
    try:
        mcp.run(transport="stdio")
    finally:
        service.close()
