from __future__ import annotations

from typing import Any
from typing import Dict
from typing import Literal
from typing import Optional
from typing import TypedDict


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
    data: list[EpssRecord]


EpssResponse = Dict[str, Any]
Scope = Optional[Literal["time-series"]]
