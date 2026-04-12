# Copyright (c) 2026 Kirky.X. All rights reserved.
# Licensed under the MIT License.
# See LICENSE file in the project root for full license information.

"""数据库 Provider"""

import logging
import stat
from pathlib import Path

import real_ladybug as lb
from dependency_injector import containers, providers

from src.db.schema import create_schema, get_schema_info

logger = logging.getLogger(__name__)


class DatabaseConnectionManager:
    """数据库连接管理器"""

    def __init__(self, db_path: str = "mcp_axon.lbug", max_retries: int = 3):
        """
        初始化数据库连接管理器

        Args:
            db_path: 数据库文件路径
            max_retries: 最大重试次数
        """
        self._db_path = db_path
        self._max_retries = max_retries
        self._db: lb.Database | None = None
        self._conn: lb.Connection | None = None

    @property
    def db_path(self) -> str:
        """获取数据库路径"""
        return self._db_path

    def initialize(self) -> lb.Connection:
        """
        初始化数据库连接

        Returns:
            数据库连接实例

        Raises:
            RuntimeError: 初始化失败
        """
        for attempt in range(self._max_retries):
            try:
                # 创建数据库
                self._db = lb.Database(self._db_path)
                self._conn = lb.Connection(self._db)

                # 创建 Schema
                create_schema(self._conn)

                # 设置数据库文件权限
                db_path_obj = Path(self._db_path)
                if not self._db_path.startswith(":memory:") and db_path_obj.exists():
                    current_mode = db_path_obj.stat().st_mode
                    if current_mode & (
                        stat.S_IRGRP | stat.S_IWGRP | stat.S_IROTH | stat.S_IWOTH
                    ):
                        db_path_obj.chmod(stat.S_IRUSR | stat.S_IWUSR)
                        logger.info(f"数据库文件权限已设置为 600: {self._db_path}")

                # 输出 Schema 信息
                schema_info = get_schema_info(self._conn)
                logger.info(
                    f"图数据库初始化完成: {self._db_path} "
                    f"(节点表: {len(schema_info['node_tables'])}, "
                    f"关系表: {len(schema_info['rel_tables'])})"
                )
                return self._conn

            except Exception as e:
                if attempt == self._max_retries - 1:
                    logger.error(
                        f"数据库初始化失败，已重试 {self._max_retries} 次: {e}"
                    )
                    raise RuntimeError(f"无法初始化图数据库: {e}")
                else:
                    logger.warning(
                        f"数据库初始化失败，正在重试 ({attempt + 1}/{self._max_retries}): {e}"
                    )
                    import time

                    time.sleep(1)

        raise RuntimeError("数据库初始化失败")

    def get_connection(self) -> lb.Connection:
        """
        获取数据库连接

        Returns:
            数据库连接实例

        Raises:
            RuntimeError: 数据库未初始化
        """
        if self._conn is None:
            raise RuntimeError("图数据库未初始化，请先调用 initialize()")
        return self._conn

    def get_db(self) -> lb.Database:
        """
        获取数据库实例

        Returns:
            数据库实例

        Raises:
            RuntimeError: 数据库未初始化
        """
        if self._db is None:
            raise RuntimeError("图数据库未初始化，请先调用 initialize()")
        return self._db

    def close(self) -> None:
        """关闭数据库连接"""
        if self._conn is not None:
            self._conn = None
            logger.info("图数据库连接已关闭")

        if self._db is not None:
            self._db = None
            logger.info("图数据库已关闭")


class DatabaseContainer(containers.DeclarativeContainer):
    """数据库容器"""

    # 配置
    config = providers.Configuration()

    # 连接管理器 (Singleton)
    connection_manager = providers.Singleton(
        DatabaseConnectionManager,
        db_path=config.db_path,
        max_retries=config.max_retries,
    )

    # 获取连接的方法
    @staticmethod
    def get_connection(manager: DatabaseConnectionManager) -> lb.Connection:
        """获取数据库连接"""
        return manager.get_connection()
