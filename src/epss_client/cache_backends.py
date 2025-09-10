from __future__ import annotations

import json
import pickle
import time
from pathlib import Path
from typing import Any

from .cache_config import DatabaseConfig
from .cache_config import FileConfig
from .cache_config import RedisConfig
from .cache_interface import CacheInterface
from .types import EpssResponse

try:
    import redis

    HAS_REDIS = True
except ImportError:
    HAS_REDIS = False

try:
    from sqlalchemy import Column
    from sqlalchemy import DateTime
    from sqlalchemy import MetaData
    from sqlalchemy import String
    from sqlalchemy import Table
    from sqlalchemy import Text
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    HAS_SQLALCHEMY = True
except ImportError:
    HAS_SQLALCHEMY = False


class FileCache(CacheInterface):
    """File-based cache backend using JSON or pickle format."""

    def __init__(self, config: FileConfig):
        self.config = config
        self.cache_dir = Path(config.directory).expanduser()
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._ensure_directory_size()

    def _get_file_path(self, key: str) -> Path:
        """Get file path for cache key."""
        # Replace invalid filename characters
        safe_key = key.replace("/", "_").replace(":", "_")
        extension = ".json" if self.config.format == "json" else ".pkl"
        return self.cache_dir / f"{safe_key}{extension}"

    def _serialize(self, value: EpssResponse) -> bytes:
        """Serialize value for storage."""
        if self.config.format == "json":
            data = json.dumps(value).encode()
        else:
            data = pickle.dumps(value)

        if self.config.compression:
            try:
                import gzip

                return gzip.compress(data)
            except ImportError:
                pass

        return data

    def _deserialize(self, data: bytes) -> EpssResponse:
        """Deserialize value from storage."""
        if self.config.compression:
            try:
                import gzip

                data = gzip.decompress(data)
            except (ImportError, OSError):
                pass

        if self.config.format == "json":
            return json.loads(data.decode())
        else:
            return pickle.loads(data)

    def _is_expired(self, file_path: Path, ttl: int | None) -> bool:
        """Check if cached file is expired."""
        if ttl is None:
            return False

        try:
            mtime = file_path.stat().st_mtime
            return time.time() - mtime > ttl
        except OSError:
            return True

    def _ensure_directory_size(self) -> None:
        """Ensure cache directory doesn't exceed size limit."""
        if self.config.max_size_mb <= 0:
            return

        max_size_bytes = self.config.max_size_mb * 1024 * 1024
        total_size = 0
        files = []

        for file_path in self.cache_dir.iterdir():
            if file_path.is_file():
                try:
                    size = file_path.stat().st_size
                    mtime = file_path.stat().st_mtime
                    total_size += size
                    files.append((file_path, mtime, size))
                except OSError:
                    continue

        if total_size <= max_size_bytes:
            return

        # Remove oldest files until we're under the limit
        files.sort(key=lambda x: x[1])  # Sort by modification time

        for file_path, _, size in files:
            try:
                file_path.unlink()
                total_size -= size
                if total_size <= max_size_bytes:
                    break
            except OSError:
                continue

    def get(self, key: str) -> EpssResponse | None:
        """Get cached value by key."""
        file_path = self._get_file_path(key)

        if not file_path.exists():
            return None

        # Note: TTL checking would require storing TTL with data or using file mtime
        # For simplicity, we'll use file modification time

        try:
            with open(file_path, "rb") as f:
                data = f.read()
            return self._deserialize(data)
        except (OSError, json.JSONDecodeError, pickle.UnpicklingError):
            # Remove corrupted file
            try:
                file_path.unlink()
            except OSError:
                pass
            return None

    def set(self, key: str, value: EpssResponse, ttl: int | None = None) -> bool:
        """Set cached value with optional TTL."""
        try:
            file_path = self._get_file_path(key)
            data = self._serialize(value)

            with open(file_path, "wb") as f:
                f.write(data)

            # Store TTL as extended attribute or in filename if needed
            # For now, we'll rely on periodic cleanup

            self._ensure_directory_size()
            return True
        except (OSError, TypeError):
            return False

    def delete(self, key: str) -> bool:
        """Delete cached value by key."""
        file_path = self._get_file_path(key)
        try:
            file_path.unlink()
            return True
        except OSError:
            return False

    def clear(self) -> bool:
        """Clear all cached values."""
        try:
            for file_path in self.cache_dir.iterdir():
                if file_path.is_file():
                    file_path.unlink()
            return True
        except OSError:
            return False

    def exists(self, key: str) -> bool:
        """Check if key exists in cache."""
        file_path = self._get_file_path(key)
        return file_path.exists()

    def close(self) -> None:
        """Close cache (no-op for file cache)."""
        pass


