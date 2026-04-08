# Copyright (c) 2026 Kirky.X. All rights reserved.
# Licensed under the MIT License.
# See LICENSE file in the project root for full license information.

"""Pytest 配置和共享 fixture (LadybugDB 图数据库版本)"""

import os
import shutil
import tempfile
from pathlib import Path

import pytest
import real_ladybug as lb

from src.core.containers import init_container, reset_container
from src.db.schema import create_schema


def pytest_configure():
    """配置 pytest 环境"""
    # 设置环境变量，确保所有测试使用内存数据库
    os.environ["PYTEST_CURRENT_TEST"] = "1"


@pytest.fixture
def graph_connection():
    """
    创建图数据库连接（内存数据库）

    每个测试函数使用独立的内存数据库，确保测试隔离。
    """
    # 使用内存数据库
    db = lb.Database(":memory:")
    conn = lb.Connection(db)

    # 创建 Schema
    create_schema(conn)

    yield conn

    # 清理（内存数据库无需显式清理）
    conn = None
    db = None


@pytest.fixture
def graph_connection_with_temp_file():
    """
    创建图数据库连接（临时文件）

    用于需要持久化的测试场景。
    """
    # 创建临时目录
    temp_dir = Path(tempfile.mkdtemp())
    db_path = temp_dir / "test.lbug"

    db = lb.Database(str(db_path))
    conn = lb.Connection(db)

    # 创建 Schema
    create_schema(conn)

    yield conn

    # 清理
    conn = None
    db = None
    shutil.rmtree(temp_dir)


@pytest.fixture
def test_container(graph_connection):
    """
    创建测试容器 - 使用内存数据库

    Args:
        graph_connection: 内存数据库连接 fixture

    Yields:
        配置好的容器实例
    """
    # 初始化测试容器
    container = init_container(db_path=":memory:")

    # 覆盖数据库连接管理器，使用测试连接
    manager = container.db_manager()
    manager._db = (
        graph_connection._db
        if hasattr(graph_connection, "_db")
        else lb.Database(":memory:")
    )
    manager._conn = graph_connection
    manager._db_path = ":memory:"

    yield container

    # 清理容器
    reset_container()


@pytest.fixture
def project_manager(test_container):
    """获取 ProjectManager 实例"""
    return test_container.project_manager()


@pytest.fixture
def requirement_manager(test_container):
    """获取 RequirementManager 实例"""
    return test_container.requirement_manager()


@pytest.fixture
def dependency_service(test_container):
    """获取 DependencyService 实例"""
    return test_container.dependency_service()


@pytest.fixture
def validation_service(test_container):
    """获取 ValidationService 实例"""
    return test_container.validation_service()


@pytest.fixture
def chain_builder(test_container):
    """获取 ChainBuilder 实例"""
    return test_container.chain_builder()


@pytest.fixture
def chain_orchestrator(test_container):
    """获取 ChainOrchestrator 实例"""
    return test_container.chain_orchestrator()


@pytest.fixture
def lock_manager(test_container):
    """获取 ProjectLockManager 实例"""
    return test_container.lock_manager()


@pytest.fixture
def snapshot_manager(test_container):
    """获取 SnapshotManager 实例"""
    return test_container.snapshot_manager()


@pytest.fixture
def cache_manager(test_container):
    """获取 CacheManager 实例"""
    return test_container.cache_manager()


@pytest.fixture
def metrics_collector(test_container):
    """获取 MetricsCollector 实例"""
    return test_container.metrics_collector()


@pytest.fixture
def rate_limiter(test_container):
    """获取 RateLimiter 实例"""
    return test_container.rate_limiter()
