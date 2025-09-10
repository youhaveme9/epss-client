from __future__ import annotations

import logging

from .cache_backends import DatabaseCache
from .cache_backends import FileCache
from .cache_backends import RedisCache
from .cache_config import CacheConfig
from .cache_interface import CacheInterface
from .cache_interface import CacheKeyGenerator
from .cache_interface import CacheStats
from .cache_interface import NoOpCache
from .types import EpssResponse

logger = logging.getLogger(__name__)


class CacheManager:
    """
    Cache manager that provides a unified interface to different cache backends.

    Handles backend selection, error recovery, and statistics tracking.
    """

    def __init__(self, config: CacheConfig | None = None):
        self.config = config or CacheConfig()
        self.key_generator = CacheKeyGenerator(self.config.key_prefix)
        self.stats = CacheStats()
        self._cache: CacheInterface = self._create_cache_backend()

    def _create_cache_backend(self) -> CacheInterface:
        """Create the appropriate cache backend based on configuration."""
        if not self.config.enabled:
            logger.info("Cache is disabled, using NoOpCache")
            return NoOpCache()

        backend = self.config.backend

        try:
            if backend == "redis":
                logger.info("Initializing Redis cache backend")
                return RedisCache(self.config.redis)
            elif backend == "database":
                logger.info("Initializing Database cache backend")
                return DatabaseCache(self.config.database)
            elif backend == "file":
                logger.info("Initializing File cache backend")
                return FileCache(self.config.file)
            else:
                logger.error(f"Unknown cache backend: {backend}")
                return NoOpCache()

        except Exception as e:
            logger.error(f"Failed to initialize {backend} cache backend: {e}")
            logger.info("Falling back to NoOpCache")
            self.stats.record_error()
            return NoOpCache()

    def get_cache_key(self, method: str, **params) -> str:
        """Generate a cache key for the given method and parameters."""
        return self.key_generator.generate_key(method, params)

    def get(self, method: str, **params) -> EpssResponse | None:
        """
        Get cached response for the given method and parameters.

        Args:
            method: The API method name (query, get, batch, top)
            **params: The parameters passed to the method

        Returns:
            Cached response if found, None otherwise
        """
        if not self.config.enabled:
            return None

        try:
            key = self.get_cache_key(method, **params)
            result = self._cache.get(key)

            if result is not None:
                self.stats.record_hit()
                logger.debug(f"Cache hit for key: {key}")
                return result
            else:
                self.stats.record_miss()
                logger.debug(f"Cache miss for key: {key}")
                return None

        except Exception as e:
            logger.error(f"Cache get error: {e}")
            self.stats.record_error()
            return None

    def set(
        self, method: str, response: EpssResponse, ttl: int | None = None, **params
    ) -> bool:
        """
        Cache response for the given method and parameters.

        Args:
            method: The API method name
            response: The API response to cache
            ttl: Time to live in seconds (uses config default if None)
            **params: The parameters passed to the method

        Returns:
            True if cached successfully, False otherwise
        """
        if not self.config.enabled:
            return True  # Pretend success when disabled

        try:
            key = self.get_cache_key(method, **params)
            cache_ttl = ttl or self.config.ttl

            success = self._cache.set(key, response, cache_ttl)

            if success:
                self.stats.record_set()
                logger.debug(f"Cached response for key: {key} (TTL: {cache_ttl}s)")
            else:
                logger.warning(f"Failed to cache response for key: {key}")

            return success

        except Exception as e:
            logger.error(f"Cache set error: {e}")
            self.stats.record_error()
            return False

    def delete(self, method: str, **params) -> bool:
        """
        Delete cached response for the given method and parameters.

        Args:
            method: The API method name
            **params: The parameters passed to the method

        Returns:
            True if deleted successfully, False otherwise
        """
        if not self.config.enabled:
            return True

        try:
            key = self.get_cache_key(method, **params)
            success = self._cache.delete(key)

            if success:
                self.stats.record_delete()
                logger.debug(f"Deleted cache entry for key: {key}")

            return success

        except Exception as e:
            logger.error(f"Cache delete error: {e}")
            self.stats.record_error()
            return False

    def clear(self) -> bool:
        """
        Clear all cached responses.

        Returns:
            True if cleared successfully, False otherwise
        """
        if not self.config.enabled:
            return True

        try:
            success = self._cache.clear()

            if success:
                logger.info("Cache cleared successfully")
                # Reset stats
                self.stats = CacheStats()

            return success

        except Exception as e:
            logger.error(f"Cache clear error: {e}")
            self.stats.record_error()
            return False

    def exists(self, method: str, **params) -> bool:
        """
        Check if cached response exists for the given method and parameters.

        Args:
            method: The API method name
            **params: The parameters passed to the method

        Returns:
            True if cached entry exists, False otherwise
        """
        if not self.config.enabled:
            return False

        try:
            key = self.get_cache_key(method, **params)
            return self._cache.exists(key)

        except Exception as e:
            logger.error(f"Cache exists error: {e}")
            self.stats.record_error()
            return False

    def get_stats(self) -> dict:
        """Get cache statistics."""
        stats = self.stats.to_dict()
        stats.update(
            {
                "enabled": self.config.enabled,
                "backend": self.config.backend,
                "ttl": self.config.ttl,
            }
        )
        return stats

    def close(self) -> None:
        """Close cache manager and underlying cache backend."""
        try:
            self._cache.close()
            logger.info("Cache manager closed")
        except Exception as e:
            logger.error(f"Error closing cache manager: {e}")

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()


def create_cache_manager(config_file: str | None = None) -> CacheManager:
    """
    Factory function to create a cache manager with configuration.

    Args:
        config_file: Optional path to configuration file

    Returns:
        Configured CacheManager instance
    """
    try:
        config = CacheConfig.load(config_file)
        return CacheManager(config)
    except Exception as e:
        logger.error(f"Failed to load cache configuration: {e}")
        logger.info("Using default (disabled) cache configuration")
        return CacheManager(CacheConfig())  # Default disabled config
