# EPSS Client

Typed Python client and CLI for the FIRST EPSS (Exploit Prediction Scoring System) API.

## Installation

```bash
pip install epss-client
```

## Quick start

```python
from epss_client import EpssClient

client = EpssClient()
# Single CVE
resp = client.query(cves=["CVE-2022-27225"])  # returns dict with data list
print(resp["data"][0])

# Batch
resp = client.query(cves=["CVE-2022-27225","CVE-2022-27223","CVE-2022-27218"]) 

# Time series (30 days)
resp = client.query(cves=["CVE-2022-25204"], scope="time-series")

# Top N by EPSS
resp = client.query(order="!epss", limit=100)

# Thresholds
resp = client.query(epss_gt=0.95)
resp = client.query(percentile_gt=0.95)

# Historic by date
resp = client.query(cves=["CVE-2022-26332"], date="2022-03-05")
```

### CLI

```bash
# Show first 100 CVEs
epss query --limit 100

# Single CVE
epss get CVE-2022-27225

# Batch
epss batch CVE-2022-27225 CVE-2022-27223 CVE-2022-27218

# Time series for 30 days
epss get CVE-2022-25204 --scope time-series

# Top 100
epss top --limit 100 --order !epss

# Above thresholds
epss query --epss-gt 0.95
epss query --percentile-gt 0.95

# Specific date
epss get CVE-2022-26332 --date 2022-03-05

# Output formats
epss query --limit 5 --format json
epss query --limit 5 --format csv > out.csv
```

## API coverage

This client wraps `https://api.first.org/data/v1/epss` including:
- single and batch CVE queries
- pagination with `offset` and `limit`
- filters: `date`, `scope=time-series`, `order`, `epss-gt`, `percentile-gt`
- optional `envelope` and `pretty`

See the official docs: `https://api.first.org/epss`.

## License

MIT
