from dataclasses import dataclass

import requests


@dataclass(frozen=True)
class GeoResult:
    country: str | None = None
    city: str | None = None
    provider: str | None = None


TIMEOUT_SECONDS = 2.0


def enrich_ip(ip_address: str | None) -> GeoResult:
    if not ip_address:
        return GeoResult()

    result = _lookup_ip_api(ip_address)
    if result:
        return result

    result = _lookup_ipapi_co(ip_address)
    if result:
        return result

    return GeoResult()


def _lookup_ip_api(ip_address: str) -> GeoResult | None:
    try:
        response = requests.get(
            f"http://ip-api.com/json/{ip_address}",
            params={"fields": "status,country,city"},
            timeout=TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        payload = response.json()
        if payload.get("status") != "success":
            return None
        return GeoResult(
            country=payload.get("country"),
            city=payload.get("city"),
            provider="ip-api.com",
        )
    except (requests.RequestException, ValueError):
        return None


def _lookup_ipapi_co(ip_address: str) -> GeoResult | None:
    try:
        response = requests.get(
            f"https://ipapi.co/{ip_address}/json/",
            timeout=TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        payload = response.json()
        if payload.get("error"):
            return None
        return GeoResult(
            country=payload.get("country_name"),
            city=payload.get("city"),
            provider="ipapi.co",
        )
    except (requests.RequestException, ValueError):
        return None
