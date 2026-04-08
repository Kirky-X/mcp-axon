# Copyright (c) 2026 Kirky.X. All rights reserved.
# Licensed under the MIT License.
# See LICENSE file in the project root for full license information.

"""验证节点管理服务测试"""

import pytest

from src.db.graph_models import RequirementStatus, ValidationStatus


def test_tc010_add_validation(
    graph_connection, project_manager, requirement_manager, validation_service
):
    """TC-010: 测试添加验证节点"""

    # Arrange
    project = project_manager.create_project(graph_connection, "测试项目")
    project_id = project["project_id"]

    requirement = requirement_manager.add_requirement(
        graph_connection, project_id, "叶子需求"
    )

    test_cases = [
        {
            "name": "测试用户注册",
            "steps": ["打开页面", "输入信息", "提交"],
            "expected": "注册成功",
        }
    ]

    # Act
    result = validation_service.add_validation(
        graph_connection,
        requirement_uuid=requirement["requirement_id"],
        test_cases=test_cases,
        acceptance_criteria="用户能成功注册",
    )

    # Assert
    assert result["validation_id"] is not None
    assert result["requirement_id"] == requirement["requirement_id"]
    assert len(result["test_cases"]) == 1
    assert result["acceptance_criteria"] == "用户能成功注册"

    # 验证需求状态更新为 VALIDATED
    updated_req = requirement_manager.get_requirement(
        graph_connection, requirement["requirement_id"]
    )
    assert updated_req["status"] == RequirementStatus.VALIDATED.value


def test_add_validation_non_leaf_requirement(
    graph_connection, project_manager, requirement_manager, validation_service
):
    """测试为非叶子节点添加验证（应失败）"""
    # Arrange
    project = project_manager.create_project(graph_connection, "测试项目")
    project_id = project["project_id"]

    parent = requirement_manager.add_requirement(graph_connection, project_id, "父需求")
    requirement_manager.add_requirement(
        graph_connection, project_id, "子需求", parent_uuid=parent["requirement_id"]
    )

    # Act & Assert
    with pytest.raises(ValueError, match="只能为叶子节点添加验证"):
        validation_service.add_validation(
            graph_connection,
            requirement_uuid=parent["requirement_id"],
            test_cases=[{"name": "测试"}],
        )


def test_add_validation_duplicate(
    graph_connection, project_manager, requirement_manager, validation_service
):
    """测试添加重复的验证节点（应失败）"""
    # Arrange
    project = project_manager.create_project(graph_connection, "测试项目")
    project_id = project["project_id"]

    requirement = requirement_manager.add_requirement(
        graph_connection, project_id, "叶子需求"
    )

    # 添加第一个验证节点
    validation_service.add_validation(
        graph_connection,
        requirement_uuid=requirement["requirement_id"],
        test_cases=[{"name": "测试1"}],
    )

    # Act & Assert: 尝试添加第二个验证节点
    with pytest.raises(ValueError, match="已有验证节点"):
        validation_service.add_validation(
            graph_connection,
            requirement_uuid=requirement["requirement_id"],
            test_cases=[{"name": "测试2"}],
        )


def test_get_validation(
    graph_connection, project_manager, requirement_manager, validation_service
):
    """测试获取验证节点"""
    # Arrange
    project = project_manager.create_project(graph_connection, "测试项目")
    project_id = project["project_id"]

    requirement = requirement_manager.add_requirement(
        graph_connection, project_id, "叶子需求"
    )

    validation_result = validation_service.add_validation(
        graph_connection,
        requirement_uuid=requirement["requirement_id"],
        test_cases=[{"name": "测试"}],
    )

    # Act
    result = validation_service.get_validation(
        graph_connection, validation_result["validation_id"]
    )

    # Assert
    assert result["validation_id"] == validation_result["validation_id"]
    assert result["requirement_id"] == requirement["requirement_id"]
    assert len(result["test_cases"]) == 1


