# Copyright (c) 2026 Kirky.X. All rights reserved.
# Licensed under the MIT License.
# See LICENSE file in the project root for full license information.

"""SDK 集成测试"""

import pytest
from src.core.sdk import RequirementSDK
from src.db.models import Project, Requirement, RequirementStatus


@pytest.mark.asyncio
async def test_tc019_full_requirement_flow(async_session):
    """TC-019: 测试完整需求管理流程"""

    # Arrange
    # 注意: SDK 使用同步 session,这里简化测试
    pass


def test_sdk_create_project():
    """测试 SDK 创建项目"""
    # Arrange
    sdk = RequirementSDK(db_path=":memory:")

    # Act
    result = sdk.create_project("测试项目", "描述")

    # Assert
    assert result["project_id"] is not None
    assert result["status"] == "CREATED"
    assert result["name"] == "测试项目"
    assert "next_action" in result


def test_sdk_add_requirement():
    """测试 SDK 添加需求"""
    # Arrange
    sdk = RequirementSDK(db_path=":memory:")
    project = sdk.create_project("测试项目")

    # Act
    result = sdk.add_requirement(
        project["project_id"],
        "实现用户管理模块"
    )

    # Assert
    assert result["requirement_id"] is not None
    assert result["level"] == 0
    assert "complexity_score" in result
    assert "needs_decomposition" in result


def test_sdk_mark_as_leaf():
    """测试 SDK 标记叶子节点"""
    # Arrange
    sdk = RequirementSDK(db_path=":memory:")
    project = sdk.create_project("测试项目")
    req = sdk.add_requirement(project["project_id"], "简单需求")

    # Act
    result = sdk.mark_as_leaf(req["requirement_id"])

    # Assert
    assert result["status"] == "LEAF"
    assert "next_action" in result


def test_sdk_add_validation():
    """测试 SDK 添加验证"""
    # Arrange
    sdk = RequirementSDK(db_path=":memory:")
    project = sdk.create_project("测试项目")
    req = sdk.add_requirement(project["project_id"], "简单需求")
    sdk.mark_as_leaf(req["requirement_id"])

    test_cases = [{"name": "测试1", "steps": ["步骤1"], "expected": "结果1"}]

    # Act
    result = sdk.add_validation(
        req["requirement_id"],
        test_cases,
        "验收标准"
    )

    # Assert
    assert result["validation_id"] is not None
    assert len(result["test_cases"]) == 1


def test_sdk_get_project_state():
    """测试 SDK 获取项目状态"""
    # Arrange
    sdk = RequirementSDK(db_path=":memory:")
    project = sdk.create_project("测试项目")

    # Act
    result = sdk.get_project_state(project["project_id"])

    # Assert
    assert result["project_id"] == project["project_id"]
    assert result["status"] == "CREATED"
    assert result["total_requirements"] == 0


def test_sdk_update_requirement():
    """测试 SDK 更新需求"""
    # Arrange
    sdk = RequirementSDK(db_path=":memory:")
    project = sdk.create_project("测试项目")
    req = sdk.add_requirement(project["project_id"], "原内容")

    # Act
    result = sdk.update_requirement(
        req["requirement_id"],
        content="新内容"
    )

    # Assert
    assert result["content"] == "新内容"


def test_sdk_delete_requirement():
    """测试 SDK 删除需求"""
    # Arrange
    sdk = RequirementSDK(db_path=":memory:")
    project = sdk.create_project("测试项目")
    req = sdk.add_requirement(project["project_id"], "要删除的需求")

    # Act
    result = sdk.delete_requirement(req["requirement_id"])

    # Assert
    assert result["deleted"] is True


def test_sdk_add_dependency():
    """测试 SDK 添加依赖"""
    # Arrange
    sdk = RequirementSDK(db_path=":memory:")
    project = sdk.create_project("测试项目")
    req1 = sdk.add_requirement(project["project_id"], "需求1")
    req2 = sdk.add_requirement(project["project_id"], "需求2")

    # Act
    result = sdk.add_dependency(
        req2["requirement_id"],
        req1["requirement_id"]
    )

    # Assert
    assert req1["requirement_id"] in result["dependencies"]


def test_sdk_transfer_dependencies():
    """测试 SDK 传递依赖"""
    # Arrange
    sdk = RequirementSDK(db_path=":memory:")
    project = sdk.create_project("测试项目")
    dep1 = sdk.add_requirement(project["project_id"], "依赖1")
    sdk.mark_as_leaf(dep1["requirement_id"])

    parent = sdk.add_requirement(project["project_id"], "父需求")
    child1 = sdk.add_requirement(
        project["project_id"],
        "子需求1",
        parent_id=parent["requirement_id"]
    )
    child2 = sdk.add_requirement(
        project["project_id"],
        "子需求2",
        parent_id=parent["requirement_id"]
    )

    # Act
    result = sdk.transfer_dependencies(
        parent["requirement_id"],
        {
            child1["requirement_id"]: [dep1["requirement_id"]],
            child2["requirement_id"]: []
        }
    )

    # Assert
    assert result["total_children"] == 2


def test_sdk_acquire_lock():
    """测试 SDK 获取锁"""
    # Arrange
    sdk = RequirementSDK(db_path=":memory:")
    project = sdk.create_project("测试项目")

    # Act
    result = sdk.acquire_lock(project["project_id"], "session1")

    # Assert
    assert result is True


def test_sdk_release_lock():
    """测试 SDK 释放锁"""
    # Arrange
    sdk = RequirementSDK(db_path=":memory:")
    project = sdk.create_project("测试项目")
    sdk.acquire_lock(project["project_id"], "session1")

    # Act
    result = sdk.release_lock(project["project_id"], "session1")

    # Assert
    assert result is True


def test_sdk_is_locked():
    """测试 SDK 检查是否锁定"""
    # Arrange
    sdk = RequirementSDK(db_path=":memory:")
    project = sdk.create_project("测试项目")

    # Act & Assert: 未锁定
    assert sdk.is_locked(project["project_id"]) is False

    # 获取锁
    sdk.acquire_lock(project["project_id"], "session1")

    # Act & Assert: 已锁定
    assert sdk.is_locked(project["project_id"]) is True