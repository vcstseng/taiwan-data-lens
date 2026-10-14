from mcp_server.service import LensService


def test_snapshot_invalid_marital_status_returns_structured_block():
    service = LensService()
    try:
        result = service.get_snapshot("marital_status_share", "台北市", "113", {"marital_status": "不存在的分類"})
        assert result["status"] == "BLOCK"
        assert result["validation"]["codes"] == ["INVALID_PARAMETER_VALUE"]
        assert result["validation"]["parameter"] == "marital_status"
        assert result["observation"] is None
    finally:
        service.close()
