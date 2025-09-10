from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Iterable

import requests

from .cache_config import CacheConfig
from .cache_manager import CacheManager
from .types import EpssResponse
from .types import Scope

logger = logging.getLogger(__name__)

_DEFAULT_BASE_URL = "https://api.first.org/data/v1/epss"


@dataclass
class EpssClientConfig:
    base_url: str = _DEFAULT_BASE_URL
    timeout: tuple[float, float] = (5.0, 30.0)
    user_agent: str = "first-epss/2.0.0 (+https://api.first.org/epss)"
    # Cache configuration (None = no caching)
    cache_config: CacheConfig | None = None


class EpssClient:
    """Minimal, typed client for the FIRST EPSS API.

    See https://api.first.org/epss for full API documentation.
    """

    def __init__(
        self,
        config: EpssClientConfig | None = None,
        session: requests.Session | None = None,
        cache_config: CacheConfig | None = None,
    ) -> None:
        self._config = config or EpssClientConfig()

        # Cache configuration can be provided directly or via client config
        if cache_config is not None:
            self._config.cache_config = cache_config

        # Initialize cache manager
        self._cache_manager = (
            CacheManager(self._config.cache_config)
            if self._config.cache_config
            else None
        )

        self._session = session or requests.Session()
        self._session.headers.setdefault("User-Agent", self._config.user_agent)
        self._session.headers.setdefault("Accept", "application/json")

    def _prepare_params(
        self,
        *,
        cves: Iterable[str] | None = None,
        date: str | None = None,
        scope: Scope = None,
        order: str | None = None,
        epss_gt: float | None = None,
        percentile_gt: float | None = None,
        limit: int | None = None,
        offset: int | None = None,
        envelope: bool = False,
        pretty: bool = False,
        extra: dict[str, str | int | float] | None = None,
    ) -> dict[str, str | int | float]:
        params: dict[str, str | int | float] = {}

        if cves:
            params["cve"] = ",".join(cves)
        if date:
            params["date"] = date
        if scope:
            params["scope"] = scope
        if order:
            params["order"] = order
        if epss_gt is not None:
            params["epss-gt"] = epss_gt
        if percentile_gt is not None:
            params["percentile-gt"] = percentile_gt
        if limit is not None:
            params["limit"] = limit
        if offset is not None:
            params["offset"] = offset
        if envelope:
            params["envelope"] = "true"
        if pretty:
            params["pretty"] = "true"
        if extra:
            params.update({k: v for k, v in extra.items() if v is not None})
        return params

    def query(
        self,
        *,
        cves: Iterable[str] | None = None,
        date: str | None = None,
        scope: Scope = None,
        order: str | None = None,
        epss_gt: float | None = None,
        percentile_gt: float | None = None,
        limit: int | None = None,
        offset: int | None = None,
        envelope: bool = False,
        pretty: bool = False,
        extra: dict[str, str | int | float] | None = None,
        use_cache: bool = True,
        cache_ttl: int | None = None,
    ) -> EpssResponse:
        """Run a generic EPSS query.

        Examples:
                - Recent CVEs: query(limit=100)
                - Single CVE: query(cves=["CVE-2022-27225"])
                - Batch: query(cves=[...])
                - Time series: query(cves=["CVE-..."], scope="time-series")
                - Top N: query(order="!epss", limit=100)
                - Thresholds: query(epss_gt=0.95) or query(percentile_gt=0.95)
                - Historic: query(cves=["CVE-..."], date="YYYY-MM-DD")

        Args:
                use_cache: Whether to use cache for this query (default: True)
                cache_ttl: Override default cache TTL for this query
        """
        # Prepare parameters for both API call and caching
        method_params = {
            "cves": list(cves) if cves else None,
            "date": date,
            "scope": scope,
            "order": order,
            "epss_gt": epss_gt,
            "percentile_gt": percentile_gt,
            "limit": limit,
            "offset": offset,
            "envelope": envelope,
            "pretty": pretty,
            "extra": extra,
        }

        # Check cache first if enabled and requested
        if use_cache and self._cache_manager:
            cached_response = self._cache_manager.get("query", **method_params)
            if cached_response is not None:
                logger.debug("Returning cached response for query")
                return cached_response

        # Prepare API request parameters
        params = self._prepare_params(
            cves=cves,
            date=date,
            scope=scope,
            order=order,
            epss_gt=epss_gt,
            percentile_gt=percentile_gt,
            limit=limit,
            offset=offset,
            envelope=envelope,
            pretty=pretty,
            extra=extra,
        )

        # Make API request
        logger.debug(
            f"Making API request to {self._config.base_url} with params: {params}"
        )
        response = self._session.get(
            self._config.base_url, params=params, timeout=self._config.timeout
        )
        response.raise_for_status()

        try:
            api_response = response.json()
        except json.JSONDecodeError as exc:
            raise RuntimeError("EPSS API returned invalid JSON") from exc

        # Cache the response if caching is enabled and requested
        if use_cache and self._cache_manager:
            self._cache_manager.set("query", api_response, cache_ttl, **method_params)

        return api_response

    # Convenience helpers
    def get(
        self,
        cve: str,
        *,
        date: str | None = None,
        scope: Scope = None,
        use_cache: bool = True,
        cache_ttl: int | None = None,
        **kwargs: object,
    ) -> EpssResponse:
        """Get EPSS data for a single CVE."""
        return self.query(
            cves=[cve],
            date=date,
            scope=scope,
            use_cache=use_cache,
            cache_ttl=cache_ttl,
            **kwargs,
        )  # type: ignore[arg-type]

    def batch(
        self,
        cves: Iterable[str],
        *,
        date: str | None = None,
        scope: Scope = None,
        use_cache: bool = True,
        cache_ttl: int | None = None,
        **kwargs: object,
    ) -> EpssResponse:
        """Get EPSS data for multiple CVEs."""
        return self.query(
            cves=list(cves),
            date=date,
            scope=scope,
            use_cache=use_cache,
            cache_ttl=cache_ttl,
            **kwargs,
        )  # type: ignore[arg-type]

    def top(
        self,
        *,
        limit: int = 100,
        order: str = "!epss",
        use_cache: bool = True,
        cache_ttl: int | None = None,
        **kwargs: object,
    ) -> EpssResponse:
        """Get top CVEs by EPSS score."""
        return self.query(
            limit=limit, order=order, use_cache=use_cache, cache_ttl=cache_ttl, **kwargs
        )  # type: ignore[arg-type]

    # Cache management methods
    def get_cache_stats(self) -> dict[str, str | int | float] | None:
        """Get cache statistics if caching is enabled."""
        if self._cache_manager:
            return self._cache_manager.get_stats()
        return None

    def clear_cache(self) -> bool:
        """Clear all cached responses."""
        if self._cache_manager:
            return self._cache_manager.clear()
        return True  # Success if no cache to clear

    def close(self) -> None:
        """Close the client and clean up resources."""
        if self._cache_manager:
            self._cache_manager.close()

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
