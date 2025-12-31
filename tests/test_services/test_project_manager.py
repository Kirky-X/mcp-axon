# Copyright (c) 2026 Kirky.X. All rights reserved.
# Licensed under the MIT License.
# See LICENSE file in the project root for full license information.

"""项目管理服务测试"""

import pytest
from src.db.models import Project, ChainState, ProjectStatus
from src.services.project_manager import ProjectManager


def test_tc006_project_manager_create(sync_session):
    """TC-006: 测试项目管理器创建项目"""

    # Arrange
    manager = ProjectManager()

    # Act
    result = manager.create_project(
        sync_session,
        name="测试项目",
        description="这是一个测试项目"
    )

    # Assert
    assert result["project_id"] is not None
    assert result["status"] == "CREATED"
    assert result["name"] == "测试项目"
    assert result["description"] == "这是一个测试项目"
    assert "created_at" in result

    # 验证数据库
    project = sync_session.get(Project, result["project_id"])
    assert project is not None
    assert project.name == "测试项目"
    assert project.status == ProjectStatus.CREATED.value

    # 验证链化状态已创建
    chain_state = sync_session.query(ChainState).filter_by(
        project_id=result["project_id"]
    ).first()
    assert chain_state is not None


def test_project_manager_get_project(sync_session):
    """测试获取项目信息"""
    # Arrange
    manager = ProjectManager()
    project = manager.create_project(sync_session, "测试项目", "描述")

    # Act
    result = manager.get_project(sync_session, project["project_id"])

    # Assert
    assert result["project_id"] == project["project_id"]
    assert result["name"] == "测试项目"
    assert result["status"] == "CREATED"
    assert result["description"] == "描述"


def test_project_manager_update_project(sync_session):
    """测试更新项目信息"""
    # Arrange
    manager = ProjectManager()
    project = manager.create_project(sync_session, "原名称", "原描述")

    from src.schemas import ProjectUpdate

    # Act
    result = manager.update_project(
        sync_session,
        project["project_id"],
        ProjectUpdate(name="新名称", description="新描述")
    )

    # Assert
    assert result["name"] == "新名称"
    assert result["description"] == "新描述"


def test_project_manager_get_project_state(sync_session):
    """测试获取项目状态"""
    # Arrange
    manager = ProjectManager()
    project = manager.create_project(sync_session, "测试项目")

    # Act
    result = manager.get_project_state(sync_session, project["project_id"])

    # Assert
    assert result["project_id"] == project["project_id"]
    assert result["status"] == "CREATED"
    assert result["total_requirements"] == 0
    assert result["leaf_requirements"] == 0
    assert result["validated_requirements"] == 0
    assert result["chained_requirements"] == 0


def test_project_manager_update_status(sync_session):
    """测试更新项目状态"""
    # Arrange
    manager = ProjectManager()
    project = manager.create_project(sync_session, "测试项目")

    # Act
    manager.update_project_status(
        sync_session,
        project["project_id"],
        ProjectStatus.DECOMPOSING
    )

    # Assert
    updated_project = sync_session.get(Project, project["project_id"])
    assert updated_project.status == ProjectStatus.DECOMPOSING.value


def test_project_manager_nonexistent_project(sync_session):
    """测试获取不存在的项目"""
    # Arrange
    manager = ProjectManager()

    # Act & Assert
    with pytest.raises(ValueError, match="项目不存在"):
        manager.get_project(sync_session, "nonexistent-id")