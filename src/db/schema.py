# Copyright (c) 2026 Kirky.X. All rights reserved.
# Licensed under the MIT License.
# See LICENSE file in the project root for full license information.

"""LadybugDB 图数据库 Schema 定义"""

import logging

import real_ladybug as lb

logger = logging.getLogger(__name__)

# Schema 版本
SCHEMA_VERSION = "1.0.0"


def create_schema(conn: lb.Connection) -> None:
    """
    创建图数据库 Schema

    Args:
        conn: LadybugDB 连接
    """
    logger.info("开始创建图数据库 Schema...")

    # 创建节点表
    _create_node_tables(conn)

    # 创建关系表
    _create_rel_tables(conn)

    logger.info(f"图数据库 Schema 创建完成 (版本: {SCHEMA_VERSION})")


def _create_node_tables(conn: lb.Connection) -> None:
    """创建节点表"""
    node_tables = [
        # Project 节点表
        """
        CREATE NODE TABLE Project (
            uuid STRING PRIMARY KEY,
            name STRING,
            description STRING,
            status STRING DEFAULT 'CREATED',
            locked_by STRING,
            locked_at STRING,
            created_at STRING,
            updated_at STRING
        )
        """,
        # Requirement 节点表
        """
        CREATE NODE TABLE Requirement (
            uuid STRING PRIMARY KEY,
            project_uuid STRING,
            parent_uuid STRING,
            content STRING,
            decompose_reason STRING,
            status STRING DEFAULT 'DRAFT',
            level INT64 DEFAULT 0,
            order_in_parent INT64 DEFAULT 0,
            chain_order INT64,
            parallel_group INT64,
            created_at STRING,
            updated_at STRING,
            version INT64 DEFAULT 1
        )
        """,
        # ValidationNode 节点表
        """
        CREATE NODE TABLE ValidationNode (
            uuid STRING PRIMARY KEY,
            requirement_uuid STRING,
            test_cases STRING,
            acceptance_criteria STRING,
            status STRING DEFAULT 'pending',
            result STRING,
            validated_at STRING,
            created_at STRING
        )
        """,
        # ChainState 节点表
        """
        CREATE NODE TABLE ChainState (
            uuid STRING PRIMARY KEY,
            project_uuid STRING,
            status STRING DEFAULT 'IDLE',
            chain_head_uuid STRING,
            current_node_uuid STRING,
            total_nodes INT64 DEFAULT 0,
            completed_nodes INT64 DEFAULT 0,
            progress_percentage INT64 DEFAULT 0,
            last_chained_at STRING,
            chain_version INT64 DEFAULT 1,
            created_at STRING,
            updated_at STRING
        )
        """,
        # Event 节点表
        """
        CREATE NODE TABLE Event (
            uuid STRING PRIMARY KEY,
            project_uuid STRING,
            event_type STRING,
            aggregate_uuid STRING,
            payload STRING,
            event_metadata STRING,
            sequence INT64,
            created_at STRING
        )
        """,
    ]

    for i, stmt in enumerate(node_tables, 1):
        try:
            conn.execute(stmt.strip())
            logger.debug(f"节点表 {i} 创建成功")
        except Exception as e:
            # 表可能已存在，检查错误信息
            if "already exists" in str(e).lower():
                logger.debug(f"节点表 {i} 已存在，跳过")
            else:
                raise

    logger.info("节点表创建完成")


def _create_rel_tables(conn: lb.Connection) -> None:
    """创建关系表"""
    rel_tables = [
        # Project -> Requirement
        "CREATE REL TABLE HAS_REQUIREMENT (FROM Project TO Requirement)",
        # Requirement -> Requirement (父子关系)
        "CREATE REL TABLE HAS_CHILD (FROM Requirement TO Requirement)",
        # Requirement -> ValidationNode
        "CREATE REL TABLE HAS_VALIDATION (FROM Requirement TO ValidationNode)",
        # Requirement -> Requirement (依赖关系)
        "CREATE REL TABLE DEPENDS_ON (FROM Requirement TO Requirement)",
        # Requirement -> Requirement (链表指针)
        "CREATE REL TABLE NEXT_IN_CHAIN (FROM Requirement TO Requirement)",
        # Project -> ChainState
        "CREATE REL TABLE HAS_CHAIN_STATE (FROM Project TO ChainState)",
        # Project -> Event
        "CREATE REL TABLE HAS_EVENT (FROM Project TO Event)",
    ]

    for i, stmt in enumerate(rel_tables, 1):
        try:
            conn.execute(stmt.strip())
            logger.debug(f"关系表 {i} 创建成功")
        except Exception as e:
            # 表可能已存在，检查错误信息
            if "already exists" in str(e).lower():
                logger.debug(f"关系表 {i} 已存在，跳过")
            else:
                raise

    logger.info("关系表创建完成")


def get_schema_info(conn: lb.Connection) -> dict:
    """
    获取 Schema 信息

    Args:
        conn: LadybugDB 连接

    Returns:
        Schema 信息字典
    """
    info = {
        "version": SCHEMA_VERSION,
        "node_tables": [],
        "rel_tables": [],
    }

    # 查询节点表
    try:
        result = conn.execute("CALL SHOW_TABLES() WHERE type = 'NODE' RETURN name")
        info["node_tables"] = [row[0] for row in result]
    except Exception as e:
        logger.debug(f"查询节点表失败: {e}")

    # 查询关系表
    try:
        result = conn.execute("CALL SHOW_TABLES() WHERE type = 'REL' RETURN name")
        info["rel_tables"] = [row[0] for row in result]
    except Exception as e:
        logger.debug(f"查询关系表失败: {e}")

    return info
