# Copyright (c) 2026 Kirky.X. All rights reserved.
# Licensed under the MIT License.
# See LICENSE file in the project root for full license information.

"""需求管理服务测试"""

import pytest
from src.db.models import Project, Requirement, RequirementStatus, ProjectStatus
from src.services.requirement_manager import RequirementManager


def test_tc007_complexity_evaluation(sync_session):
    """TC-007: 测试复杂度评估"""

    # Arrange
    manager = RequirementManager()

    # Test Case 1: 简单需求
    simple_content = "实现用户登录"
    score1 = manager._evaluate_complexity(simple_content, level=1)
    assert score1 < 0.5

    # Test Case 2: 复杂需求
    complex_content = "实现完整的用户管理模块系统，包括用户注册、登录、权限控制、角色管理等功能，并集成第三方认证平台"
    score2 = manager._evaluate_complexity(complex_content, level=0)
    assert score2 > 0.7

    # Test Case 3: 关键词匹配
    keyword_content = "设计微服务架构的API网关模块"
    score3 = manager._evaluate_complexity(keyword_content, level=0)
    assert score3 >= 0.5


def test_tc008_add_requirement(sync_session):
    """TC-008: 测试添加需求"""
    # Arrange
    manager = RequirementManager()
    project = Project(name="测试项目")
    sync_session.add(project)
    sync_session.commit()

    # Act
    result = manager.add_requirement(
        sync_session,
        project_id=project.id,
        content="实现用户管理模块系统",
        parent_id=None
    )

    # Assert
    assert result["requirement_id"] is not None
    assert result["level"] == 0
    assert result["complexity_score"] > 0.0
    assert "decompose_hints" in result
    assert "needs_decomposition" in result

    # 验证数据库
    req = sync_session.get(Requirement, result["requirement_id"])
    assert req.project_id == project.id
    assert req.status == RequirementStatus.DRAFT.value


def test_add_requirement_with_parent(sync_session):
    """测试添加子需求"""
    # Arrange
    manager = RequirementManager()
    project = Project(name="测试项目")
    sync_session.add(project)
    sync_session.commit()

    parent_req = manager.add_requirement(
        sync_session,
        project.id,
        "父需求"
    )

    # Act
    result = manager.add_requirement(
        sync_session,
        project.id,
        "子需求",
        parent_id=parent_req["requirement_id"]
    )

    # Assert
    assert result["level"] == 1
    assert result["parent_id"] == parent_req["requirement_id"]

    # 验证父需求状态更新
    parent = sync_session.get(Requirement, parent_req["requirement_id"])
    assert parent.status == RequirementStatus.DECOMPOSING.value


def test_mark_as_leaf(sync_session):
    """测试标记叶子节点"""
    # Arrange
    manager = RequirementManager()
    project = Project(name="测试项目")
    sync_session.add(project)
    sync_session.commit()

    req = manager.add_requirement(sync_session, project.id, "叶子需求")

    # Act
    result = manager.mark_as_leaf(sync_session, req["requirement_id"])

    # Assert
    assert result["status"] == "LEAF"

    # 验证数据库
    leaf_req = sync_session.get(Requirement, req["requirement_id"])
    assert leaf_req.status == RequirementStatus.LEAF.value


def test_mark_as_leaf_with_children(sync_session):
    """测试标记有子需求的节点为叶子（应失败）"""
    # Arrange
    manager = RequirementManager()
    project = Project(name="测试项目")
    sync_session.add(project)
    sync_session.commit()

    parent_req = manager.add_requirement(sync_session, project.id, "父需求")
    manager.add_requirement(
        sync_session,
        project.id,
        "子需求",
        parent_id=parent_req["requirement_id"]
    )

    # Act & Assert
    with pytest.raises(ValueError, match="有.*个子需求"):
        manager.mark_as_leaf(sync_session, parent_req["requirement_id"])


def test_update_requirement(sync_session):
    """测试更新需求"""
    # Arrange
    manager = RequirementManager()
    project = Project(name="测试项目")
    sync_session.add(project)
    sync_session.commit()

    req = manager.add_requirement(sync_session, project.id, "原内容")

    from src.schemas import RequirementUpdate

    # Act
    result = manager.update_requirement(
        sync_session,
        req["requirement_id"],
        RequirementUpdate(content="新内容")
    )

    # Assert
    assert result["content"] == "新内容"


def test_delete_requirement(sync_session):
    """测试删除需求"""
    # Arrange
    manager = RequirementManager()
    project = Project(name="测试项目")
    sync_session.add(project)
    sync_session.commit()

    req = manager.add_requirement(sync_session, project.id, "要删除的需求")

    # Act
    result = manager.delete_requirement(sync_session, req["requirement_id"])

    # Assert
    assert result["deleted"] is True

    # 验证数据库
    deleted_req = sync_session.get(Requirement, req["requirement_id"])
    assert deleted_req is None


def test_get_requirement(sync_session):
    """测试获取需求信息"""
    # Arrange
    manager = RequirementManager()
    project = Project(name="测试项目")
    sync_session.add(project)
    sync_session.commit()

    req = manager.add_requirement(sync_session, project.id, "测试需求")

    # Act
    result = manager.get_requirement(sync_session, req["requirement_id"])

    # Assert
    assert result["requirement_id"] == req["requirement_id"]
    assert result["content"] == "测试需求"
    assert result["level"] == 0


def test_generate_decompose_hints(sync_session):
    """测试生成分解提示"""
    # Arrange
    manager = RequirementManager()

    # Test Case 1: 包含"模块"
    hints1 = manager._generate_decompose_hints("实现用户管理模块", level=0)
    assert any("功能模块" in hint for hint in hints1)

    # Test Case 2: 包含"系统"
    hints2 = manager._generate_decompose_hints("构建电商系统", level=0)
    assert any("子系统" in hint for hint in hints2)

    # Test Case 3: 根需求
    hints3 = manager._generate_decompose_hints("简单需求", level=0)
    assert any("3-7" in hint for hint in hints3)