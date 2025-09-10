#!/usr/bin/env python3
"""
Demo script showing EPSS Client v2 caching functionality.

This script demonstrates:
1. Setting up caching configuration
2. Making cached API calls  
3. Viewing cache statistics
4. Different cache backends (file, Redis, database)
"""

import sys
from pathlib import Path
import time

# Add src to path for demo
sys.path.insert(0, str(Path(__file__).parent / "src"))

from epss_client import EpssClient, EpssClientConfig, CacheConfig


def demo_file_cache():
    """Demonstrate file-based caching."""
    print("=== File Cache Demo ===")
    
    # Configure file-based cache
    cache_config = CacheConfig(
        enabled=True,
        backend="file",
        ttl=300,  # 5 minutes
    )
    cache_config.file.directory = "/tmp/epss_demo_cache"
    cache_config.file.max_size_mb = 10
    
    client_config = EpssClientConfig(cache_config=cache_config)
    
    with EpssClient(config=client_config) as client:
        print("1. Making first API call (will hit EPSS API)...")
        start_time = time.time()
        result1 = client.get("CVE-2023-4911")  # Example CVE
        first_call_time = time.time() - start_time
        print(f"   First call took: {first_call_time:.3f} seconds")
        
        print("\n2. Making same API call again (should hit cache)...")
        start_time = time.time()
        result2 = client.get("CVE-2023-4911")
        second_call_time = time.time() - start_time
        print(f"   Second call took: {second_call_time:.3f} seconds")
        
        # Verify results are the same
        print(f"   Results identical: {result1 == result2}")
        print(f"   Cache speedup: {first_call_time / second_call_time:.1f}x faster")
        
        print("\n3. Cache statistics:")
        stats = client.get_cache_stats()
        if stats:
            print(f"   Cache enabled: {stats['enabled']}")
            print(f"   Backend: {stats['backend']}")
            print(f"   Hits: {stats['hits']}")
            print(f"   Misses: {stats['misses']}")
            print(f"   Hit rate: {stats['hit_rate']:.1%}")


def demo_cache_bypass():
    """Demonstrate cache bypass functionality."""
    print("\n=== Cache Bypass Demo ===")
    
    cache_config = CacheConfig(enabled=True, backend="file", ttl=300)
    cache_config.file.directory = "/tmp/epss_demo_cache"
    
    client_config = EpssClientConfig(cache_config=cache_config)
    
    with EpssClient(config=client_config) as client:
        print("1. Making cached call...")
        client.get("CVE-2023-1234", use_cache=True)
        
        print("2. Making same call with cache bypass...")
        client.get("CVE-2023-1234", use_cache=False)
        
        stats = client.get_cache_stats()
        print(f"   Total API calls made: {stats['misses']}")  # Both should be misses


def demo_multiple_backends():
    """Demonstrate different cache backend configurations."""
    print("\n=== Multiple Cache Backends Demo ===")
    
    backends = [
        ("File", CacheConfig(enabled=True, backend="file", ttl=300)),
        # Note: Redis and Database demos would require those services to be running
        # ("Redis", CacheConfig(enabled=True, backend="redis", ttl=300)), 
        # ("Database", CacheConfig(enabled=True, backend="database", ttl=300)),
    ]
    
    for name, config in backends:
        print(f"\n{name} Backend:")
        if name == "File":
            config.file.directory = f"/tmp/epss_demo_cache_{name.lower()}"
        
        try:
            client_config = EpssClientConfig(cache_config=config)
            with EpssClient(config=client_config) as client:
                client.get("CVE-2023-5678")
                stats = client.get_cache_stats()
                print(f"   ✓ {name} cache working - Backend: {stats['backend']}")
        except Exception as e:
            print(f"   ✗ {name} cache failed: {e}")


def demo_cli_integration():
    """Demonstrate CLI cache commands."""
    print("\n=== CLI Integration Demo ===")
    print("You can now use these CLI commands:")
    print("  epss get CVE-2023-4911 --cache-backend file")
    print("  epss cache stats")
    print("  epss cache clear") 
    print("  epss cache config")
    print("  epss query --limit 10 --cache-ttl 3600")
    print("  epss batch CVE-2023-1234 CVE-2023-5678 --no-cache")


def main():
    """Run all demos."""
    print("EPSS Client v2.0 - Caching Feature Demo")
    print("=" * 50)
    
    try:
        demo_file_cache()
        demo_cache_bypass()
        demo_multiple_backends()
        demo_cli_integration()
        
        print("\n" + "=" * 50)
        print("✅ Demo completed successfully!")
        print("\nFor more information, see:")
        print("- example_cache_config.yaml for configuration examples")
        print("- README.md for full documentation")
        
    except Exception as e:
        print(f"\n❌ Demo failed with error: {e}")
        print("Note: This demo requires internet connectivity to access EPSS API")
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
