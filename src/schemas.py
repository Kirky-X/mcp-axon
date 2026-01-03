# Copyright (c) 2026 Kirky.X. All rights reserved.
# Licensed under the MIT License.
# See LICENSE file in the project root for full license information.

"""Pydantic 数据校验 Schema 定义"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class ProjectCreate(BaseModel):
    """项目创建 Schema"""

    name: str = Field(..., min_length=1, max_length=200, description="项目名称")
    description: Optional[str] = Field(None, max_length=2000, description="项目描述")

    @field_validator("name")
    @classmethod
    def name_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("项目名称不能为空")
        return v.strip()


class ProjectUpdate(BaseModel):
    """项目更新 Schema"""

    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=2000)

    @field_validator("name")
    @classmethod
    def name_not_empty(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and not v.strip():
            raise ValueError("项目名称不能为空")
        return v.strip() if v else v


class ProjectResponse(BaseModel):
    """项目响应 Schema"""

    project_id: str
    name: str
    description: Optional[str]
    status: str
    locked_by: Optional[str]
    locked_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class RequirementCreate(BaseModel):
    """需求创建 Schema"""

    project_id: str = Field(..., min_length=36, max_length=36, description="项目 ID")
    content: str = Field(..., min_length=1, max_length=5000, description="需求内容")
    parent_id: Optional[str] = Field(
        None, min_length=36, max_length=36, description="父需求 ID"
    )
    order_in_parent: Optional[int] = Field(0, ge=0, description="在父需求中的顺序")

    @field_validator("content")
    @classmethod
    def content_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("需求内容不能为空")
        return v.strip()


class RequirementUpdate(BaseModel):
    """需求更新 Schema"""

    content: Optional[str] = Field(None, min_length=1, max_length=5000)
    status: Optional[str] = Field(None, description="需求状态")

    @field_validator("content")
    @classmethod
    def content_not_empty(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and not v.strip():
            raise ValueError("需求内容不能为空")
        return v.strip() if v else v


class RequirementResponse(BaseModel):
    """需求响应 Schema"""

    requirement_id: str
    project_id: str
    parent_id: Optional[str]
    content: str
    decompose_reason: Optional[str]
    status: str
    level: int
    order_in_parent: int
    dependencies: List[str]
    chain_order: Optional[int]
    next_requirement_id: Optional[str]
    created_at: datetime
    updated_at: datetime
    version: int

    model_config = ConfigDict(from_attributes=True)


class ValidationCreate(BaseModel):
    """验证节点创建 Schema"""

    requirement_id: str = Field(
        ..., min_length=36, max_length=36, description="需求 ID"
    )
    test_cases: List[Dict[str, Any]] = Field(
        default_factory=list, description="测试用例列表"
    )
    acceptance_criteria: Optional[str] = Field(
        None, max_length=2000, description="验收标准"
    )

    @field_validator("test_cases")
    @classmethod
    def validate_test_cases(cls, v: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """验证测试用例格式"""
        for i, test_case in enumerate(v):
            if not isinstance(test_case, dict):
                raise ValueError(f"测试用例 {i + 1} 必须是字典格式")
            if "name" not in test_case:
                raise ValueError(f"测试用例 {i + 1} 缺少 name 字段")
        return v


class ValidationUpdate(BaseModel):
    """验证节点更新 Schema"""

    test_cases: Optional[List[Dict[str, Any]]] = None
    acceptance_criteria: Optional[str] = Field(None, max_length=2000)
    status: Optional[str] = Field(None, description="验证状态")
    result: Optional[Dict[str, Any]] = None


class ValidationResponse(BaseModel):
    """验证节点响应 Schema"""

    validation_id: str
    requirement_id: str
    test_cases: List[Dict[str, Any]]
    acceptance_criteria: Optional[str]
    status: str
    result: Optional[Dict[str, Any]]
    validated_at: Optional[datetime]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DependencyMapping(BaseModel):
    """依赖映射 Schema"""

    parent_id: str = Field(..., min_length=36, max_length=36, description="父需求 ID")
    dependency_mapping: Dict[str, List[str]] = Field(
        ..., description="依赖映射 {子需求ID: [依赖ID列表]}"
    )

    @field_validator("dependency_mapping")
    @classmethod
    def validate_mapping(cls, v: Dict[str, List[str]]) -> Dict[str, List[str]]:
        """验证依赖映射格式"""
        for child_id, dep_ids in v.items():
            if not isinstance(dep_ids, list):
                raise ValueError(f"子需求 {child_id} 的依赖必须是列表")
            for dep_id in dep_ids:
                if not isinstance(dep_id, str) or len(dep_id) != 36:
                    raise ValueError(f"依赖 ID {dep_id} 格式不正确")
        return v


class ParallelOrderResolve(BaseModel):
    """并行节点排序 Schema"""

    project_id: str = Field(..., min_length=36, max_length=36, description="项目 ID")
    parallel_nodes: List[str] = Field(..., min_length=1, description="并行节点 ID 列表")
    sorted_order: List[str] = Field(
        ..., min_length=1, description="排序后的节点 ID 列表"
    )

    @model_validator(mode="after")
    def validate_order_consistency(self) -> "ParallelOrderResolve":
        """验证排序一致性"""
        if set(self.parallel_nodes) != set(self.sorted_order):
            raise ValueError("排序后的节点必须与并行节点一致")
        return self


class ChainBuildResponse(BaseModel):
    """链化构建响应 Schema"""

    status: str = Field(..., description="链化状态: needs_sorting, completed")
    parallel_nodes: Optional[List[str]] = Field(None, description="需要排序的并行节点")
    chain_head: Optional[str] = Field(None, description="链表头节点 ID")
    total_nodes: Optional[int] = Field(None, description="总节点数")
    message: Optional[str] = Field(None, description="提示消息")


class ProjectStateResponse(BaseModel):
    """项目状态响应 Schema"""

    project_id: str
    name: str
    status: str
    total_requirements: int
    leaf_requirements: int
    validated_requirements: int
    chained_requirements: int
    chain_status: Optional[str]
    current_node_id: Optional[str]
    progress_percentage: int
    created_at: datetime
    updated_at: datetime


class NextRequirementResponse(BaseModel):
    """下一个需求响应 Schema"""

    requirement_id: Optional[str]
    content: Optional[str]
    status: Optional[str]
    chain_order: Optional[int]
    is_last: bool
    progress_percentage: int
    message: Optional[str]


class ErrorResponse(BaseModel):
    """错误响应 Schema"""

    error: bool = True
    error_type: str
    message: str
    timestamp: datetime
    context: Optional[Dict[str, Any]] = None
    recovery: Optional[str] = None


class MCPToolResponse(BaseModel):
    """MCP 工具统一响应 Schema"""

    success: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    next_action: Optional[str] = Field(None, description="引导下一步操作")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class DependencyUpdate(BaseModel):
    """依赖更新 Schema"""

    requirement_id: str = Field(
        ..., min_length=36, max_length=36, description="需求 ID"
    )
    dependencies: List[str] = Field(..., description="依赖 ID 列表")

    @field_validator("dependencies")
    @classmethod
    def validate_dependencies(cls, v: List[str]) -> List[str]:
        """验证依赖 ID 格式"""
        if not isinstance(v, list):
            raise ValueError("依赖必须是列表")
        for dep_id in v:
            if not isinstance(dep_id, str):
                raise ValueError(f"依赖 ID {dep_id} 必须是字符串")
            if len(dep_id) != 36:
                raise ValueError(f"依赖 ID {dep_id} 格式不正确，应为 36 字符的 UUID")
        return v