def test_get_validation_by_requirement(
    graph_connection, project_manager, requirement_manager, validation_service
):
    """测试根据需求 ID 获取验证节点"""
    # Arrange
    project = project_manager.create_project(graph_connection, "测试项目")
    project_id = project["project_id"]

    requirement = requirement_manager.add_requirement(
        graph_connection, project_id, "叶子需求"
    )

    validation_service.add_validation(
        graph_connection,
        requirement_uuid=requirement["requirement_id"],
        test_cases=[{"name": "测试"}],
    )

    # Act
    result = validation_service.get_validation_by_requirement(
        graph_connection, requirement["requirement_id"]
    )

    # Assert
    assert result is not None
    assert result["requirement_id"] == requirement["requirement_id"]


def test_get_validation_by_requirement_not_found(
    graph_connection, project_manager, requirement_manager, validation_service
):
    """测试获取不存在的验证节点"""
    # Arrange
    project = project_manager.create_project(graph_connection, "测试项目")
    project_id = project["project_id"]

    requirement = requirement_manager.add_requirement(
        graph_connection, project_id, "叶子需求"
    )

    # Act
    result = validation_service.get_validation_by_requirement(
        graph_connection, requirement["requirement_id"]
    )

    # Assert
    assert result is None


def test_update_validation(
    graph_connection, project_manager, requirement_manager, validation_service
):
    """测试更新验证节点"""
    # Arrange
    project = project_manager.create_project(graph_connection, "测试项目")
    project_id = project["project_id"]

    requirement = requirement_manager.add_requirement(
        graph_connection, project_id, "叶子需求"
    )

    validation_result = validation_service.add_validation(
        graph_connection,
        requirement_uuid=requirement["requirement_id"],
        test_cases=[{"name": "测试1"}],
    )

    from src.schemas import ValidationUpdate

    # Act
    result = validation_service.update_validation(
        graph_connection,
        validation_result["validation_id"],
        ValidationUpdate(
            test_cases=[{"name": "测试2"}, {"name": "测试3"}],
            status=ValidationStatus.PASSED.value,
        ),
    )

    # Assert
    assert len(result["test_cases"]) == 2
    assert result["status"] == "passed"
    assert result["validated_at"] is not None


def test_delete_validation(
    graph_connection, project_manager, requirement_manager, validation_service
):
    """测试删除验证节点"""
    # Arrange
    project = project_manager.create_project(graph_connection, "测试项目")
    project_id = project["project_id"]

    requirement = requirement_manager.add_requirement(
        graph_connection, project_id, "叶子需求"
    )

    validation_result = validation_service.add_validation(
        graph_connection,
        requirement_uuid=requirement["requirement_id"],
        test_cases=[{"name": "测试"}],
    )

    # Act
    result = validation_service.delete_validation(
        graph_connection, validation_result["validation_id"]
    )

    # Assert
    assert result["deleted"] is True

    # 验证数据库中已删除
    deleted_validation = validation_service.get_validation_by_requirement(
        graph_connection, requirement["requirement_id"]
    )
    assert deleted_validation is None


def test_add_validation_multiple_test_cases(
    graph_connection, project_manager, requirement_manager, validation_service
):
    """测试添加多个测试用例"""
    # Arrange
    project = project_manager.create_project(graph_connection, "测试项目")
    project_id = project["project_id"]

    requirement = requirement_manager.add_requirement(
        graph_connection, project_id, "叶子需求"
    )

    test_cases = [
        {"name": "测试1", "steps": ["步骤1", "步骤2"], "expected": "结果1"},
        {"name": "测试2", "steps": ["步骤A", "步骤B"], "expected": "结果2"},
        {"name": "测试3", "steps": ["步骤X", "步骤Y"], "expected": "结果3"},
    ]

    # Act
    result = validation_service.add_validation(
        graph_connection,
        requirement_uuid=requirement["requirement_id"],
        test_cases=test_cases,
    )

    # Assert
    assert len(result["test_cases"]) == 3
