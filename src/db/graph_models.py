# Copyright (c) 2026 Kirky.X. All rights reserved.
# Licensed under the MIT License.
# See LICENSE file in the project root for full license information.

"""图数据库模型定义 (Pydantic 数据类)"""

import json
import uuid
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field

# ============ 枚举类型 ============


class ProjectStatus(StrEnum):
    """项目状态枚举"""

    CREATED = "CREATED"
    DECOMPOSING = "DECOMPOSING"
    CHAINING = "CHAINING"
    READY = "READY"
    EXECUTING = "EXECUTING"
    COMPLETED = "COMPLETED"


class RequirementStatus(StrEnum):
    """需求状态枚举"""

    DRAFT = "DRAFT"
    DECOMPOSING = "DECOMPOSING"
    LEAF = "LEAF"
    CHAINED = "CHAINED"
    VALIDATED = "VALIDATED"
    COMPLETED = "COMPLETED"


class ValidationStatus(StrEnum):
    """验证状态枚举"""

    PENDING = "pending"
    PASSED = "passed"
    FAILED = "failed"


class ChainStatus(StrEnum):
    """链化状态枚举"""

    IDLE = "IDLE"
    BUILDING = "BUILDING"
    COMPLETED = "COMPLETED"


# ============ 辅助函数 ============


def generate_uuid() -> str:
    """生成 UUID 字符串"""
    return str(uuid.uuid4())


def now_utc() -> str:
    """获取当前 UTC 时间字符串 (ISO 格式)"""
    return datetime.now(UTC).isoformat()


def serialize_json(data: Any) -> str:
    """序列化为 JSON 字符串（使用 base64 编码）

    注意：LadybugDB 在存储 JSON 字符串时会移除属性名的引号，
    导致无法正确解析。因此使用 base64 编码来避免这个问题。
    """
    if data is None:
        return ""

    # 先转换为标准 JSON，再用 base64 编码
    json_str = json.dumps(data, ensure_ascii=False)
    import base64

    return base64.b64encode(json_str.encode()).decode()


def deserialize_json(data: str) -> Any:
    """反序列化 JSON 字符串（使用 base64 解码）"""
    if not data or data == "null":
        return None

    import base64

    try:
        # 尝试 base64 解码
        json_str = base64.b64decode(data.encode()).decode()
        return json.loads(json_str)
    except Exception:
        # 如果不是 base64 编码，尝试直接解析（向后兼容旧数据）
        # 对于旧数据格式（LadybugDB 移除引号后的格式），尝试修复
        if data.startswith("[{") or data.startswith("{"):
            # 尝试修复引号问题：在属性名前添加引号
            import re

            # 修复格式：{name: value} -> {"name": value}
            fixed = re.sub(r"([{,])\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*:", r'\1"\2":', data)
            # 修复字符串值（中文或其他非数字值）
            fixed = re.sub(
                r":\s*([a-zA-Z_\u4e00-\u9fff][a-zA-Z0-9_\u4e00-\u9fff]*)\s*([,}])",
                r': "\1"\2',
                fixed,
            )
            return json.loads(fixed)
        return json.loads(data)


# ============ 节点模型 ============


