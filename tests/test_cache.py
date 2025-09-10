from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from epss_client import CacheConfig
from epss_client import EpssClient
from epss_client import EpssClientConfig
from epss_client.cache_backends import FileCache
from epss_client.cache_interface import CacheKeyGenerator
from epss_client.cache_interface import CacheStats
from epss_client.cache_interface import NoOpCache
from epss_client.cache_manager import CacheManager


class TestCacheKeyGenerator(unittest.TestCase):
    """Test cache key generation."""

    def setUp(self):
        self.generator = CacheKeyGenerator("test")

    def test_basic_key_generation(self):
        """Test basic cache key generation."""
        key = self.generator.generate_key("query", {"limit": 100})
        self.assertTrue(key.startswith("test:query:"))
        self.assertTrue(key.endswith(":current"))

    def test_date_in_key(self):
        """Test that date is included in cache key."""
        key = self.generator.generate_key("query", {"limit": 100, "date": "2024-01-01"})
        self.assertTrue(key.endswith(":2024-01-01"))

    def test_consistent_keys(self):
        """Test that same parameters produce same key."""
        params = {"limit": 100, "order": "!epss"}
        key1 = self.generator.generate_key("query", params)
        key2 = self.generator.generate_key("query", params)
        self.assertEqual(key1, key2)

    def test_different_params_different_keys(self):
        """Test that different parameters produce different keys."""
        key1 = self.generator.generate_key("query", {"limit": 100})
        key2 = self.generator.generate_key("query", {"limit": 200})
        self.assertNotEqual(key1, key2)

    def test_none_values_filtered(self):
        """Test that None values are filtered out."""
        params_with_none = {"limit": 100, "order": None, "date": None}
        params_without_none = {"limit": 100}

        key1 = self.generator.generate_key("query", params_with_none)
        key2 = self.generator.generate_key("query", params_without_none)
        self.assertEqual(key1, key2)


class TestCacheStats(unittest.TestCase):
    """Test cache statistics tracking."""

    def setUp(self):
        self.stats = CacheStats()

    def test_initial_stats(self):
        """Test initial state of stats."""
        self.assertEqual(self.stats.hits, 0)
        self.assertEqual(self.stats.misses, 0)
        self.assertEqual(self.stats.sets, 0)
        self.assertEqual(self.stats.deletes, 0)
        self.assertEqual(self.stats.errors, 0)
        self.assertEqual(self.stats.hit_rate, 0.0)

    def test_hit_rate_calculation(self):
        """Test hit rate calculation."""
        self.stats.record_hit()
        self.stats.record_hit()
        self.stats.record_miss()

        self.assertEqual(self.stats.hits, 2)
        self.assertEqual(self.stats.misses, 1)
        self.assertEqual(self.stats.hit_rate, 2 / 3)

    def test_to_dict(self):
        """Test stats conversion to dictionary."""
        self.stats.record_hit()
        self.stats.record_set()

        stats_dict = self.stats.to_dict()
        self.assertIn("hits", stats_dict)
        self.assertIn("hit_rate", stats_dict)
        self.assertIn("uptime", stats_dict)
        self.assertEqual(stats_dict["hits"], 1)
        self.assertEqual(stats_dict["sets"], 1)


class TestNoOpCache(unittest.TestCase):
    """Test NoOpCache implementation."""

    def setUp(self):
        self.cache = NoOpCache()

    def test_get_always_none(self):
        """Test that get always returns None."""
        result = self.cache.get("any_key")
        self.assertIsNone(result)

    def test_set_always_true(self):
        """Test that set always returns True."""
        result = self.cache.set("key", {"data": "value"})
        self.assertTrue(result)

    def test_exists_always_false(self):
        """Test that exists always returns False."""
        result = self.cache.exists("any_key")
        self.assertFalse(result)

    def test_delete_always_true(self):
        """Test that delete always returns True."""
        result = self.cache.delete("any_key")
        self.assertTrue(result)

    def test_clear_always_true(self):
        """Test that clear always returns True."""
        result = self.cache.clear()
        self.assertTrue(result)


