# Copyright (c) 2026 Kirky.X. All rights reserved.
# Licensed under the MIT License.
# See LICENSE file in the project root for full license information.

"""依赖注入容器 - 主入口"""

import logging
import os
from typing import Optional

import real_ladybug as lb
from dependency_injector import containers, providers

from src.core.containers.config import AppConfig, CacheConfig, create_config_from_env
from src.core.containers.database import DatabaseConnectionManager
from src.core.containers.services import ServicesContainer
from src.core.containers.utils import UtilsContainer

logger = logging.getLogger(__name__)

# 全局容器实例
_container: Optional["Container"] = None


class Container(containers.DeclarativeContainer):
    """主容器 - 组装所有子容器"""

    # 配置
    config = providers.Configuration()

    # 应用配置对象
    app_config = providers.Singleton(lambda: create_config_from_env())

    # 数据库连接管理器
    db_manager = providers.Singleton(
        DatabaseConnectionManager,
        db_path=config.db_path,
        max_retries=config.max_retries,
    )

    # 数据库连接 (需要初始化后才能使用)
    connection = providers.Singleton(
        lambda manager: manager.get_connection(),
        manager=db_manager,
    )

    # 工具类实例
    cache_manager = providers.Singleton(
        lambda app_cfg: _create_cache_manager(app_cfg),
        app_cfg=app_config,
    )

    metrics_collector = providers.Singleton(
        lambda: _create_metrics_collector(),
    )

    rate_limiter = providers.Singleton(
        lambda app_cfg: _create_rate_limiter(app_cfg),
        app_cfg=app_config,
    )

    snapshot_manager = providers.Singleton(
        lambda: _create_snapshot_manager(),
    )

    lock_manager = providers.Singleton(
        lambda app_cfg: _create_lock_manager(app_cfg),
        app_cfg=app_config,
    )

    graph_algorithms = providers.Singleton(
        lambda: _create_graph_algorithms(),
    )

    # 辅助服务
    complexity_evaluator = providers.Singleton(
        lambda: _create_complexity_evaluator(),
    )

    decomposition_advisor = providers.Singleton(
        lambda: _create_decomposition_advisor(),
    )

    # 核心服务
    dependency_service = providers.Singleton(
        lambda cache: _create_dependency_service(cache),
        cache=cache_manager,
    )

    validation_service = providers.Singleton(
        lambda cache: _create_validation_service(cache),
        cache=cache_manager,
    )

    project_manager = providers.Singleton(
        lambda cache: _create_project_manager(cache),
        cache=cache_manager,
    )

    requirement_manager = providers.Singleton(
        lambda cache, comp_eval, decomp_adv: _create_requirement_manager(
            cache, comp_eval, decomp_adv
        ),
        cache=cache_manager,
        comp_eval=complexity_evaluator,
        decomp_adv=decomposition_advisor,
    )

    chain_builder = providers.Singleton(
        lambda cache, graph_alg: _create_chain_builder(cache, graph_alg),
        cache=cache_manager,
        graph_alg=graph_algorithms,
    )

    chain_orchestrator = providers.Singleton(
        lambda chain_bldr, snap_mgr: _create_chain_orchestrator(chain_bldr, snap_mgr),
        chain_bldr=chain_builder,
        snap_mgr=snapshot_manager,
    )


# ============ 工厂函数（模块级私有函数） ============


def _create_cache_manager(app_config: AppConfig) -> "CacheManager":
    """创建缓存管理器"""
    from src.utils.cache import CacheManager

    cache_cfg = app_config.cache
    return CacheManager(
        project_cache_size=cache_cfg.project_cache_size,
        requirement_cache_size=cache_cfg.requirement_cache_size,
        chain_cache_size=cache_cfg.chain_cache_size,
        ttl_seconds=cache_cfg.ttl_seconds,
    )


def _create_metrics_collector() -> "MetricsCollector":
    """创建指标收集器"""
    from src.utils.metrics import MetricsCollector

    return MetricsCollector()


def _create_rate_limiter(app_config: AppConfig) -> "RateLimiter":
    """创建限流器"""
    from src.utils.rate_limiter import RateLimiter

    rate_cfg = app_config.rate_limit
    return RateLimiter(
        max_requests=rate_cfg.max_requests,
        window_seconds=rate_cfg.window_seconds,
    )


