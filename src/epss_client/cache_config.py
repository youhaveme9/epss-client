from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Literal, Optional, Union

try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False

try:
    import tomllib
    HAS_TOML = True
except ImportError:
    try:
        import toml as tomllib  # fallback for older Python versions
        HAS_TOML = True
    except ImportError:
        HAS_TOML = False


@dataclass
class RedisConfig:
    """Redis cache backend configuration."""
    host: str = "localhost"
    port: int = 6379
    db: int = 0
    password: Optional[str] = None
    socket_timeout: float = 5.0
    socket_connect_timeout: float = 5.0
    max_connections: int = 10
    decode_responses: bool = True


@dataclass 
class DatabaseConfig:
    """Database cache backend configuration."""
    url: str = "sqlite:///~/.cache/epss/cache.db"
    table_name: str = "epss_cache"
    pool_size: int = 5
    max_overflow: int = 10
    pool_timeout: int = 30


@dataclass
class FileConfig:
    """File-based cache backend configuration."""
    directory: str = "~/.cache/epss"
    max_size_mb: int = 100
    compression: bool = True
    format: Literal["json", "pickle"] = "json"


@dataclass
class CacheConfig:
    """Main cache configuration."""
    enabled: bool = False
    backend: Literal["redis", "database", "file"] = "file"
    ttl: int = 3600  # 1 hour default
    key_prefix: str = "epss"
    
    redis: RedisConfig = field(default_factory=RedisConfig)
    database: DatabaseConfig = field(default_factory=DatabaseConfig)
    file: FileConfig = field(default_factory=FileConfig)
    
    # Performance tuning
    compression: bool = True
    serialize_format: Literal["json", "pickle"] = "json"
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> CacheConfig:
        """Create CacheConfig from dictionary."""
        cache_data = data.get("cache", {})
        
        return cls(
            enabled=cache_data.get("enabled", False),
            backend=cache_data.get("backend", "file"),
            ttl=cache_data.get("ttl", 3600),
            key_prefix=cache_data.get("key_prefix", "epss"),
            redis=RedisConfig(**cache_data.get("redis", {})),
            database=DatabaseConfig(**cache_data.get("database", {})),
            file=FileConfig(**cache_data.get("file", {})),
            compression=cache_data.get("compression", True),
            serialize_format=cache_data.get("serialize_format", "json"),
        )
    
    @classmethod
    def from_file(cls, file_path: Union[str, Path]) -> CacheConfig:
        """Load configuration from file."""
        file_path = Path(file_path).expanduser()
        
        if not file_path.exists():
            raise FileNotFoundError(f"Config file not found: {file_path}")
        
        suffix = file_path.suffix.lower()
        
        with open(file_path, 'r') as f:
            if suffix in ['.yaml', '.yml']:
                if not HAS_YAML:
                    raise ImportError("PyYAML required for YAML config files")
                data = yaml.safe_load(f)
            elif suffix == '.toml':
                if not HAS_TOML:
                    raise ImportError("toml/tomllib required for TOML config files")
                data = tomllib.load(f) if hasattr(tomllib, 'load') else tomllib.loads(f.read())
            else:
                raise ValueError(f"Unsupported config file format: {suffix}")
        
        return cls.from_dict(data)
    
    @classmethod
    def from_env(cls) -> CacheConfig:
        """Load configuration from environment variables."""
        return cls(
            enabled=os.getenv("EPSS_CACHE_ENABLED", "false").lower() == "true",
            backend=os.getenv("EPSS_CACHE_BACKEND", "file"),
            ttl=int(os.getenv("EPSS_CACHE_TTL", "3600")),
            key_prefix=os.getenv("EPSS_CACHE_KEY_PREFIX", "epss"),
            redis=RedisConfig(
                host=os.getenv("EPSS_CACHE_REDIS_HOST", "localhost"),
                port=int(os.getenv("EPSS_CACHE_REDIS_PORT", "6379")),
                db=int(os.getenv("EPSS_CACHE_REDIS_DB", "0")),
                password=os.getenv("EPSS_CACHE_REDIS_PASSWORD"),
            ),
            database=DatabaseConfig(
                url=os.getenv("EPSS_CACHE_DATABASE_URL", "sqlite:///~/.cache/epss/cache.db"),
                table_name=os.getenv("EPSS_CACHE_DATABASE_TABLE", "epss_cache"),
            ),
            file=FileConfig(
                directory=os.getenv("EPSS_CACHE_FILE_DIRECTORY", "~/.cache/epss"),
                max_size_mb=int(os.getenv("EPSS_CACHE_FILE_MAX_SIZE_MB", "100")),
            ),
        )
    
    @classmethod
    def load(cls, config_file: Optional[Union[str, Path]] = None) -> CacheConfig:
        """
        Load configuration with precedence: config_file > env vars > defaults.
        
        If no config_file is provided, tries these locations:
        - ~/.epss/config.yaml
        - ~/.epss/config.yml  
        - ./epss.yaml
        - ./epss.yml
        - ./pyproject.toml
        """
        # Try loading from file
        if config_file:
            try:
                return cls.from_file(config_file)
            except (FileNotFoundError, ValueError, ImportError):
                pass
        else:
            # Try default locations
            default_locations = [
                Path.home() / ".epss" / "config.yaml",
                Path.home() / ".epss" / "config.yml",
                Path.cwd() / "epss.yaml", 
                Path.cwd() / "epss.yml",
                Path.cwd() / "pyproject.toml",
            ]
            
            for location in default_locations:
                if location.exists():
                    try:
                        return cls.from_file(location)
                    except (ValueError, ImportError):
                        continue
        
        # Fallback to environment variables
        return cls.from_env()