class RedisCache(CacheInterface):
    """Redis-based cache backend."""

    def __init__(self, config: RedisConfig):
        if not HAS_REDIS:
            raise ImportError("redis package required for Redis cache backend")

        self.config = config
        self.client = redis.Redis(
            host=config.host,
            port=config.port,
            db=config.db,
            password=config.password,
            socket_timeout=config.socket_timeout,
            socket_connect_timeout=config.socket_connect_timeout,
            max_connections=config.max_connections,
            decode_responses=False,  # We handle serialization ourselves
        )

        # Test connection
        try:
            self.client.ping()
        except redis.ConnectionError as e:
            raise ConnectionError(f"Cannot connect to Redis: {e}") from e

    def _serialize(self, value: EpssResponse) -> bytes:
        """Serialize value for Redis storage."""
        return json.dumps(value).encode()

    def _deserialize(self, data: bytes) -> EpssResponse:
        """Deserialize value from Redis storage."""
        return json.loads(data.decode())

    def get(self, key: str) -> EpssResponse | None:
        """Get cached value by key."""
        try:
            data = self.client.get(key)
            if data is None:
                return None
            return self._deserialize(data)
        except (redis.RedisError, json.JSONDecodeError):
            return None

    def set(self, key: str, value: EpssResponse, ttl: int | None = None) -> bool:
        """Set cached value with optional TTL."""
        try:
            data = self._serialize(value)
            return self.client.set(key, data, ex=ttl)
        except (redis.RedisError, TypeError):
            return False

    def delete(self, key: str) -> bool:
        """Delete cached value by key."""
        try:
            return bool(self.client.delete(key))
        except redis.RedisError:
            return False

    def clear(self) -> bool:
        """Clear all cached values."""
        try:
            # This clears the entire database - be careful!
            return self.client.flushdb()
        except redis.RedisError:
            return False

    def exists(self, key: str) -> bool:
        """Check if key exists in cache."""
        try:
            return bool(self.client.exists(key))
        except redis.RedisError:
            return False

    def close(self) -> None:
        """Close Redis connection."""
        try:
            self.client.close()
        except redis.RedisError:
            pass