def _create_snapshot_manager() -> "SnapshotManager":
    """创建快照管理器"""
    from src.utils.snapshot_manager import SnapshotManager

    return SnapshotManager()


def _create_lock_manager(app_config: AppConfig) -> "ProjectLockManager":
    """创建锁管理器"""
    from src.utils.lock_manager import ProjectLockManager

    return ProjectLockManager(timeout_minutes=app_config.lock.timeout_minutes)


def _create_graph_algorithms() -> "GraphAlgorithms":
    """创建图算法工具"""
    from src.utils.graph import GraphAlgorithms

    return GraphAlgorithms()


def _create_complexity_evaluator() -> "ComplexityEvaluator":
    """创建复杂度评估器"""
    from src.services.complexity_evaluator import ComplexityEvaluator

    return ComplexityEvaluator()


def _create_decomposition_advisor() -> "DecompositionAdvisor":
    """创建分解建议器"""
    from src.services.decomposition_advisor import DecompositionAdvisor

    return DecompositionAdvisor()


def _create_dependency_service(cache) -> "DependencyService":
    """创建依赖服务"""
    from src.services.dependency_service import DependencyService

    return DependencyService(cache=cache)


def _create_validation_service(cache) -> "ValidationService":
    """创建验证服务"""
    from src.services.validation_service import ValidationService

    return ValidationService(cache=cache)


def _create_project_manager(cache) -> "ProjectManager":
    """创建项目管理器"""
    from src.services.project_manager import ProjectManager

    return ProjectManager(cache=cache)


def _create_requirement_manager(
    cache, complexity_evaluator, decomposition_advisor
) -> "RequirementManager":
    """创建需求管理器"""
    from src.services.requirement_manager import RequirementManager

    return RequirementManager(
        cache=cache,
        complexity_evaluator=complexity_evaluator,
        decomposition_advisor=decomposition_advisor,
    )


def _create_chain_builder(cache, graph_algorithms) -> "ChainBuilder":
    """创建链化构建器"""
    from src.services.chain_builder import ChainBuilder

    return ChainBuilder(
        cache=cache,
        graph_algorithms=graph_algorithms,
    )


def _create_chain_orchestrator(chain_builder, snapshot_manager) -> "ChainOrchestrator":
    """创建链化编排器"""
    from src.services.chain_orchestrator import ChainOrchestrator

    return ChainOrchestrator(
        chain_builder=chain_builder,
        snapshot_manager=snapshot_manager,
    )


# ============ 全局访问函数 ============


def init_container(db_path: Optional[str] = None, max_retries: int = 3) -> Container:
    """
    初始化容器

    Args:
        db_path: 数据库路径（可选，默认从环境变量获取）
        max_retries: 最大重试次数

    Returns:
        容器实例
    """
    global _container

    # 获取配置
    if db_path is None:
        db_path = os.getenv("MCP_AXON_DB_PATH", "mcp_axon.lbug")

    # 创建容器
    _container = Container()

    # 设置配置
    _container.config.from_dict(
        {
            "db_path": db_path,
            "max_retries": max_retries,
        }
    )

    logger.info(f"容器初始化完成: db_path={db_path}")

    return _container


def get_container() -> Container:
    """
    获取容器实例

    Returns:
        容器实例

    Raises:
        RuntimeError: 容器未初始化
    """
    if _container is None:
        raise RuntimeError("容器未初始化，请先调用 init_container()")
    return _container


def get_connection() -> lb.Connection:
    """
    获取数据库连接

    Returns:
        数据库连接实例
    """
    container = get_container()
    manager: DatabaseConnectionManager = container.db_manager()
    return manager.get_connection()


def init_database() -> lb.Connection:
    """
    初始化数据库连接

    Returns:
        数据库连接实例
    """
    container = get_container()
    manager: DatabaseConnectionManager = container.db_manager()
    return manager.initialize()


def close_database() -> None:
    """关闭数据库连接"""
    global _container
    if _container is not None:
        manager: DatabaseConnectionManager = _container.db_manager()
        manager.close()


def reset_container() -> None:
    """重置容器（主要用于测试）"""
    global _container
    if _container is not None:
        close_database()
        _container = None
