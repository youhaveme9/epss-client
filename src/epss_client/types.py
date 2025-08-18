from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional, TypedDict


class EpssRecord(TypedDict, total=False):
	cve: str
	epss: str  # string in API, can be parsed to float
	percentile: str  # string in API
	date: str  # YYYY-MM-DD


class EpssEnvelope(TypedDict, total=False):
	status: str
	"""e.g. OK"""

	status_code: int
	version: str
	access: str
	total: int
	offset: int
	limit: int
	data: List[EpssRecord]


EpssResponse = Dict[str, Any]
Scope = Optional[Literal["time-series"]]
