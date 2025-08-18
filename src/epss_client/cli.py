from __future__ import annotations

import argparse
import csv
import json
import sys
from typing import Any, Dict, Iterable, List

from .client import EpssClient


def _write_csv(rows: List[Dict[str, Any]]) -> None:
	if not rows:
		return
	writer = csv.DictWriter(sys.stdout, fieldnames=sorted({k for r in rows for k in r.keys()}))
	writer.writeheader()
	for r in rows:
		writer.writerow(r)


def _print_output(obj: Dict[str, Any], fmt: str) -> None:
	if fmt == "json":
		json.dump(obj, sys.stdout, indent=2, sort_keys=True)
		print()
	elif fmt == "csv":
		rows: List[Dict[str, Any]] = obj.get("data", []) if isinstance(obj, dict) else []
		_write_csv(rows)
	else:
		print(json.dumps(obj, indent=2, sort_keys=True))


def _parse_common_args(p: argparse.ArgumentParser) -> None:
	p.add_argument("--date", help="YYYY-MM-DD")
	p.add_argument("--scope", choices=["time-series"], help="Use time-series scope")
	p.add_argument("--order", help="Sorting order, e.g. !epss")
	p.add_argument("--epss-gt", type=float, dest="epss_gt", help="Filter: epss greater than")
	p.add_argument("--percentile-gt", type=float, dest="percentile_gt", help="Filter: percentile greater than")
	p.add_argument("--limit", type=int)
	p.add_argument("--offset", type=int)
	p.add_argument("--envelope", action="store_true")
	p.add_argument("--pretty", action="store_true")
	p.add_argument("--format", choices=["json", "csv"], default="json")


def cmd_query(args: argparse.Namespace) -> int:
	client = EpssClient()
	resp = client.query(
		date=args.date,
		scope=args.scope,
		order=args.order,
		epss_gt=args.epss_gt,
		percentile_gt=args.percentile_gt,
		limit=args.limit,
		offset=args.offset,
		envelope=args.envelope,
		pretty=args.pretty,
	)
	_print_output(resp, args.format)
	return 0


def cmd_get(args: argparse.Namespace) -> int:
	client = EpssClient()
	resp = client.get(args.cve, date=args.date, scope=args.scope, envelope=args.envelope, pretty=args.pretty)
	_print_output(resp, args.format)
	return 0


def cmd_batch(args: argparse.Namespace) -> int:
	client = EpssClient()
	resp = client.batch(args.cves, date=args.date, scope=args.scope, envelope=args.envelope, pretty=args.pretty)
	_print_output(resp, args.format)
	return 0


def cmd_top(args: argparse.Namespace) -> int:
	client = EpssClient()
	resp = client.top(limit=args.limit or 100, order=args.order or "!epss", envelope=args.envelope, pretty=args.pretty)
	_print_output(resp, args.format)
	return 0


def main(argv: List[str] | None = None) -> int:
	parser = argparse.ArgumentParser(prog="epss", description="FIRST EPSS API CLI")
	sub = parser.add_subparsers(dest="cmd", required=True)

	p_query = sub.add_parser("query", help="Generic query")
	_parse_common_args(p_query)
	p_query.set_defaults(func=cmd_query)

	p_get = sub.add_parser("get", help="Get a single CVE")
	p_get.add_argument("cve")
	_parse_common_args(p_get)
	p_get.set_defaults(func=cmd_get)

	p_batch = sub.add_parser("batch", help="Batch CVEs")
	p_batch.add_argument("cves", nargs="+")
	_parse_common_args(p_batch)
	p_batch.set_defaults(func=cmd_batch)

	p_top = sub.add_parser("top", help="Top N CVEs by EPSS score")
	p_top.add_argument("--limit", type=int, default=100)
	p_top.add_argument("--order", default="!epss")
	p_top.add_argument("--format", choices=["json", "csv"], default="json")
	p_top.add_argument("--envelope", action="store_true")
	p_top.add_argument("--pretty", action="store_true")
	p_top.set_defaults(func=cmd_top)

	args = parser.parse_args(argv)
	return int(args.func(args))


if __name__ == "__main__":
	sys.exit(main())
