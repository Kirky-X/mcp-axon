# Copyright (c) 2026 Kirky.X. All rights reserved.
# Licensed under the MIT License.
# See LICENSE file in the project root for full license information.

"""Pytest 配置和共享 fixture"""

import asyncio

import pytest
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from src.db.database import init_sync_db
from src.db.models import Base


@pytest.fixture(scope="session")
def event_loop():
    """创建事件循环"""

    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
async def async_engine():
    """创建异步数据库引擎（内存数据库）"""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    # 创建表
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine
    await engine.dispose()


@pytest.fixture
async def async_session(async_engine):
    """创建异步会话"""
    async_session_maker = async_sessionmaker(
        async_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    async with async_session_maker() as session:
        yield session


@pytest.fixture
def sync_engine():
    """创建同步数据库引擎（内存数据库）"""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    # 创建表
    Base.metadata.create_all(engine)

    yield engine


@pytest.fixture
def sync_session(sync_engine):
    """创建同步会话"""
    SessionMaker = sessionmaker(bind=sync_engine)
    session = SessionMaker()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


@pytest.fixture
def test_db_path():
    """创建临时测试数据库"""
    import os
    import tempfile

    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)

    # 初始化数据库
    init_sync_db(path, echo=False)

    yield path

    # 清理
    if os.path.exists(path):
        os.remove(path)
