from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Dict, Iterable, Optional, Tuple, Union

import requests

from .types import EpssResponse, Scope

_DEFAULT_BASE_URL = "https://api.first.org/data/v1/epss"


@dataclass
class EpssClientConfig:
	base_url: str = _DEFAULT_BASE_URL
	timeout: Tuple[float, float] = (5.0, 30.0)
	user_agent: str = "first-epss/0.1.0 (+https://api.first.org/epss)"


class EpssClient:
	"""Minimal, typed client for the FIRST EPSS API.

	See https://api.first.org/epss for full API documentation.
	"""

	def __init__(self, config: Optional[EpssClientConfig] = None, session: Optional[requests.Session] = None) -> None:
		self._config = config or EpssClientConfig()
		self._session = session or requests.Session()
		self._session.headers.setdefault("User-Agent", self._config.user_agent)
		self._session.headers.setdefault("Accept", "application/json")

	def _prepare_params(
		self,
		*,
		cves: Optional[Iterable[str]] = None,
		date: Optional[str] = None,
		scope: Scope = None,
		order: Optional[str] = None,
		epss_gt: Optional[float] = None,
		percentile_gt: Optional[float] = None,
		limit: Optional[int] = None,
		offset: Optional[int] = None,
		envelope: bool = False,
		pretty: bool = False,
		extra: Optional[Dict[str, Union[str, int, float]]] = None,
	) -> Dict[str, Union[str, int, float]]:
		params: Dict[str, Union[str, int, float]] = {}

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
		cves: Optional[Iterable[str]] = None,
		date: Optional[str] = None,
		scope: Scope = None,
		order: Optional[str] = None,
		epss_gt: Optional[float] = None,
		percentile_gt: Optional[float] = None,
		limit: Optional[int] = None,
		offset: Optional[int] = None,
		envelope: bool = False,
		pretty: bool = False,
		extra: Optional[Dict[str, Union[str, int, float]]] = None,
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
		"""
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
		response = self._session.get(self._config.base_url, params=params, timeout=self._config.timeout)
		response.raise_for_status()
		try:
			return response.json()
		except json.JSONDecodeError as exc:
			raise RuntimeError("EPSS API returned invalid JSON") from exc

	# Convenience helpers
	def get(self, cve: str, *, date: Optional[str] = None, scope: Scope = None, **kwargs: object) -> EpssResponse:
		return self.query(cves=[cve], date=date, scope=scope, **kwargs)  # type: ignore[arg-type]

	def batch(self, cves: Iterable[str], *, date: Optional[str] = None, scope: Scope = None, **kwargs: object) -> EpssResponse:
		return self.query(cves=list(cves), date=date, scope=scope, **kwargs)  # type: ignore[arg-type]

	def top(self, *, limit: int = 100, order: str = "!epss", **kwargs: object) -> EpssResponse:
		return self.query(limit=limit, order=order, **kwargs)  # type: ignore[arg-type]
