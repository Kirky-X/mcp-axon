# Copyright (c) 2026 Kirky.X. All rights reserved.
# Licensed under the MIT License.
# See LICENSE file in the project root for full license information.

"""项目管理服务测试"""

import pytest

from src.db.graph_models import ProjectStatus


def test_tc006_project_manager_create(graph_connection, project_manager):
    """TC-006: 测试项目管理器创建项目"""

    # Act
    result = project_manager.create_project(
        graph_connection, name="测试项目", description="这是一个测试项目"
    )

    # Assert
    assert result["project_id"] is not None
    assert result["status"] == "CREATED"
    assert result["name"] == "测试项目"
    assert result["description"] == "这是一个测试项目"
    assert "created_at" in result

    # 验证可以获取项目
    project = project_manager.get_project(graph_connection, result["project_id"])
    assert project is not None
    assert project["name"] == "测试项目"
    assert project["status"] == ProjectStatus.CREATED.value


def test_project_manager_get_project(graph_connection, project_manager):
    """测试获取项目信息"""
    # Arrange
    project = project_manager.create_project(graph_connection, "测试项目", "描述")

    # Act
    result = project_manager.get_project(graph_connection, project["project_id"])

    # Assert
    assert result["project_id"] == project["project_id"]
    assert result["name"] == "测试项目"
    assert result["status"] == "CREATED"
    assert result["description"] == "描述"


def test_project_manager_update_project(graph_connection, project_manager):
    """测试更新项目信息"""
    # Arrange
    project = project_manager.create_project(graph_connection, "原名称", "原描述")

    from src.schemas import ProjectUpdate

    # Act
    result = project_manager.update_project(
        graph_connection,
        project["project_id"],
        ProjectUpdate(name="新名称", description="新描述"),
    )

    # Assert
    assert result["name"] == "新名称"
    assert result["description"] == "新描述"


def test_project_manager_get_project_state(graph_connection, project_manager):
    """测试获取项目状态"""
    # Arrange
    project = project_manager.create_project(graph_connection, "测试项目")

    # Act
    result = project_manager.get_project_state(graph_connection, project["project_id"])

    # Assert
    assert result["project_id"] == project["project_id"]
    assert result["status"] == "CREATED"
    assert result["total_requirements"] == 0
    assert result["leaf_requirements"] == 0
    assert result["validated_requirements"] == 0
    assert result["chained_requirements"] == 0


def test_project_manager_update_status(graph_connection, project_manager):
    """测试更新项目状态"""
    # Arrange
    project = project_manager.create_project(graph_connection, "测试项目")

    # Act
    project_manager.update_project_status(
        graph_connection, project["project_id"], ProjectStatus.DECOMPOSING
    )

    # Assert
    updated_project = project_manager.get_project(
        graph_connection, project["project_id"]
    )
    assert updated_project["status"] == ProjectStatus.DECOMPOSING.value


def test_project_manager_nonexistent_project(graph_connection, project_manager):
    """测试获取不存在的项目"""
    # Act & Assert
    with pytest.raises(ValueError, match="项目不存在"):
        project_manager.get_project(graph_connection, "nonexistent-id")
