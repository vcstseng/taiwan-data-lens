import pytest
from mcp_server.query_resolver import QueryResolver
from mcp_server.service import LensService

@pytest.fixture(scope="module")
def resolver():
    return QueryResolver()

@pytest.fixture(scope="module")
def service():
    s = LensService()
    yield s
    s.close()

@pytest.mark.parametrize("metric,period", [("total_population","11508"),("age_group_population","11508"),("marital_population","113"),("marriage_person_count","114"),("migration_flow_count","11508"),("total_fertility_rate","114")])
def test_latest_period(resolver,metric,period):
    result=resolver.latest_period(metric)
    assert result["status"]=="OK"
    assert result["period"]==period

@pytest.mark.parametrize("name,canonical,level", [("台北市","臺北市","county"),("台北市松山區","臺北市松山區","district"),("臺北市","臺北市","county"),("高雄市","高雄市","county")])
def test_geography(resolver,name,canonical,level):
    result=resolver.resolve_geography(name)
    assert result["status"]=="OK"
    assert result["geography"]==canonical
    assert result["geography_level"]==level

def test_unknown_metric(resolver):
    assert resolver.metric_contract("not_a_metric")["status"]=="BLOCK"

def test_unknown_geography(resolver):
    assert resolver.resolve_geography("不存在市")["status"]=="BLOCK"

def test_service_golden_path(service):
    result=service.get_snapshot("total_population","台北市")
    assert result["status"]=="OK"
    rows=result["observation"]["results"]
    assert len(rows)==1
    assert rows[0]["geography"]=="臺北市"
    assert rows[0]["period"]=="11508"
    assert rows[0]["metric_value"]==2421830.0

@pytest.mark.parametrize("metric,geography,expected", [("not_a_metric","台北市","BLOCK"),("total_population","不存在市","BLOCK"),("aging_speed","台北市","BLOCK"),("total_fertility_rate","台北市","BLOCK")])
def test_service_guards(service,metric,geography,expected):
    assert service.get_snapshot(metric,geography)["status"]==expected

def test_invalid_parameters(service):
    assert service.get_snapshot("total_population","台北市",parameters="invalid")["status"]=="BLOCK"

def test_no_data(service):
    assert service.get_snapshot("total_population","台北市",period="99912")["status"]=="NO_DATA"


@pytest.mark.parametrize("metric,expected_year", [
    ("marital_population", 113),
    ("marriage_person_count", 114),
])
def test_county_snapshot_is_scoped(service, metric, expected_year):
    result = service.get_snapshot(metric, "台北市")
    assert result["status"] == "OK", result
    rows = result["observation"]["results"]
    assert len(rows) == 1, rows
    assert rows[0]["geography"] == "臺北市", rows
    assert rows[0]["year"] == expected_year, rows
    assert rows[0]["metric_value"] > 0, rows
