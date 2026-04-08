# Copyright (c) 2026 Kirky.X. All rights reserved.
# Licensed under the MIT License.
# See LICENSE file in the project root for full license information.

"""LadybugDB 图数据库连接管理

注意：此模块提供向后兼容的 API，实际数据库连接由容器管理。
建议直接使用 src.core.containers 中的 get_connection() 和 init_database()。
"""

import logging
from contextlib import contextmanager
from typing import Generator

import real_ladybug as lb

logger = logging.getLogger(__name__)


def get_connection() -> lb.Connection:
    """
    获取数据库连接

    Returns:
        LadybugDB 连接实例

    Raises:
        RuntimeError: 数据库未初始化
    """
    from src.core.containers import get_connection as container_get_connection

    return container_get_connection()


def init_graph_db(
    db_path: str = "mcp_axon.lbug",
    max_retries: int = 3,
) -> None:
    """
    初始化图数据库连接

    注意：此函数提供向后兼容性，建议使用容器初始化。

    Args:
        db_path: 数据库文件路径（使用 ':memory:' 创建内存数据库）
        max_retries: 最大重试次数
    """
    from src.core.containers import init_container, get_container

    init_container(db_path=db_path, max_retries=max_retries)
    manager = get_container().db_manager()
    manager.initialize()


@contextmanager
def get_session() -> Generator[lb.Connection, None, None]:
    """
    获取数据库会话（上下文管理器）

    用法:
        with get_session() as session:
            result = session.execute("CREATE (p:Project {...})")
    """
    conn = get_connection()
    yield conn


def get_db() -> lb.Database:
    """
    获取数据库实例

    Returns:
        LadybugDB 数据库实例

    Raises:
        RuntimeError: 数据库未初始化
    """
    from src.core.containers import get_container

    manager = get_container().db_manager()
    return manager.get_db()


def get_db_path() -> str:
    """
    获取数据库文件路径

    Returns:
        数据库文件路径
    """
    from src.core.containers import get_container

    manager = get_container().db_manager()
    return manager.db_path


def close_db() -> None:
    """关闭数据库连接"""
    from src.core.containers import close_database

    close_database()
