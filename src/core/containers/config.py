# Copyright (c) 2026 Kirky.X. All rights reserved.
# Licensed under the MIT License.
# See LICENSE file in the project root for full license information.

"""容器配置 Provider"""

import os
from dataclasses import dataclass, field

from dependency_injector import containers, providers


@dataclass
class CacheConfig:
    """缓存配置"""

    project_cache_size: int = 50
    requirement_cache_size: int = 200
    chain_cache_size: int = 50
    ttl_seconds: int = 300


@dataclass
class RateLimitConfig:
    """限流配置"""

    max_requests: int = 100
    window_seconds: int = 60


@dataclass
class LockConfig:
    """锁配置"""

    timeout_minutes: int = 30


@dataclass
class DatabaseConfig:
    """数据库配置"""

    db_path: str = "axon.db"
    max_retries: int = 3


@dataclass
class AppConfig:
    """应用配置"""

    database: DatabaseConfig = field(default_factory=DatabaseConfig)
    cache: CacheConfig = field(default_factory=CacheConfig)
    rate_limit: RateLimitConfig = field(default_factory=RateLimitConfig)
    lock: LockConfig = field(default_factory=LockConfig)


def create_config_from_env() -> AppConfig:
    """从环境变量创建配置"""
    db_path = os.getenv("MCP_AXON_DB_PATH", "axon.db")

    # 尝试从性能配置中读取缓存大小
    cache_config = CacheConfig()
    try:
        from src.utils.performance_config import PerformanceConfig

        perf_config = PerformanceConfig()
        cache_settings = perf_config.get("cache", {})
        cache_config = CacheConfig(
            project_cache_size=cache_settings.get("project_size", 50),
            requirement_cache_size=cache_settings.get("requirement_size", 200),
            chain_cache_size=cache_settings.get("chain_size", 50),
            ttl_seconds=cache_settings.get("ttl_seconds", 300),
        )
    except Exception:
        pass

    return AppConfig(
        database=DatabaseConfig(db_path=db_path),
        cache=cache_config,
        rate_limit=RateLimitConfig(),
        lock=LockConfig(),
    )


class ConfigContainer(containers.DeclarativeContainer):
    """配置容器"""

    config = providers.Configuration()

    # 应用配置对象
    app_config = providers.Singleton(lambda: create_config_from_env())
