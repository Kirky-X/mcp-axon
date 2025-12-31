# Copyright (c) 2026 Kirky.X. All rights reserved.
# Licensed under the MIT License.
# See LICENSE file in the project root for full license information.

"""验证节点管理服务"""

import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session

from src.db.models import (
    ValidationNode, Requirement, RequirementStatus, ValidationStatus, Event
)
from src.schemas import ValidationCreate, ValidationUpdate
from src.utils.metrics import performance_monitor

logger = logging.getLogger(__name__)


class ValidationService:
    """验证节点管理服务"""

    def __init__(self):
        """初始化验证服务"""
        pass

    @performance_monitor("add_validation")
    def add_validation(
        self,
        session: Session,
        requirement_id: str,
        test_cases: List[Dict[str, Any]],
        acceptance_criteria: str = ""
    ) -> Dict[str, Any]:
        """
        添加验证节点

        注意: 只能为叶子节点添加验证

        Args:
            session: 数据库会话
            requirement_id: 需求 ID
            test_cases: 测试用例列表
            acceptance_criteria: 验收标准

        Returns:
            验证节点信息
        """
        # 获取需求
        requirement = session.query(Requirement).filter_by(
            id=requirement_id
        ).first()

        if not requirement:
            raise ValueError(f"需求不存在: {requirement_id}")

        # 检查是否已有验证节点
        existing = session.query(ValidationNode).filter_by(
            requirement_id=requirement_id
        ).first()

        if existing:
            raise ValueError("已有验证节点")

        # 检查是否为叶子节点
        if requirement.status != RequirementStatus.LEAF.value:
            raise ValueError(
                f"只能为叶子节点添加验证，当前状态: {requirement.status}"
            )

        # 创建验证节点
        validation = ValidationNode(
            requirement_id=requirement_id,
            test_cases=test_cases,
            acceptance_criteria=acceptance_criteria,
            status=ValidationStatus.PENDING.value
        )
        session.add(validation)
        session.flush()

        # 更新需求状态为 VALIDATED
        old_status = requirement.status
        requirement.status = RequirementStatus.VALIDATED.value
        requirement.updated_at = datetime.now(timezone.utc)

        # 记录事件
        self._log_event(
            session,
            requirement.project_id,
            "ValidationAdded",
            validation.id,
            {
                "requirement_id": requirement_id,
                "test_cases_count": len(test_cases),
                "acceptance_criteria": acceptance_criteria,
                "old_status": old_status,
                "new_status": RequirementStatus.VALIDATED.value
            }
        )

        session.commit()

        logger.info(f"验证节点添加成功: {validation.id}")

        return {
            "validation_id": validation.id,
            "requirement_id": validation.requirement_id,
            "test_cases": validation.test_cases,
            "acceptance_criteria": validation.acceptance_criteria,
            "status": validation.status,
            "created_at": validation.created_at.isoformat()
        }

    def update_validation(
        self,
        session: Session,
        validation_id: str,
        update_data: ValidationUpdate
    ) -> Dict[str, Any]:
        """
        更新验证节点

        Args:
            session: 数据库会话
            validation_id: 验证节点 ID
            update_data: 更新数据

        Returns:
            更新后的验证节点信息
        """
        validation = session.query(ValidationNode).filter_by(
            id=validation_id
        ).first()

        if not validation:
            raise ValueError(f"验证节点不存在: {validation_id}")

        # 更新测试用例
        if update_data.test_cases is not None:
            validation.test_cases = update_data.test_cases

        # 更新验收标准
        if update_data.acceptance_criteria is not None:
            validation.acceptance_criteria = update_data.acceptance_criteria

        # 更新状态
        if update_data.status is not None:
            old_status = validation.status
            validation.status = update_data.status

            # 如果状态为 passed 或 failed，记录验证时间
            if update_data.status in ['passed', 'failed']:
                validation.validated_at = datetime.now(timezone.utc)

            # 记录事件
            self._log_event(
                session,
                validation.requirement.project_id,
                "ValidationStatusChanged",
                validation_id,
                {
                    "requirement_id": validation.requirement_id,
                    "old_status": old_status,
                    "new_status": update_data.status
                }
            )

        # 更新结果
        if update_data.result is not None:
            validation.result = update_data.result

        session.commit()

        logger.info(f"验证节点更新成功: {validation_id}")

        return {
            "validation_id": validation.id,
            "requirement_id": validation.requirement_id,
            "test_cases": validation.test_cases,
            "acceptance_criteria": validation.acceptance_criteria,
            "status": validation.status,
            "result": validation.result,
            "validated_at": validation.validated_at.isoformat() if validation.validated_at else None
        }

    def get_validation(
        self,
        session: Session,
        validation_id: str
    ) -> Dict[str, Any]:
        """
        获取验证节点信息

        Args:
            session: 数据库会话
            validation_id: 验证节点 ID

        Returns:
            验证节点信息
        """
        validation = session.query(ValidationNode).filter_by(
            id=validation_id
        ).first()

        if not validation:
            raise ValueError(f"验证节点不存在: {validation_id}")

        return {
            "validation_id": validation.id,
            "requirement_id": validation.requirement_id,
            "test_cases": validation.test_cases,
            "acceptance_criteria": validation.acceptance_criteria,
            "status": validation.status,
            "result": validation.result,
            "validated_at": validation.validated_at.isoformat() if validation.validated_at else None,
            "created_at": validation.created_at.isoformat()
        }

    def get_validation_by_requirement(
        self,
        session: Session,
        requirement_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        根据需求 ID 获取验证节点

        Args:
            session: 数据库会话
            requirement_id: 需求 ID

        Returns:
            验证节点信息，如果不存在则返回 None
        """
        validation = session.query(ValidationNode).filter_by(
            requirement_id=requirement_id
        ).first()

        if not validation:
            return None

        return {
            "validation_id": validation.id,
            "requirement_id": validation.requirement_id,
            "test_cases": validation.test_cases,
            "acceptance_criteria": validation.acceptance_criteria,
            "status": validation.status,
            "result": validation.result,
            "validated_at": validation.validated_at.isoformat() if validation.validated_at else None,
            "created_at": validation.created_at.isoformat()
        }

    def delete_validation(
        self,
        session: Session,
        validation_id: str
    ) -> Dict[str, Any]:
        """
        删除验证节点

        Args:
            session: 数据库会话
            validation_id: 验证节点 ID

        Returns:
            删除结果
        """
        validation = session.query(ValidationNode).filter_by(
            id=validation_id
        ).first()

        if not validation:
            raise ValueError(f"验证节点不存在: {validation_id}")

        requirement_id = validation.requirement_id
        project_id = validation.requirement.project_id

        # 删除验证节点
        session.delete(validation)

        # 记录事件
        self._log_event(
            session,
            project_id,
            "ValidationDeleted",
            validation_id,
            {
                "requirement_id": requirement_id
            }
        )

        session.commit()

        logger.info(f"验证节点删除成功: {validation_id}")

        return {
            "validation_id": validation_id,
            "deleted": True
        }

    def _log_event(
        self,
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