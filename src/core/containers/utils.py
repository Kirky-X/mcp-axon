# Copyright (c) 2026 Kirky.X. All rights reserved.
# Licensed under the MIT License.
# See LICENSE file in the project root for full license information.

"""工具类 Provider"""

from dependency_injector import containers, providers

from src.utils.cache import CacheManager
from src.utils.graph import GraphAlgorithms
from src.utils.lock_manager import ProjectLockManager
from src.utils.metrics import MetricsCollector
from src.utils.rate_limiter import RateLimiter
from src.utils.snapshot_manager import SnapshotManager


class UtilsContainer(containers.DeclarativeContainer):
    """工具类容器"""

    # 配置
    config = providers.Configuration()

    # 缓存管理器 (Singleton)
    cache_manager = providers.Singleton(
        CacheManager,
        project_cache_size=config.cache.project_cache_size,
        requirement_cache_size=config.cache.requirement_cache_size,
        chain_cache_size=config.cache.chain_cache_size,
        ttl_seconds=config.cache.ttl_seconds,
    )

    # 指标收集器 (Singleton)
    metrics_collector = providers.Singleton(MetricsCollector)

    # 限流器 (Singleton)
    rate_limiter = providers.Singleton(
        RateLimiter,
        max_requests=config.rate_limit.max_requests,
        window_seconds=config.rate_limit.window_seconds,
    )

    # 快照管理器 (Singleton)
    snapshot_manager = providers.Singleton(SnapshotManager)

    # 项目锁管理器 (Singleton)
    lock_manager = providers.Singleton(
        ProjectLockManager,
        timeout_minutes=config.lock.timeout_minutes,
    )

    # 图算法工具 (Singleton)
    graph_algorithms = providers.Singleton(GraphAlgorithms)