class DatabaseCache(CacheInterface):
    """SQL database cache backend using SQLAlchemy."""

    def __init__(self, config: DatabaseConfig):
        if not HAS_SQLALCHEMY:
            raise ImportError("sqlalchemy package required for database cache backend")

        self.config = config

        # Expand user path for SQLite URLs
        db_url = config.url
        if db_url.startswith("sqlite:///~"):
            db_url = db_url.replace("sqlite:///~", f"sqlite:///{Path.home()}")
            # Ensure directory exists for SQLite
            db_path = Path(db_url.replace("sqlite:///", ""))
            db_path.parent.mkdir(parents=True, exist_ok=True)

        self.engine = create_engine(
            db_url,
            pool_size=config.pool_size,
            max_overflow=config.max_overflow,
            pool_timeout=config.pool_timeout,
        )

        # Create table schema
        self.metadata = MetaData()
        self.cache_table = Table(
            config.table_name,
            self.metadata,
            Column("cache_key", String(255), primary_key=True),
            Column("data", Text, nullable=False),
            Column("created_at", DateTime, nullable=False),
            Column("expires_at", DateTime, nullable=True),
        )

        # Create table if it doesn't exist
        self.metadata.create_all(self.engine)

        self.Session = sessionmaker(bind=self.engine)

    def _is_expired(self, expires_at: Any | None) -> bool:
        """Check if cache entry is expired."""
        if expires_at is None:
            return False

        from datetime import datetime

        return datetime.utcnow() > expires_at

    def get(self, key: str) -> EpssResponse | None:
        """Get cached value by key."""
        try:
            with self.Session() as session:
                from sqlalchemy import select

                stmt = select(self.cache_table).where(
                    self.cache_table.c.cache_key == key
                )
                result = session.execute(stmt).fetchone()

                if result is None:
                    return None

                # Check if expired
                if self._is_expired(result.expires_at):
                    # Delete expired entry
                    session.execute(
                        self.cache_table.delete().where(
                            self.cache_table.c.cache_key == key
                        )
                    )
                    session.commit()
                    return None

                return json.loads(result.data)
        except Exception:
            return None

    def set(self, key: str, value: EpssResponse, ttl: int | None = None) -> bool:
        """Set cached value with optional TTL."""
        try:
            from datetime import datetime
            from datetime import timedelta

            expires_at = None
            if ttl is not None:
                expires_at = datetime.utcnow() + timedelta(seconds=ttl)

            data = json.dumps(value)

            with self.Session() as session:
                # Use upsert logic (insert or update)
                from sqlalchemy import text
                from sqlalchemy.dialects.sqlite import insert as sqlite_insert

                if "sqlite" in self.config.url:
                    stmt = sqlite_insert(self.cache_table).values(
                        cache_key=key,
                        data=data,
                        created_at=datetime.utcnow(),
                        expires_at=expires_at,
                    )
                    stmt = stmt.on_conflict_do_update(
                        index_elements=["cache_key"],
                        set_={
                            "data": stmt.excluded.data,
                            "created_at": stmt.excluded.created_at,
                            "expires_at": stmt.excluded.expires_at,
                        },
                    )
                    session.execute(stmt)
                else:
                    # For other databases, use merge/upsert pattern
                    session.execute(
                        text(
                            f"""
                        INSERT INTO {self.config.table_name}
                        (cache_key, data, created_at, expires_at)
                        VALUES (:key, :data, :created_at, :expires_at)
                        ON CONFLICT (cache_key)
                        DO UPDATE SET
                            data = EXCLUDED.data,
                            created_at = EXCLUDED.created_at,
                            expires_at = EXCLUDED.expires_at
                        """
                        ),
                        {
                            "key": key,
                            "data": data,
                            "created_at": datetime.utcnow(),
                            "expires_at": expires_at,
                        },
                    )

                session.commit()
                return True
        except Exception:
            return False

    def delete(self, key: str) -> bool:
        """Delete cached value by key."""
        try:
            with self.Session() as session:
                result = session.execute(
                    self.cache_table.delete().where(self.cache_table.c.cache_key == key)
                )
                session.commit()
                return result.rowcount > 0
        except Exception:
            return False

    def clear(self) -> bool:
        """Clear all cached values."""
        try:
            with self.Session() as session:
                session.execute(self.cache_table.delete())
                session.commit()
                return True
        except Exception:
            return False

    def exists(self, key: str) -> bool:
        """Check if key exists in cache."""
        try:
            with self.Session() as session:
                from sqlalchemy import func
                from sqlalchemy import select

                stmt = select(func.count()).select_from(
                    select(self.cache_table.c.cache_key)
                    .where(self.cache_table.c.cache_key == key)
                    .subquery()
                )
                result = session.execute(stmt).scalar()
                return result > 0
        except Exception:
            return False

    def close(self) -> None:
        """Close database connection."""
        try:
            self.engine.dispose()
        except Exception:
            pass
