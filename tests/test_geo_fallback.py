from app.services import geo


def test_geo_falls_back_to_second_provider(monkeypatch):
    calls = []

    def first(_ip):
        calls.append("ip-api")
        return None

    def second(_ip):
        calls.append("ipapi.co")
        return geo.GeoResult(country="Türkiye", city="Konya", provider="ipapi.co")

    monkeypatch.setattr(geo, "_lookup_ip_api", first)
    monkeypatch.setattr(geo, "_lookup_ipapi_co", second)

    result = geo.enrich_ip("203.0.113.10")

    assert result.provider == "ipapi.co"
    assert result.country == "Türkiye"
    assert calls == ["ip-api", "ipapi.co"]


def test_geo_returns_empty_result_when_all_providers_fail(monkeypatch):
    monkeypatch.setattr(geo, "_lookup_ip_api", lambda _ip: None)
    monkeypatch.setattr(geo, "_lookup_ipapi_co", lambda _ip: None)

    result = geo.enrich_ip("203.0.113.10")

    assert result == geo.GeoResult()
