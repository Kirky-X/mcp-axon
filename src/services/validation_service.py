# Copyright (c) 2026 Kirky.X. All rights reserved.
# Licensed under the MIT License.
# See LICENSE file in the project root for full license information.

"""验证节点管理服务"""

import logging
import uuid
from typing import Any

import real_ladybug as lb

from src.db.graph_models import (
    RequirementStatus,
    ValidationStatus,
    deserialize_json,
    now_utc,
    serialize_json,
)
from src.db.graph_queries import (
    CREATE_HAS_VALIDATION,
    CREATE_VALIDATION,
    DELETE_VALIDATION,
    GET_CHILDREN,
    GET_REQUIREMENT_BY_UUID,
    GET_VALIDATION_BY_REQUIREMENT,
    GET_VALIDATION_BY_UUID,
    UPDATE_REQUIREMENT_STATUS,
    UPDATE_VALIDATION,
)
from src.schemas import ValidationUpdate
from src.utils.cache import CacheManager
from src.utils.event_logger import log_event
from src.utils.metrics import performance_monitor

logger = logging.getLogger(__name__)


class ValidationService:
    """验证节点管理服务"""

    def __init__(self, cache: CacheManager):
        """初始化验证服务

        Args:
            cache: 缓存管理器实例
        """
        self.cache = cache

    @performance_monitor("add_validation")
    def add_validation(
        self,
        conn: lb.Connection,
        requirement_uuid: str,
        test_cases: list[dict[str, Any]],
        acceptance_criteria: str = "",
    ) -> dict[str, Any]:
        """
        添加验证节点

        注意: 只能为叶子节点添加验证

        Args:
            conn: 数据库连接
            requirement_uuid: 需求 ID
            test_cases: 测试用例列表
            acceptance_criteria: 验收标准

        Returns:
            验证节点信息
        """
        # 获取需求
        result = conn.execute(GET_REQUIREMENT_BY_UUID, {"uuid": requirement_uuid})
        rows = list(result)
        if not rows:
            raise ValueError(f"需求不存在: {requirement_uuid}")

        requirement = rows[0]
        project_uuid = requirement[1]  # project_uuid
        current_status = requirement[5]  # status

        # 检查是否已有验证节点
        existing_result = conn.execute(
            GET_VALIDATION_BY_REQUIREMENT, {"requirement_uuid": requirement_uuid}
        )
        if list(existing_result):
            raise ValueError("已有验证节点")

        # 检查是否为叶子节点
        if current_status != RequirementStatus.LEAF.value:
            raise ValueError(f"只能为叶子节点添加验证，当前状态: {current_status}")

        # 检查是否已有子需求
        children_result = conn.execute(GET_CHILDREN, {"parent_uuid": requirement_uuid})
        children_count = len(list(children_result))
        if children_count > 0:
            raise ValueError(
                f"只能为叶子节点添加验证，该需求已有 {children_count} 个子需求"
            )

        # 创建验证节点
        validation_uuid = str(uuid.uuid4())
        created_at = now_utc()

        conn.execute(
            CREATE_VALIDATION,
            {
                "uuid": validation_uuid,
                "requirement_uuid": requirement_uuid,
                "test_cases": serialize_json(test_cases),
                "acceptance_criteria": acceptance_criteria,
                "status": ValidationStatus.PENDING.value,
                "result": "null",
                "validated_at": "",
                "created_at": created_at,
            },
        )

        # 创建 HAS_VALIDATION 边
        conn.execute(
            CREATE_HAS_VALIDATION,
            {"requirement_uuid": requirement_uuid, "validation_uuid": validation_uuid},
        )

        # 更新需求状态为 VALIDATED
        old_status = current_status
        conn.execute(
            UPDATE_REQUIREMENT_STATUS,
            {
                "uuid": requirement_uuid,
                "status": RequirementStatus.VALIDATED.value,
                "updated_at": now_utc(),
            },
        )

        # 刷新缓存
        self.cache.invalidate_requirement(requirement_uuid, project_uuid)
        self.cache.invalidate_project(project_uuid)

        # 记录事件
        log_event(
            conn,
            project_uuid,
            "ValidationAdded",
            validation_uuid,
            {
                "requirement_uuid": requirement_uuid,
                "test_cases_count": len(test_cases),
                "acceptance_criteria": acceptance_criteria,
                "old_status": old_status,
                "new_status": RequirementStatus.VALIDATED.value,
            },
        )

        logger.info(f"验证节点添加成功: {validation_uuid}")

        return {
            "validation_id": validation_uuid,
            "requirement_id": requirement_uuid,
            "test_cases": test_cases,
            "acceptance_criteria": acceptance_criteria,
            "status": ValidationStatus.PENDING.value,
            "created_at": created_at,
        }

    def update_validation(
        self, conn: lb.Connection, validation_uuid: str, update_data: ValidationUpdate
    ) -> dict[str, Any]:
        """
        更新验证节点

        Args:
            conn: 数据库连接
            validation_uuid: 验证节点 ID
            update_data: 更新数据

        Returns:
            更新后的验证节点信息
        """
        result = conn.execute(GET_VALIDATION_BY_UUID, {"uuid": validation_uuid})
        rows = list(result)
        if not rows:
            raise ValueError(f"验证节点不存在: {validation_uuid}")

        validation = rows[0]
        requirement_uuid = validation[1]  # requirement_uuid
        project_uuid = None

        # 获取 project_uuid
        req_result = conn.execute(GET_REQUIREMENT_BY_UUID, {"uuid": requirement_uuid})
        req_rows = list(req_result)
        if req_rows:
            project_uuid = req_rows[0][1]

        # 准备更新参数
        test_cases = validation[2]  # test_cases (JSON string)
        acceptance_criteria = validation[3] or ""  # acceptance_criteria
        status = validation[4]  # status
        result_json = validation[5] or "null"  # result
        validated_at = validation[6] or ""  # validated_at

        if update_data.test_cases is not None:
            test_cases = serialize_json(update_data.test_cases)

        if update_data.acceptance_criteria is not None:
            acceptance_criteria = update_data.acceptance_criteria

        if update_data.status is not None:
            old_status = status
            status = update_data.status

            # 如果状态为 passed 或 failed，记录验证时间
            if update_data.status in ["passed", "failed"]:
                validated_at = now_utc()

            # 记录事件
            if project_uuid:
                log_event(
                    conn,
                    project_uuid,
                    "ValidationStatusChanged",
                    validation_uuid,
                    {
                        "requirement_uuid": requirement_uuid,
                        "old_status": old_status,
                        "new_status": update_data.status,
                    },
                )

        if update_data.result is not None:
            result_json = serialize_json(update_data.result)

        # 执行更新
        conn.execute(
            UPDATE_VALIDATION,
            {
                "uuid": validation_uuid,
                "test_cases": test_cases,
                "acceptance_criteria": acceptance_criteria,
                "status": status,
                "result": result_json,
                "validated_at": validated_at,
            },
        )

        logger.info(f"验证节点更新成功: {validation_uuid}")

        return {
            "validation_id": validation_uuid,
            "requirement_id": requirement_uuid,
            "test_cases": deserialize_json(test_cases) if test_cases else [],
            "acceptance_criteria": acceptance_criteria,
            "status": status,
            "result": deserialize_json(result_json) if result_json else None,
            "validated_at": validated_at if validated_at else None,
        }

    def get_validation(
        self, conn: lb.Connection, validation_uuid: str
    ) -> dict[str, Any]:
        """
        获取验证节点信息

        Args:
            conn: 数据库连接
            validation_uuid: 验证节点 ID

        Returns:
            验证节点信息
        """
        result = conn.execute(GET_VALIDATION_BY_UUID, {"uuid": validation_uuid})
        rows = list(result)
        if not rows:
            raise ValueError(f"验证节点不存在: {validation_uuid}")

        row = rows[0]
        return {
            "validation_id": row[0],
            "requirement_id": row[1],
            "test_cases": deserialize_json(row[2]) if row[2] else [],
            "acceptance_criteria": row[3],
            "status": row[4],
            "result": deserialize_json(row[5]) if row[5] else None,
            "validated_at": row[6] if row[6] else None,
            "created_at": row[7],
        }

    def get_validation_by_requirement(
        self, conn: lb.Connection, requirement_uuid: str
    ) -> dict[str, Any] | None:
        """
        根据需求 ID 获取验证节点

        Args:
            conn: 数据库连接
            requirement_uuid: 需求 ID

        Returns:
            验证节点信息，如果不存在则返回 None
        """
        result = conn.execute(
            GET_VALIDATION_BY_REQUIREMENT, {"requirement_uuid": requirement_uuid}
        )
        rows = list(result)

        if not rows:
            return None

        row = rows[0]
        return {
            "validation_id": row[0],
            "requirement_id": row[1],
            "test_cases": deserialize_json(row[2]) if row[2] else [],
            "acceptance_criteria": row[3],
            "status": row[4],
            "result": deserialize_json(row[5]) if row[5] else None,
            "validated_at": row[6] if row[6] else None,
            "created_at": row[7],
        }

    def delete_validation(
        self, conn: lb.Connection, validation_uuid: str
    ) -> dict[str, Any]:
        """
        删除验证节点

        Args:
            conn: 数据库连接
            validation_uuid: 验证节点 ID

        Returns:
            删除结果
        """
        result = conn.execute(GET_VALIDATION_BY_UUID, {"uuid": validation_uuid})
        rows = list(result)
        if not rows:
            raise ValueError(f"验证节点不存在: {validation_uuid}")

        validation = rows[0]
        requirement_uuid = validation[1]  # requirement_uuid

        # 获取 project_uuid
        project_uuid = None
        req_result = conn.execute(GET_REQUIREMENT_BY_UUID, {"uuid": requirement_uuid})
        req_rows = list(req_result)
        if req_rows:
            project_uuid = req_rows[0][1]

        # 删除验证节点
        conn.execute(DELETE_VALIDATION, {"uuid": validation_uuid})

        # 记录事件
        if project_uuid:
            log_event(
                conn,
                project_uuid,
                "ValidationDeleted",
                validation_uuid,
                {"requirement_uuid": requirement_uuid},
            )

        logger.info(f"验证节点删除成功: {validation_uuid}")

        return {"validation_id": validation_uuid, "deleted": True}
