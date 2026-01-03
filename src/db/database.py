# Copyright (c) 2026 Kirky.X. All rights reserved.
# Licensed under the MIT License.
# See LICENSE file in the project root for full license information.

"""数据库会话管理和事务处理"""

import logging
import os
import stat
from contextlib import asynccontextmanager, contextmanager
from typing import AsyncGenerator, Generator

from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import Session, sessionmaker

from src.db.models import Base

logger = logging.getLogger(__name__)


# 同步数据库引擎
_engine = None
_session_factory = None

# 异步数据库引擎
_async_engine = None
_async_session_factory = None


def init_sync_db(
    db_path: str = "requirements.db",
    echo: bool = False,
    max_retries: int = 3,
    pool_size: int = 5,
):
    """初始化同步数据库连接"""

    global _engine, _session_factory

    for attempt in range(max_retries):
        try:
            # SQLite 不支持连接池，禁用连接池以避免并发问题
            _engine = create_engine(
                f"sqlite:///{db_path}",
                echo=echo,
                connect_args={"check_same_thread": False},
                poolclass=None,  # 禁用连接池
                pool_pre_ping=False,  # 禁用连接健康检查
            )
            _session_factory = sessionmaker(bind=_engine)

            # 创建所有表
            Base.metadata.create_all(_engine)

            # 设置数据库文件权限（仅所有者可读写）
            # 跳过内存数据库（:memory:）
            if not db_path.startswith(":memory:"):
                if not os.path.exists(db_path):
                    # 新创建的数据库文件，设置权限为 600
                    os.chmod(db_path, stat.S_IRUSR | stat.S_IWUSR)
                    logger.info(f"数据库文件权限已设置为 600: {db_path}")
                else:
                    # 已存在的数据库文件，检查并修复权限
                    current_mode = os.stat(db_path).st_mode
                    if current_mode & (
                        stat.S_IRGRP | stat.S_IWGRP | stat.S_IROTH | stat.S_IWOTH
                    ):
                        # 其他用户有读写权限，修复为 600
                        os.chmod(db_path, stat.S_IRUSR | stat.S_IWUSR)
                        logger.warning(
                            f"数据库文件权限已修复为 600: {db_path} (原权限: {oct(current_mode & 0o777)})"
                        )

            logger.info(f"同步数据库初始化完成: {db_path}")
            return

        except Exception as e:
            if attempt == max_retries - 1:
                logger.error(f"数据库初始化失败，已重试 {max_retries} 次: {e}")
                raise RuntimeError(f"无法初始化数据库: {e}")
            else:
                logger.warning(
                    f"数据库初始化失败，正在重试 ({attempt + 1}/{max_retries}): {e}"
                )
                import time

                time.sleep(1)


def init_async_db(
    db_path: str = "requirements.db",
    echo: bool = False,
    pool_size: int = 5,
):
    """初始化异步数据库连接"""
    global _async_engine, _async_session_factory

    _async_engine = create_async_engine(
        f"sqlite+aiosqlite:///{db_path}",
        echo=echo,
        pool_size=pool_size,  # 连接池大小
        pool_recycle=3600,  # 1小时回收连接
    )
    _async_session_factory = async_sessionmaker(
        bind=_async_engine, class_=AsyncSession, expire_on_commit=False
    )

    # 设置数据库文件权限（仅所有者可读写）
    # 跳过内存数据库（:memory:）
    if not db_path.startswith(":memory:"):
        if not os.path.exists(db_path):
            # 新创建的数据库文件，设置权限为 600
            os.chmod(db_path, stat.S_IRUSR | stat.S_IWUSR)
            logger.info(f"数据库文件权限已设置为 600: {db_path}")
        else:
            # 已存在的数据库文件，检查并修复权限
            current_mode = os.stat(db_path).st_mode
            if current_mode & (
                stat.S_IRGRP | stat.S_IWGRP | stat.S_IROTH | stat.S_IWOTH
            ):
                # 其他用户有读写权限，修复为 600
                os.chmod(db_path, stat.S_IRUSR | stat.S_IWUSR)
                logger.warning(
                    f"数据库文件权限已修复为 600: {db_path} (原权限: {oct(current_mode & 0o777)})"
                )

    logger.info(f"异步数据库初始化完成: {db_path}")


async def create_tables_async():
    """异步创建所有表"""
    async with _async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("数据库表创建完成")


@contextmanager
def get_session() -> Generator[Session, None, None]:
    """
    获取同步数据库会话（上下文管理器）

    用法:
        with get_session() as session:
            project = Project(name="test")
            session.add(project)
            session.commit()
    """
    if _session_factory is None:
        raise RuntimeError("数据库未初始化，请先调用 init_sync_db()")

    session = _session_factory()
    try:
        yield session
        session.commit()
    except Exception as e:
        try:
            session.rollback()
        except Exception as rollback_error:
            logger.error(f"数据库回滚失败: {rollback_error}")
        logger.error(f"数据库操作失败，已回滚: {e}")
        raise
    finally:
        try:
            session.close()
        except Exception as close_error:
            logger.warning(f"数据库会话关闭失败: {close_error}")


@asynccontextmanager
async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """
    获取异步数据库会话（上下文管理器）

    用法:
        async with get_async_session() as session:
            project = Project(name="test")
            session.add(project)
            await session.commit()
    """
    if _async_session_factory is None:
        raise RuntimeError("数据库未初始化，请先调用 init_async_db()")

    session = _async_session_factory()
    try:
        yield session
        await session.commit()
    except Exception as e:
        await session.rollback()
        logger.error(f"数据库操作失败，已回滚: {e}")
        raise
    finally:
        await session.close()


def get_sync_session() -> Session:
    """
    获取同步数据库会话（手动管理）

    用法:
        session = get_sync_session()
        try:
            # 操作数据库
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
    """
    if _session_factory is None:
        raise RuntimeError("数据库未初始化，请先调用 init_sync_db()")

    return _session_factory()


def get_async_session_maker() -> async_sessionmaker:
    """获取异步会话工厂"""
    if _async_session_factory is None:
        raise RuntimeError("数据库未初始化，请先调用 init_async_db()")

    return _async_session_factory


def get_engine():
    """获取同步引擎"""
    if _engine is None:
        raise RuntimeError("数据库未初始化，请先调用 init_sync_db()")
    return _engine


def get_async_engine():
    """获取异步引擎"""
    if _async_engine is None:
        raise RuntimeError("数据库未初始化，请先调用 init_async_db()")
    return _async_engine


async def close_db():
    """关闭数据库连接"""
    global _async_engine

    if _async_engine:
        await _async_engine.dispose()
        logger.info("异步数据库连接已关闭")


def close_sync_db():
    """关闭同步数据库连接"""
    global _engine

    if _engine:
        _engine.dispose()
        logger.info("同步数据库连接已关闭")
