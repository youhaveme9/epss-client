from __future__ import annotations

import hashlib
import json
import time
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, Union

from .types import EpssResponse


class CacheInterface(ABC):
    """Abstract interface for cache backends."""
    
    @abstractmethod
    def get(self, key: str) -> Optional[EpssResponse]:
        """Get cached value by key."""
        pass
    
    @abstractmethod
    def set(self, key: str, value: EpssResponse, ttl: Optional[int] = None) -> bool:
        """Set cached value with optional TTL in seconds."""
        pass
    
    @abstractmethod
    def delete(self, key: str) -> bool:
        """Delete cached value by key."""
        pass
    
    @abstractmethod
    def clear(self) -> bool:
        """Clear all cached values."""
        pass
    
    @abstractmethod
    def exists(self, key: str) -> bool:
        """Check if key exists in cache."""
        pass
    
    @abstractmethod
    def close(self) -> None:
        """Close cache connection/resources."""
        pass


class CacheKeyGenerator:
    """Utility class for generating consistent cache keys."""
    
    def __init__(self, prefix: str = "epss"):
        self.prefix = prefix
    
    def generate_key(
        self, 
        method: str, 
        params: Dict[str, Union[str, int, float, bool, None]]
    ) -> str:
        """
        Generate a consistent cache key from method and parameters.
        
        Args:
            method: The API method name (query, get, batch, top)
            params: The parameters passed to the method
            
        Returns:
            A cache key string
        """
        # Filter out None values and sort for consistency
        clean_params = {k: v for k, v in params.items() if v is not None}
        
        # Create a deterministic string representation
        param_str = json.dumps(clean_params, sort_keys=True, separators=(',', ':'))
        
        # Hash the parameters to create a shorter, consistent key
        param_hash = hashlib.md5(param_str.encode()).hexdigest()
        
        # Include date if present for proper cache invalidation
        date_suffix = f":{clean_params.get('date', 'current')}"
        
        return f"{self.prefix}:{method}:{param_hash}{date_suffix}"


class CacheStats:
    """Cache statistics tracking."""
    
    def __init__(self):
        self.hits = 0
        self.misses = 0
        self.sets = 0
        self.deletes = 0
        self.errors = 0
        self.start_time = time.time()
    
    def record_hit(self) -> None:
        """Record a cache hit."""
        self.hits += 1
    
    def record_miss(self) -> None:
        """Record a cache miss."""
        self.misses += 1
    
    def record_set(self) -> None:
        """Record a cache set operation."""
        self.sets += 1
    
    def record_delete(self) -> None:
        """Record a cache delete operation."""
        self.deletes += 1
    
    def record_error(self) -> None:
        """Record a cache error."""
        self.errors += 1
    
    @property
    def hit_rate(self) -> float:
        """Calculate cache hit rate."""
        total = self.hits + self.misses
        return self.hits / total if total > 0 else 0.0
    
    @property
    def uptime(self) -> float:
        """Calculate cache uptime in seconds."""
        return time.time() - self.start_time
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert stats to dictionary."""
        return {
            "hits": self.hits,
            "misses": self.misses,
            "sets": self.sets,
            "deletes": self.deletes,
            "errors": self.errors,
            "hit_rate": self.hit_rate,
            "uptime": self.uptime,
        }


class NoOpCache(CacheInterface):
    """No-operation cache that doesn't actually cache anything."""
    
    def get(self, key: str) -> Optional[EpssResponse]:
        """Always return None (cache miss)."""
        return None
    
    def set(self, key: str, value: EpssResponse, ttl: Optional[int] = None) -> bool:
        """Always return True but don't store anything."""
        return True
    
    def delete(self, key: str) -> bool:
        """Always return True."""
        return True
    
    def clear(self) -> bool:
        """Always return True."""
        return True
    
    def exists(self, key: str) -> bool:
        """Always return False."""
        return False
    
    def close(self) -> None:
        """No-op close."""
        pass
