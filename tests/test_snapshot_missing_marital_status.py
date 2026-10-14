from mcp_server.service import LensService


def test_snapshot_missing_marital_status_returns_structured_block():
    result = LensService().get_snapshot(
        metric="marital_status_share",
        geography="台北市",
        period="latest",
    )
    assert result["status"] == "BLOCK"
    assert result["validation"]["status"] == "BLOCK"
    assert result["validation"]["codes"] == ["MISSING_METRIC_PARAMETER"]
    assert result["validation"]["parameter"] == "marital_status"
    assert result["observation"] is None