class TestFileCache(unittest.TestCase):
    """Test file-based cache implementation."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        from epss_client.cache_config import FileConfig

        self.config = FileConfig(
            directory=self.temp_dir,
            max_size_mb=1,  # Small size for testing
            compression=False,  # Disable for simpler testing
            format="json",
        )
        self.cache = FileCache(self.config)

    def tearDown(self):
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_set_and_get(self):
        """Test setting and getting cached values."""
        test_data = {"status": "OK", "data": [{"cve": "CVE-2023-1234", "epss": "0.5"}]}

        success = self.cache.set("test_key", test_data)
        self.assertTrue(success)

        retrieved = self.cache.get("test_key")
        self.assertEqual(retrieved, test_data)

    def test_get_nonexistent_key(self):
        """Test getting non-existent key returns None."""
        result = self.cache.get("nonexistent_key")
        self.assertIsNone(result)

    def test_exists(self):
        """Test exists functionality."""
        test_data = {"data": "value"}

        self.assertFalse(self.cache.exists("test_key"))

        self.cache.set("test_key", test_data)
        self.assertTrue(self.cache.exists("test_key"))

    def test_delete(self):
        """Test delete functionality."""
        test_data = {"data": "value"}

        self.cache.set("test_key", test_data)
        self.assertTrue(self.cache.exists("test_key"))

        success = self.cache.delete("test_key")
        self.assertTrue(success)
        self.assertFalse(self.cache.exists("test_key"))

    def test_clear(self):
        """Test clear functionality."""
        self.cache.set("key1", {"data": "value1"})
        self.cache.set("key2", {"data": "value2"})

        self.assertTrue(self.cache.exists("key1"))
        self.assertTrue(self.cache.exists("key2"))

        success = self.cache.clear()
        self.assertTrue(success)

        self.assertFalse(self.cache.exists("key1"))
        self.assertFalse(self.cache.exists("key2"))


class TestCacheConfig(unittest.TestCase):
    """Test cache configuration loading and creation."""

    def test_default_config(self):
        """Test default configuration."""
        config = CacheConfig()
        self.assertFalse(config.enabled)
        self.assertEqual(config.backend, "file")
        self.assertEqual(config.ttl, 3600)
        self.assertEqual(config.key_prefix, "epss")

    def test_from_dict(self):
        """Test creating config from dictionary."""
        data = {
            "cache": {
                "enabled": True,
                "backend": "redis",
                "ttl": 7200,
                "redis": {"host": "redis.example.com", "port": 6380},
            }
        }

        config = CacheConfig.from_dict(data)
        self.assertTrue(config.enabled)
        self.assertEqual(config.backend, "redis")
        self.assertEqual(config.ttl, 7200)
        self.assertEqual(config.redis.host, "redis.example.com")
        self.assertEqual(config.redis.port, 6380)

    def test_from_env(self):
        """Test loading config from environment variables."""
        with patch.dict(
            "os.environ",
            {
                "EPSS_CACHE_ENABLED": "true",
                "EPSS_CACHE_BACKEND": "database",
                "EPSS_CACHE_TTL": "1800",
                "EPSS_CACHE_DATABASE_URL": "sqlite:///test.db",
            },
        ):
            config = CacheConfig.from_env()
            self.assertTrue(config.enabled)
            self.assertEqual(config.backend, "database")
            self.assertEqual(config.ttl, 1800)
            self.assertEqual(config.database.url, "sqlite:///test.db")


class TestCacheManager(unittest.TestCase):
    """Test cache manager functionality."""

    def setUp(self):
        self.config = CacheConfig(enabled=True, backend="file", ttl=3600)
        # Use a temporary directory
        self.temp_dir = tempfile.mkdtemp()
        self.config.file.directory = self.temp_dir

        self.manager = CacheManager(self.config)

    def tearDown(self):
        self.manager.close()
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_cache_key_generation(self):
        """Test cache key generation through manager."""
        key = self.manager.get_cache_key("query", limit=100, order="!epss")
        self.assertTrue(key.startswith("epss:query:"))

    def test_get_set_cycle(self):
        """Test complete get/set cycle."""
        test_response = {"status": "OK", "data": []}
        params = {"limit": 100, "cves": ["CVE-2023-1234"]}

        # Initially should be cache miss
        result = self.manager.get("query", **params)
        self.assertIsNone(result)

        # Set the value
        success = self.manager.set("query", test_response, **params)
        self.assertTrue(success)

        # Should now be cache hit
        result = self.manager.get("query", **params)
        self.assertEqual(result, test_response)

    def test_stats_tracking(self):
        """Test that statistics are tracked correctly."""
        test_response = {"data": []}
        params = {"limit": 100}

        # Cache miss
        self.manager.get("query", **params)
        stats = self.manager.get_stats()
        self.assertEqual(stats["misses"], 1)
        self.assertEqual(stats["hits"], 0)

        # Set and hit
        self.manager.set("query", test_response, **params)
        self.manager.get("query", **params)

        stats = self.manager.get_stats()
        self.assertEqual(stats["misses"], 1)
        self.assertEqual(stats["hits"], 1)
        self.assertEqual(stats["sets"], 1)

    def test_disabled_cache(self):
        """Test behavior when cache is disabled."""
        disabled_config = CacheConfig(enabled=False)
        manager = CacheManager(disabled_config)

        # Should always return None for get
        result = manager.get("query", limit=100)
        self.assertIsNone(result)

        # Set should succeed but not actually cache
        success = manager.set("query", {"data": []}, limit=100)
        self.assertTrue(success)

        # Still should return None
        result = manager.get("query", limit=100)
        self.assertIsNone(result)

    def test_clear_cache(self):
        """Test clearing cache."""
        test_response = {"data": []}
        self.manager.set("query", test_response, limit=100)

        # Verify it's cached
        result = self.manager.get("query", limit=100)
        self.assertIsNotNone(result)

        # Clear cache
        success = self.manager.clear()
        self.assertTrue(success)

        # Should now be cache miss
        result = self.manager.get("query", limit=100)
        self.assertIsNone(result)


class TestEpssClientCaching(unittest.TestCase):
    """Test caching integration in EpssClient."""

    def setUp(self):
        # Create a cache config with file backend
        self.temp_dir = tempfile.mkdtemp()
        cache_config = CacheConfig(enabled=True, backend="file", ttl=3600)
        cache_config.file.directory = self.temp_dir

        self.client_config = EpssClientConfig(cache_config=cache_config)

    def tearDown(self):
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    @patch("requests.Session.get")
    def test_cache_integration(self, mock_get):
        """Test that caching works with actual client calls."""
        # Mock API response
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {
            "status": "OK",
            "data": [{"cve": "CVE-2023-1234", "epss": "0.5", "percentile": "0.8"}],
        }
        mock_get.return_value = mock_response

        client = EpssClient(config=self.client_config)

        # First call should hit the API
        result1 = client.get("CVE-2023-1234")
        self.assertEqual(mock_get.call_count, 1)

        # Second call should hit the cache
        result2 = client.get("CVE-2023-1234")
        self.assertEqual(mock_get.call_count, 1)  # Still 1, not 2

        # Results should be identical
        self.assertEqual(result1, result2)

    @patch("requests.Session.get")
    def test_cache_bypass(self, mock_get):
        """Test bypassing cache when use_cache=False."""
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {"status": "OK", "data": []}
        mock_get.return_value = mock_response

        client = EpssClient(config=self.client_config)

        # First call with cache
        client.get("CVE-2023-1234", use_cache=True)
        self.assertEqual(mock_get.call_count, 1)

        # Second call bypassing cache
        client.get("CVE-2023-1234", use_cache=False)
        self.assertEqual(mock_get.call_count, 2)  # Should make another API call

    def test_cache_stats(self):
        """Test cache statistics functionality."""
        client = EpssClient(config=self.client_config)

        stats = client.get_cache_stats()
        self.assertIsNotNone(stats)
        self.assertIn("enabled", stats)
        self.assertIn("backend", stats)
        self.assertTrue(stats["enabled"])
        self.assertEqual(stats["backend"], "file")

    def test_cache_clear(self):
        """Test cache clearing functionality."""
        client = EpssClient(config=self.client_config)

        success = client.clear_cache()
        self.assertTrue(success)

    def test_no_cache_client(self):
        """Test client without caching enabled."""
        client = EpssClient()  # No cache config

        stats = client.get_cache_stats()
        self.assertIsNone(stats)

        success = client.clear_cache()
        self.assertTrue(success)  # Should succeed even without cache


if __name__ == "__main__":
    unittest.main()
