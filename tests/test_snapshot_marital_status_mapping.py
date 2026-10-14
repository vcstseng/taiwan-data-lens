from mcp_server.service import LensService


def test_snapshot_marital_status_maps_parameter_to_filter(monkeypatch):
    captured = {}

    def fake_explore(self, plan):
        captured.update(plan)
        return {"status": "OK", "observation": {"results": [{"metric_value": 1.0}]}}

    monkeypatch.setattr(LensService, "explore_data", fake_explore)
    result = LensService().get_snapshot("marital_status_share", "台北市", "113", {"marital_status": "未婚"})
    assert result["status"] == "OK"
    assert captured["parameters"] == {"marital_status": "未婚"}
    assert captured["filters"] == {"marital_status": "未婚"}
