
"""Launch: python -m mcp_server.server (local stdio MCP)."""

from pathlib import Path

# Preload pandas before MCP tools run. This avoids a reproducible first-query
# initialization stall observed in the local MCP stdio integration tests.
import pandas  # noqa: F401

from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings
from .service import LensService


# Load ChatGPT-facing instructions from a separate Markdown file.
# Resolve relative to this module so local and Railway launches behave alike.
INSTRUCTIONS_PATH = Path(__file__).resolve().with_name("instructions.md")
INSTRUCTIONS = INSTRUCTIONS_PATH.read_text(encoding="utf-8")


mcp = FastMCP(
    "Taiwan Data Lens",
    instructions=INSTRUCTIONS,
    transport_security=TransportSecuritySettings(
        enable_dns_rebinding_protection=True,
        allowed_hosts=[
            "127.0.0.1:*",
            "localhost:*",
            "[::1]:*",
            "taiwan-data-lens-production.up.railway.app",
        ],
    ),
)

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


@mcp.tool()
def get_snapshot(
    metric: str,
    geography: str,
    period: str = "latest",
    parameters: dict | None = None,
) -> dict:
    """Get one geographic metric snapshot without constructing a semantic plan.

    Use canonical metric IDs from discover_data. Geography accepts supported
    Taiwan county/district names, including 台/臺 aliases. period defaults to
    the latest available period for the source fact; an explicit period must
    use ROC year (YYY) or month (YYYMM), depending on the metric.
    Some metrics require parameters. Unsupported metric/geography combinations
    return BLOCK. NO_DATA is not zero. Do not invent missing observations.
    """
    return service.get_snapshot(metric, geography, period, parameters)


if __name__ == "__main__":
    try:
        mcp.run(transport="stdio")
    finally:
        service.close()
