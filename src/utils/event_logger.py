# Copyright (c) 2026 Kirky.X. All rights reserved.
# Licensed under the MIT License.
# See LICENSE file in the project root for full license information.

"""通用事件记录服务（增强审计日志）"""

import functools
import logging
from typing import Any, Dict, Optional

from sqlalchemy.orm import Session

from src.db.models import Event

logger = logging.getLogger(__name__)


def log_event_decorator(event_type: str):
    """事件记录装饰器

    Args:
        event_type: 事件类型

    Returns:
        装饰器函数
    """

    def decorator(func):
        @functools.wraps(func)
        def wrapper(self, session: Session, *args, **kwargs):
            # 执行原函数
            result = func(self, session, *args, **kwargs)

            # 从结果中提取必要信息
            if isinstance(result, dict) and "project_id" in result:
                project_id = result["project_id"]
                aggregate_id = (
                    result.get("id")
                    or result.get("requirement_id")
                    or result.get("project_id")
                )

                # 记录事件
                log_event(
                    session=session,
                    project_id=project_id,
                    event_type=event_type,
                    aggregate_id=aggregate_id,
                    payload=result,
                )

            return result

        return wrapper

    return decorator


def log_event(
    session: Session,
    project_id: str,
    event_type: str,
    aggregate_id: Optional[str],
    payload: Dict[str, Any],
    metadata: Optional[Dict[str, Any]] = None,
    session_id: Optional[str] = None,
) -> Event:
    """
    记录事件（增强审计版本）

    Args:
        session: 数据库会话
        project_id: 项目 ID
        event_type: 事件类型
        aggregate_id: 聚合根 ID
        payload: 事件负载
        metadata: 元数据
        session_id: 会话 ID（用于审计追踪）

    Returns:
        创建的事件对象
    """
    # 获取当前序列号
    last_event = (
        session.query(Event)
        .filter_by(project_id=project_id)
        .order_by(Event.sequence.desc())
        .first()
    )

    sequence = (last_event.sequence + 1) if last_event else 1

    # 增强元数据
    enhanced_metadata = metadata or {}
    if session_id:
        enhanced_metadata["session_id"] = session_id

    event = Event(
        project_id=project_id,
        event_type=event_type,
        aggregate_id=aggregate_id,
        payload=payload,
        event_metadata=enhanced_metadata,
        sequence=sequence,
    )
    session.add(event)

    # 记录日志
    logger.info(
        f"事件记录: {event_type} | 项目: {project_id} | 聚合: {aggregate_id} | "
        f"序列: {sequence} | 会话: {session_id or 'N/A'}"
    )

    return event


def log_sensitive_event(
    session: Session,
    project_id: str,
    event_type: str,
    aggregate_id: str,
    payload: Dict[str, Any],
    metadata: Optional[Dict[str, Any]] = None,
    session_id: Optional[str] = None,
    sensitive_fields: Optional[list] = None,
) -> Event:
    """
    记录敏感事件（自动过滤敏感字段）

    Args:
        session: 数据库会话
        project_id: 项目 ID
        event_type: 事件类型
        aggregate_id: 聚合根 ID
        payload: 事件负载
        metadata: 元数据
        session_id: 会话 ID
        sensitive_fields: 敏感字段列表（将被过滤）

    Returns:
        创建的事件对象
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
            f"项目: {project_id}"
        )

    return log_event(
        session=session,
        project_id=project_id,
        event_type=event_type,
        aggregate_id=aggregate_id,
        payload=safe_payload,
        metadata=metadata,
        session_id=session_id,
    )


def get_event_history(
    session: Session,
    project_id: str,
    event_type: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
) -> list[Event]:
    """
    获取事件历史

    Args:
        session: 数据库会话
        project_id: 项目 ID
        event_type: 事件类型（可选）
        limit: 返回数量限制
        offset: 偏移量

    Returns:
        事件列表
    """
    query = session.query(Event).filter_by(project_id=project_id)

    if event_type:
        query = query.filter_by(event_type=event_type)

    return query.order_by(Event.sequence.desc()).limit(limit).offset(offset).all()


def get_events_by_session(
    session: Session,
    session_id: str,
    limit: int = 100,
) -> list[Event]:
    """
    获取特定会话的事件

    Args:
        session: 数据库会话
        session_id: 会话 ID
        limit: 返回数量限制

    Returns:
        事件列表
    """
    return (
        session.query(Event)
        .filter(Event.event_metadata["session_id"].astext == session_id)
        .order_by(Event.sequence.desc())
        .limit(limit)
        .all()
    )
