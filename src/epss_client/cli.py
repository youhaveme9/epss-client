from __future__ import annotations

import argparse
import csv
import json
import sys
from typing import Any

from .cache_config import CacheConfig
from .client import EpssClient
from .client import EpssClientConfig


def _write_csv(rows: list[dict[str, Any]]) -> None:
    if not rows:
        return
    writer = csv.DictWriter(
        sys.stdout, fieldnames=sorted({k for r in rows for k in r.keys()})
    )
    writer.writeheader()
    for r in rows:
        writer.writerow(r)


def _print_output(obj: dict[str, Any], fmt: str) -> None:
    if fmt == "json":
        json.dump(obj, sys.stdout, indent=2, sort_keys=True)
        print()
    elif fmt == "csv":
        rows: list[dict[str, Any]] = (
            obj.get("data", []) if isinstance(obj, dict) else []
        )
        _write_csv(rows)
    else:
        print(json.dumps(obj, indent=2, sort_keys=True))


def _create_client(args: argparse.Namespace) -> EpssClient:
    """Create an EpssClient with cache configuration."""
    cache_config = None

    # Try to load cache configuration
    if hasattr(args, "cache_config_file") and args.cache_config_file:
        try:
            cache_config = CacheConfig.from_file(args.cache_config_file)
        except Exception as e:
            print(f"Warning: Failed to load cache config: {e}", file=sys.stderr)

    # Override with CLI options if provided
    if hasattr(args, "cache_backend") and args.cache_backend:
        if cache_config is None:
            cache_config = CacheConfig()
        cache_config.enabled = True
        cache_config.backend = args.cache_backend

    if hasattr(args, "cache_ttl") and args.cache_ttl is not None:
        if cache_config is None:
            cache_config = CacheConfig()
        cache_config.enabled = True
        cache_config.ttl = args.cache_ttl

    # Disable cache if requested
    if hasattr(args, "no_cache") and args.no_cache:
        cache_config = None

    # Create client config
    client_config = EpssClientConfig(cache_config=cache_config)

    return EpssClient(config=client_config)


def _parse_cache_args(p: argparse.ArgumentParser) -> None:
    """Add cache-related arguments to parser."""
    cache_group = p.add_argument_group("cache options")
    cache_group.add_argument(
        "--cache-config",
        dest="cache_config_file",
        help="Path to cache configuration file",
    )
    cache_group.add_argument(
        "--cache-backend",
        choices=["redis", "database", "file"],
        help="Cache backend to use",
    )
    cache_group.add_argument("--cache-ttl", type=int, help="Cache TTL in seconds")
    cache_group.add_argument(
        "--no-cache", action="store_true", help="Disable caching for this request"
    )


def _parse_common_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("--date", help="YYYY-MM-DD")
    p.add_argument("--scope", choices=["time-series"], help="Use time-series scope")
    p.add_argument("--order", help="Sorting order, e.g. !epss")
    p.add_argument(
        "--epss-gt", type=float, dest="epss_gt", help="Filter: epss greater than"
    )
    p.add_argument(
        "--percentile-gt",
        type=float,
        dest="percentile_gt",
        help="Filter: percentile greater than",
    )
    p.add_argument("--limit", type=int)
    p.add_argument("--offset", type=int)
    p.add_argument("--envelope", action="store_true")
    p.add_argument("--pretty", action="store_true")
    p.add_argument("--format", choices=["json", "csv"], default="json")
    _parse_cache_args(p)


def cmd_query(args: argparse.Namespace) -> int:
    with _create_client(args) as client:
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
            use_cache=not args.no_cache,
            cache_ttl=args.cache_ttl,
        )
        _print_output(resp, args.format)
    return 0


def cmd_get(args: argparse.Namespace) -> int:
    with _create_client(args) as client:
        resp = client.get(
            args.cve,
            date=args.date,
            scope=args.scope,
            envelope=args.envelope,
            pretty=args.pretty,
            use_cache=not args.no_cache,
            cache_ttl=args.cache_ttl,
        )
        _print_output(resp, args.format)
    return 0


def cmd_batch(args: argparse.Namespace) -> int:
    with _create_client(args) as client:
        resp = client.batch(
            args.cves,
            date=args.date,
            scope=args.scope,
            envelope=args.envelope,
            pretty=args.pretty,
            use_cache=not args.no_cache,
            cache_ttl=args.cache_ttl,
        )
        _print_output(resp, args.format)
    return 0


def cmd_top(args: argparse.Namespace) -> int:
    with _create_client(args) as client:
        resp = client.top(
            limit=args.limit or 100,
            order=args.order or "!epss",
            envelope=args.envelope,
            pretty=args.pretty,
            use_cache=not args.no_cache,
            cache_ttl=args.cache_ttl,
        )
        _print_output(resp, args.format)
    return 0


def cmd_cache_stats(args: argparse.Namespace) -> int:
    """Show cache statistics."""
    with _create_client(args) as client:
        stats = client.get_cache_stats()
        if stats is None:
            print("Cache is disabled or not configured", file=sys.stderr)
            return 1

        _print_output(stats, args.format)
    return 0


def cmd_cache_clear(args: argparse.Namespace) -> int:
    """Clear the cache."""
    with _create_client(args) as client:
        success = client.clear_cache()
        if success:
            print("Cache cleared successfully")
        else:
            print("Failed to clear cache", file=sys.stderr)
            return 1
    return 0


def cmd_cache_config(args: argparse.Namespace) -> int:
    """Show current cache configuration."""
    try:
        config = CacheConfig.load(args.cache_config_file)
        config_dict = {
            "enabled": config.enabled,
            "backend": config.backend,
            "ttl": config.ttl,
            "key_prefix": config.key_prefix,
            "compression": config.compression,
            "serialize_format": config.serialize_format,
        }

        if config.backend == "redis":
            config_dict["redis"] = {
                "host": config.redis.host,
                "port": config.redis.port,
                "db": config.redis.db,
                "max_connections": config.redis.max_connections,
            }
        elif config.backend == "database":
            config_dict["database"] = {
                "url": config.database.url,
                "table_name": config.database.table_name,
            }
        elif config.backend == "file":
            config_dict["file"] = {
                "directory": config.file.directory,
                "max_size_mb": config.file.max_size_mb,
                "format": config.file.format,
            }

        _print_output(config_dict, args.format)
        return 0
    except Exception as e:
        print(f"Error loading cache configuration: {e}", file=sys.stderr)
        return 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="epss", description="FIRST EPSS API CLI")
    sub = parser.add_subparsers(dest="cmd", required=True)

    # Query commands
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
    _parse_cache_args(p_top)
    p_top.set_defaults(func=cmd_top)

    # Cache commands
    p_cache = sub.add_parser("cache", help="Cache management commands")
    cache_sub = p_cache.add_subparsers(dest="cache_cmd", required=True)

    p_cache_stats = cache_sub.add_parser("stats", help="Show cache statistics")
    p_cache_stats.add_argument("--format", choices=["json", "csv"], default="json")
    _parse_cache_args(p_cache_stats)
    p_cache_stats.set_defaults(func=cmd_cache_stats)

    p_cache_clear = cache_sub.add_parser("clear", help="Clear cache")
    _parse_cache_args(p_cache_clear)
    p_cache_clear.set_defaults(func=cmd_cache_clear)

    p_cache_config = cache_sub.add_parser("config", help="Show cache configuration")
    p_cache_config.add_argument("--format", choices=["json", "csv"], default="json")
    _parse_cache_args(p_cache_config)
    p_cache_config.set_defaults(func=cmd_cache_config)

    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    sys.exit(main())
