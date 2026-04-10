# Copyright (c) 2026 Kirky.X. All rights reserved.
# Licensed under the MIT License.
# See LICENSE file in the project root for full license information.

"""通用事件记录服务（增强审计日志）"""

import logging
import uuid
from typing import Any, Dict, Optional

import real_ladybug as lb

from src.db.graph_models import now_utc, serialize_json
from src.db.graph_queries import (
    CREATE_EVENT,
    CREATE_HAS_EVENT,
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
