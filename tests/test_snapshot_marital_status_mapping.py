
from mcp_server.service import LensService


def test_snapshot_marital_status_uses_parameter_only(monkeypatch):
    captured = {}

    def fake_explore(self, plan):
        captured.update(plan)
        return {
            "status": "OK",
            "observation": {
                "results": [{"metric_value": 1.0}]
            },
        }

    monkeypatch.setattr(LensService, "explore_data", fake_explore)

    result = LensService().get_snapshot(
        "marital_status_share",
        "台北市",
        "113",
        {"marital_status": "未婚"},
    )

    assert result["status"] == "OK"
    assert captured["parameters"] == {"marital_status": "未婚"}
    assert "filters" not in captured
    assert captured["scope"] == {
        "geography": "臺北市",
        "geography_level": "county",
    }