class ProjectNode(BaseModel):
    """项目节点"""

    uuid: str = Field(default_factory=generate_uuid)
    name: str
    description: str | None = None
    status: str = Field(default=ProjectStatus.CREATED.value)
    locked_by: str | None = None
    locked_at: str | None = None
    created_at: str = Field(default_factory=now_utc)
    updated_at: str = Field(default_factory=now_utc)

    def to_cypher_params(self) -> dict[str, Any]:
        """转换为 Cypher 参数"""
        return {
            "uuid": self.uuid,
            "name": self.name,
            "description": self.description or "",
            "status": self.status,
            "locked_by": self.locked_by or "",
            "locked_at": self.locked_at or "",
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


class RequirementNode(BaseModel):
    """需求节点"""

    uuid: str = Field(default_factory=generate_uuid)
    project_uuid: str
    parent_uuid: str | None = None
    content: str
    decompose_reason: str | None = None
    status: str = Field(default=RequirementStatus.DRAFT.value)
    level: int = Field(default=0)
    order_in_parent: int = Field(default=0)
    chain_order: int | None = None
    created_at: str = Field(default_factory=now_utc)
    updated_at: str = Field(default_factory=now_utc)
    version: int = Field(default=1)

    # 非持久化字段（从关系查询填充）
    dependencies: list[str] = Field(default_factory=list)
    next_requirement_uuid: str | None = None

    def to_cypher_params(self) -> dict[str, Any]:
        """转换为 Cypher 参数"""
        return {
            "uuid": self.uuid,
            "project_uuid": self.project_uuid,
            "parent_uuid": self.parent_uuid or "",
            "content": self.content,
            "decompose_reason": self.decompose_reason or "",
            "status": self.status,
            "level": self.level,
            "order_in_parent": self.order_in_parent,
            "chain_order": self.chain_order if self.chain_order is not None else -1,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "version": self.version,
        }


class ValidationNode(BaseModel):
    """验证节点"""

    uuid: str = Field(default_factory=generate_uuid)
    requirement_uuid: str
    test_cases: list[dict[str, Any]] = Field(default_factory=list)
    acceptance_criteria: str | None = None
    status: str = Field(default=ValidationStatus.PENDING.value)
    result: dict[str, Any] | None = None
    validated_at: str | None = None
    created_at: str = Field(default_factory=now_utc)

    def to_cypher_params(self) -> dict[str, Any]:
        """转换为 Cypher 参数"""
        return {
            "uuid": self.uuid,
            "requirement_uuid": self.requirement_uuid,
            "test_cases": serialize_json(self.test_cases),
            "acceptance_criteria": self.acceptance_criteria or "",
            "status": self.status,
            "result": serialize_json(self.result),
            "validated_at": self.validated_at or "",
            "created_at": self.created_at,
        }

    @classmethod
    def from_query_result(cls, row: dict[str, Any]) -> "ValidationNode":
        """从查询结果创建"""
        return cls(
            uuid=row.get("uuid", ""),
            requirement_uuid=row.get("requirement_uuid", ""),
            test_cases=deserialize_json(row.get("test_cases", "[]")) or [],
            acceptance_criteria=row.get("acceptance_criteria") or None,
            status=row.get("status", ValidationStatus.PENDING.value),
            result=deserialize_json(row.get("result", "null")),
            validated_at=row.get("validated_at") or None,
            created_at=row.get("created_at", now_utc()),
        )


class ChainStateNode(BaseModel):
    """链化状态节点"""

    uuid: str = Field(default_factory=generate_uuid)
    project_uuid: str
    status: str = Field(default=ChainStatus.IDLE.value)
    chain_head_uuid: str | None = None
    current_node_uuid: str | None = None
    total_nodes: int = Field(default=0)
    completed_nodes: int = Field(default=0)
    progress_percentage: int = Field(default=0)
    last_chained_at: str | None = None
    chain_version: int = Field(default=1)
    created_at: str = Field(default_factory=now_utc)
    updated_at: str = Field(default_factory=now_utc)

    def to_cypher_params(self) -> dict[str, Any]:
        """转换为 Cypher 参数"""
        return {
            "uuid": self.uuid,
            "project_uuid": self.project_uuid,
            "status": self.status,
            "chain_head_uuid": self.chain_head_uuid or "",
            "current_node_uuid": self.current_node_uuid or "",
            "total_nodes": self.total_nodes,
            "completed_nodes": self.completed_nodes,
            "progress_percentage": self.progress_percentage,
            "last_chained_at": self.last_chained_at or "",
            "chain_version": self.chain_version,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


class EventNode(BaseModel):
    """事件节点"""

    uuid: str = Field(default_factory=generate_uuid)
    project_uuid: str
    event_type: str
    aggregate_uuid: str
    payload: dict[str, Any]
    event_metadata: dict[str, Any] | None = None
    sequence: int = Field(default=1)
    created_at: str = Field(default_factory=now_utc)

    def to_cypher_params(self) -> dict[str, Any]:
        """转换为 Cypher 参数"""
        return {
            "uuid": self.uuid,
            "project_uuid": self.project_uuid,
            "event_type": self.event_type,
            "aggregate_uuid": self.aggregate_uuid,
            "payload": serialize_json(self.payload),
            "event_metadata": serialize_json(self.event_metadata),
            "sequence": self.sequence,
            "created_at": self.created_at,
        }

    @classmethod
    def from_query_result(cls, row: dict[str, Any]) -> "EventNode":
        """从查询结果创建"""
        return cls(
            uuid=row.get("uuid", ""),
            project_uuid=row.get("project_uuid", ""),
            event_type=row.get("event_type", ""),
            aggregate_uuid=row.get("aggregate_uuid", ""),
            payload=deserialize_json(row.get("payload", "{}")) or {},
            event_metadata=deserialize_json(row.get("event_metadata", "null")),
            sequence=row.get("sequence", 1),
            created_at=row.get("created_at", now_utc()),
        )


# ============ 关系类型常量 ============


class RelType:
    """关系类型常量"""

    HAS_REQUIREMENT = "HAS_REQUIREMENT"
    HAS_CHILD = "HAS_CHILD"
    HAS_VALIDATION = "HAS_VALIDATION"
    DEPENDS_ON = "DEPENDS_ON"
    NEXT_IN_CHAIN = "NEXT_IN_CHAIN"
    HAS_CHAIN_STATE = "HAS_CHAIN_STATE"
    HAS_EVENT = "HAS_EVENT"


# ============ 查询结果辅助函数 ============
