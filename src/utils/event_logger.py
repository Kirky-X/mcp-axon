# Copyright (c) 2026 Kirky.X. All rights reserved.
# Licensed under the MIT License.
# See LICENSE file in the project root for full license information.

"""通用事件记录服务（增强审计日志）"""

import json
import logging
import uuid
from typing import Any, Dict, Optional

import real_ladybug as lb

from src.db.graph_models import now_utc, serialize_json
from src.db.graph_queries import (
    CREATE_EVENT,
    CREATE_HAS_EVENT,
    GET_EVENTS_BY_PROJECT,
    GET_LATEST_EVENT_SEQUENCE,
)

logger = logging.getLogger(__name__)


def log_event(
    conn: lb.Connection,
    project_uuid: str,
    event_type: str,
    aggregate_uuid: Optional[str],
    payload: Dict[str, Any],
    metadata: Optional[Dict[str, Any]] = None,
    session_id: Optional[str] = None,
) -> str:
    """
    记录事件（增强审计版本）

    Args:
        conn: 数据库连接
        project_uuid: 项目 ID
        event_type: 事件类型
        aggregate_uuid: 聚合根 ID
        payload: 事件负载
        metadata: 元数据
        session_id: 会话 ID（用于审计追踪）

    Returns:
        创建的事件 UUID
    """
    # 获取当前序列号
    result = conn.execute(GET_LATEST_EVENT_SEQUENCE, {"project_uuid": project_uuid})
    rows = list(result)
    max_sequence = rows[0][0] if rows and rows[0][0] else 0
    sequence = max_sequence + 1

    # 增强元数据
    enhanced_metadata = metadata or {}
    if session_id:
        enhanced_metadata["session_id"] = session_id

    # 创建事件 UUID
    event_uuid = str(uuid.uuid4())
    created_at = now_utc()

    # 创建事件节点
    conn.execute(
        CREATE_EVENT,
        {
            "uuid": event_uuid,
            "project_uuid": project_uuid,
            "event_type": event_type,
            "aggregate_uuid": aggregate_uuid or "",
            "payload": serialize_json(payload),
            "event_metadata": serialize_json(enhanced_metadata),
            "sequence": sequence,
            "created_at": created_at,
        },
    )

    # 创建 HAS_EVENT 边
    conn.execute(
        CREATE_HAS_EVENT, {"project_uuid": project_uuid, "event_uuid": event_uuid}
    )

    # 记录日志
    logger.info(
        f"事件记录: {event_type} | 项目: {project_uuid} | 聚合: {aggregate_uuid} | "
        f"序列: {sequence} | 会话: {session_id or 'N/A'}"
    )

    return event_uuid


def log_sensitive_event(
    conn: lb.Connection,
    project_uuid: str,
    event_type: str,
    aggregate_uuid: str,
    payload: Dict[str, Any],
    metadata: Optional[Dict[str, Any]] = None,
    session_id: Optional[str] = None,
    sensitive_fields: Optional[list] = None,
) -> str:
    """
    记录敏感事件（自动过滤敏感字段）

    Args:
        conn: 数据库连接
        project_uuid: 项目 ID
        event_type: 事件类型
        aggregate_uuid: 聚合根 ID
        payload: 事件负载
        metadata: 元数据
        session_id: 会话 ID
        sensitive_fields: 敏感字段列表（将被过滤）

    Returns:
        创建的事件 UUID
    """
    # 过滤敏感字段
    safe_payload = {}
    sensitive_fields = sensitive_fields or []

    for key, value in payload.items():
        if key in sensitive_fields:
            safe_payload[key] = "[FILTERED]"
        else:
            safe_payload[key] = value

    # 记录日志警告
    if sensitive_fields:
        logger.warning(
            f"敏感事件记录: {event_type} | 已过滤字段: {sensitive_fields} | "
            f"项目: {project_uuid}"
        )

    return log_event(
        conn=conn,
        project_uuid=project_uuid,
        event_type=event_type,
        aggregate_uuid=aggregate_uuid,
        payload=safe_payload,
        metadata=metadata,
        session_id=session_id,
    )


def get_event_history(
    conn: lb.Connection,
    project_uuid: str,
    event_type: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
) -> list:
    """
    获取事件历史

    Args:
        conn: 数据库连接
        project_uuid: 项目 ID
        event_type: 事件类型（可选）
        limit: 返回数量限制
        offset: 偏移量

    Returns:
        事件列表
    """
    result = conn.execute(
        GET_EVENTS_BY_PROJECT, {"project_uuid": project_uuid, "limit": limit}
    )
    rows = list(result)

    events = []
    for row in rows:
        # 安全解析 JSON payload
        payload = {}
        if row[4]:
            try:
                payload = json.loads(row[4])
            except json.JSONDecodeError:
                payload = {}

        # 安全解析 JSON metadata
        event_metadata = None
        if row[5]:
            try:
                event_metadata = json.loads(row[5])
            except json.JSONDecodeError:
                event_metadata = None

        event = {
            "uuid": row[0],
            "project_uuid": row[1],
            "event_type": row[2],
            "aggregate_uuid": row[3],
            "payload": payload,
            "event_metadata": event_metadata,
            "sequence": row[6],
            "created_at": row[7],
        }

        # 按事件类型过滤
        if event_type and event["event_type"] != event_type:
            continue

        events.append(event)

    return events


def get_events_by_session(
    conn: lb.Connection,
    project_uuid: str,
    session_id: str,
    limit: int = 100,
) -> list:
    """
    获取特定会话的事件

    Args:
        conn: 数据库连接
        project_uuid: 项目 ID
        session_id: 会话 ID
        limit: 返回数量限制

    Returns:
        事件列表
    """
    # 获取所有事件，然后在 Python 中过滤
    result = conn.execute(
        GET_EVENTS_BY_PROJECT, {"project_uuid": project_uuid, "limit": limit}
    )
    rows = list(result)

    events = []
    for row in rows:
        metadata_str = row[5]  # event_metadata
        if metadata_str:
            metadata = json.loads(metadata_str)
            if metadata.get("session_id") == session_id:
                events.append(
                    {
                        "uuid": row[0],
                        "project_uuid": row[1],
                        "event_type": row[2],
                        "aggregate_uuid": row[3],
                        "payload": json.loads(row[4]) if row[4] else {},
                        "event_metadata": metadata,
                        "sequence": row[6],
                        "created_at": row[7],
                    }
                )

    return events
