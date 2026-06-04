from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

import httpx

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class APIClientError(Exception):
    message: str

    def __str__(self) -> str:
        return self.message


class APIClient:
    def __init__(self, base_url: str, timeout: float = 20.0, retries: int = 3) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.retries = max(1, retries)

    def _request(self, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        last_error: Exception | None = None
        url = f"{self.base_url}{path}"
        for attempt in range(1, self.retries + 1):
            try:
                logger.debug("GET %s params=%s attempt=%s", url, params, attempt)
                with httpx.Client(timeout=self.timeout) as client:
                    response = client.get(url, params=params)
                    response.raise_for_status()
                    payload = response.json()
                    if not isinstance(payload, dict):
                        raise ValueError("expected JSON object response")
                    return payload
            except httpx.TimeoutException as exc:
                last_error = exc
                logger.warning("Timeout on %s (attempt %s/%s)", url, attempt, self.retries)
            except httpx.HTTPStatusError as exc:
                last_error = exc
                detail = exc.response.text.strip() or exc.response.reason_phrase
                if exc.response.status_code in {404, 400, 422}:
                    raise APIClientError(f"{exc.response.status_code} from {url}: {detail}") from exc
                logger.warning("HTTP error on %s (attempt %s/%s): %s", url, attempt, self.retries, detail)
            except (httpx.HTTPError, ValueError) as exc:
                last_error = exc
                logger.warning("Request failed for %s (attempt %s/%s): %s", url, attempt, self.retries, exc)

        raise APIClientError(f"Failed to fetch {url} after {self.retries} attempt(s): {last_error}")

    def get_assets(self, instrument_class: str | None = None, region: str | None = None) -> list[dict[str, Any]]:
        params: dict[str, Any] = {}
        if instrument_class:
            params["instrument_class"] = instrument_class
        if region:
            params["region"] = region
        payload = self._request("/api/v1/q2/assets", params=params or None)
        data = payload.get("data", [])
        return data if isinstance(data, list) else []

    def get_asset(self, symbol: str) -> dict[str, Any]:
        payload = self._request(f"/api/v1/q1/assets/{symbol}")
        data = payload.get("data", {})
        return data if isinstance(data, dict) else {}

    def get_data_sources(self) -> list[dict[str, Any]]:
        payload = self._request("/api/v1/q3/data-sources")
        data = payload.get("data", [])
        return data if isinstance(data, list) else []

    def get_timeseries(
        self,
        symbol: str,
        data_source_id: str | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
        limit: int = 1000,
    ) -> list[dict[str, Any]]:
        params: dict[str, Any] = {"limit": limit}
        if data_source_id:
            params["data_source_id"] = data_source_id
        if start_date:
            params["start_date"] = start_date
        if end_date:
            params["end_date"] = end_date
        payload = self._request(f"/api/v1/q4/time-series/{symbol}", params=params)
        data = payload.get("data", [])
        return data if isinstance(data, list) else []

    def get_latest_timeseries(self, data_source_id: str | None = None, limit: int = 1000) -> list[dict[str, Any]]:
        params: dict[str, Any] = {"limit": limit}
        if data_source_id:
            params["data_source_id"] = data_source_id
        payload = self._request("/api/v1/q5/latest-time-series", params=params)
        data = payload.get("data", [])
        return data if isinstance(data, list) else []

    def get_analytics(self, symbol: str) -> dict[str, Any]:
        return self._request(f"/analytics/{symbol}")
