# Copyright (c) 2026 Kirky.X. All rights reserved.
# Licensed under the MIT License.
# See LICENSE file in the project root for full license information.

"""通用事件记录服务"""

from datetime import datetime
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session

from src.db.models import Event


def log_event(
    session: Session,
    project_id: str,
    event_type: str,
    aggregate_id: str,
    payload: Dict[str, Any],
    metadata: Optional[Dict[str, Any]] = None
):
    """

    记录事件

    Args:
        session: 数据库会话
        project_id: 项目 ID
        event_type: 事件类型
        aggregate_id: 聚合根 ID
        payload: 事件负载
        metadata: 元数据
    """
    # 获取当前序列号
    last_event = session.query(Event).filter_by(
        project_id=project_id
    ).order_by(Event.sequence.desc()).first()

    sequence = (last_event.sequence + 1) if last_event else 1

    event = Event(
        project_id=project_id,
        event_type=event_type,
        aggregate_id=aggregate_id,
        payload=payload,
        event_metadata=metadata,
        sequence=sequence
    )
    session.add(event)