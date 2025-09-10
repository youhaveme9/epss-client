# EPSS Client v2.0

Typed Python client and CLI for the FIRST EPSS (Exploit Prediction Scoring System) API with advanced caching support.

## Features

- **Fast & Typed**: Full type hints and optimized performance
- **Advanced Caching**: Redis, Database, and File-based caching
- **Configurable**: YAML/TOML configuration files + environment variables
- **Statistics**: Built-in cache performance monitoring
- **CLI Tools**: Comprehensive command-line interface

## Installation

```bash
pip install epss-client

# Optional: Install with caching support
pip install epss-client[cache-redis]     # Redis backend
pip install epss-client[cache-db]        # Database backend  
pip install epss-client[cache-full]      # All cache backends
pip install epss-client[config]          # Configuration file support
```

## Quick start

### Basic Usage (No Caching)

```python
from epss_client import EpssClient

client = EpssClient()

# Single CVE
resp = client.get("CVE-2022-27225")
print(resp["data"][0])

# Batch CVEs
resp = client.batch(["CVE-2022-27225","CVE-2022-27223","CVE-2022-27218"]) 

# Time series (30 days)
resp = client.get("CVE-2022-25204", scope="time-series")

# Top N by EPSS
resp = client.top(limit=100)

# Filters and thresholds
resp = client.query(epss_gt=0.95)
resp = client.query(percentile_gt=0.95)

# Historic by date
resp = client.get("CVE-2022-26332", date="2022-03-05")
```

### With Caching (New in v2.0!)

```python
from epss_client import EpssClient, EpssClientConfig, CacheConfig

# Configure file-based caching
cache_config = CacheConfig(
    enabled=True,
    backend="file",  # or "redis", "database"
    ttl=3600        # 1 hour cache
)

client_config = EpssClientConfig(cache_config=cache_config)
client = EpssClient(config=client_config)

# First call hits the API
resp1 = client.get("CVE-2022-27225")  # ~200ms

# Second call hits the cache  
resp2 = client.get("CVE-2022-27225")  # ~2ms - 100x faster!

# View cache statistics
stats = client.get_cache_stats()
print(f"Cache hit rate: {stats['hit_rate']:.1%}")

# Clear cache when needed
client.clear_cache()
```

## CLI Usage

### Basic Commands

```bash
# Single CVE
epss get CVE-2022-27225

# Multiple CVEs
epss batch CVE-2022-27225 CVE-2022-27223 CVE-2022-27218

# Top CVEs by EPSS score
epss top --limit 100

# Generic queries with filters
epss query --limit 100 --epss-gt 0.95
epss query --percentile-gt 0.95 --date 2022-03-05

# Time series data
epss get CVE-2022-25204 --scope time-series

# Output formats
epss query --limit 5 --format json
epss query --limit 5 --format csv > data.csv
```

### Cache Commands (New in v2.0!)

```bash
# Use caching with CLI options
epss get CVE-2022-27225 --cache-backend file --cache-ttl 3600

# Use configuration file
epss get CVE-2022-27225 --cache-config ~/.epss/config.yaml

# Disable cache for a single request
epss query --limit 100 --no-cache

# Cache management
epss cache stats                    # Show cache statistics
epss cache clear                    # Clear all cached data
epss cache config                   # Show current cache configuration
```

## Caching System

EPSS Client v2.0 introduces a powerful, configurable caching system that can significantly improve performance for repeated queries.

### Cache Backends

#### File Cache (Default)
```python
from epss_client import CacheConfig

config = CacheConfig(
    enabled=True,
    backend="file",
    ttl=3600,  # 1 hour
)
config.file.directory = "~/.cache/epss"
config.file.max_size_mb = 100
config.file.compression = True
```

#### Redis Cache
```python
config = CacheConfig(
    enabled=True,
    backend="redis",
    ttl=3600,
)
config.redis.host = "localhost"
config.redis.port = 6379
config.redis.db = 0
```

#### Database Cache
```python
config = CacheConfig(
    enabled=True,
    backend="database",
    ttl=3600,
)
# SQLite (default)
config.database.url = "sqlite:///~/.cache/epss/cache.db"
# Or PostgreSQL
# config.database.url = "postgresql://user:pass@localhost/epss"
```

### Configuration Files

Create `~/.epss/config.yaml`:

```yaml
cache:
  enabled: true
  backend: file  # or redis, database
  ttl: 3600
  
  file:
    directory: ~/.cache/epss
    max_size_mb: 100
    compression: true
    
  redis:
    host: localhost
    port: 6379
    db: 0
    
  database:
    url: sqlite:///~/.cache/epss/cache.db
    table_name: epss_cache
```

Load automatically:
```python
from epss_client import CacheConfig, EpssClient, EpssClientConfig

# Loads from ~/.epss/config.yaml, ./epss.yaml, or env vars
cache_config = CacheConfig.load()
client_config = EpssClientConfig(cache_config=cache_config)
client = EpssClient(config=client_config)
```

### Environment Variables

```bash
export EPSS_CACHE_ENABLED=true
export EPSS_CACHE_BACKEND=redis
export EPSS_CACHE_TTL=3600
export EPSS_CACHE_REDIS_HOST=localhost
export EPSS_CACHE_REDIS_PORT=6379
```

### Cache Statistics

```python
client = EpssClient(config=client_config)

# Make some cached requests
client.get("CVE-2022-27225")
client.get("CVE-2022-27225")  # Cache hit

# View statistics
stats = client.get_cache_stats()
print(f"Hit rate: {stats['hit_rate']:.1%}")
print(f"Total hits: {stats['hits']}")
print(f"Total misses: {stats['misses']}")
print(f"Cache backend: {stats['backend']}")
```

### Per-Request Cache Control

```python
# Disable cache for specific request
client.get("CVE-2022-27225", use_cache=False)

# Custom TTL for specific request
client.get("CVE-2022-27225", cache_ttl=7200)  # 2 hours

# Same for CLI
epss get CVE-2022-27225 --no-cache
epss get CVE-2022-27225 --cache-ttl 7200
```

## API Coverage

This client wraps `https://api.first.org/data/v1/epss` with complete support for:

- **Single & Batch Queries**: Individual CVEs or bulk operations
- **Time Series Data**: Historical EPSS scores over time  
- **Filtering & Sorting**: By date, score thresholds, custom ordering
- **Pagination**: Efficient handling of large datasets
- **Output Formats**: JSON and CSV export
- **Caching**: Intelligent caching with multiple backend options

### Supported Parameters
- `cves`: Single CVE or list of CVEs
- `date`: Specific date (YYYY-MM-DD format)
- `scope`: Use "time-series" for historical data
- `order`: Sort results (e.g., "!epss" for descending EPSS score)
- `epss_gt`: Filter by EPSS score greater than threshold
- `percentile_gt`: Filter by percentile greater than threshold  
- `limit` & `offset`: Pagination controls
- `envelope` & `pretty`: Response formatting options

See the official EPSS API documentation: https://api.first.org/epss

## License

MIT
