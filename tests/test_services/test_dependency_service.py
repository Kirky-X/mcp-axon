# Copyright (c) 2026 Kirky.X. All rights reserved.
# Licensed under the MIT License.
# See LICENSE file in the project root for full license information.

"""依赖关系管理服务测试"""

import pytest
from sqlalchemy.orm.attributes import flag_modified
from src.db.models import Project, Requirement
from src.services.dependency_service import DependencyService


def test_tc009_dependency_single_child_inheritance(sync_session):
    """TC-009: 测试单子需求依赖继承"""

    # Arrange
    service = DependencyService()
    project = Project(name="测试项目")
    sync_session.add(project)
    sync_session.commit()

    # 创建依赖需求
    dep1 = Requirement(project_id=project.id, content="依赖1")
    sync_session.add(dep1)
    sync_session.commit()

    # 创建父需求（依赖 dep1）
    parent = Requirement(
        project_id=project.id,
        content="父需求",
        dependencies=[dep1.id]
    )
    sync_session.add(parent)
    sync_session.flush()
    flag_modified(parent, 'dependencies')
    sync_session.commit()

    # 创建子需求
    child = Requirement(
        project_id=project.id,
        parent_id=parent.id,
        content="子需求"
    )
    sync_session.add(child)
    sync_session.commit()

    # Act: 传递依赖（单子需求自动继承）
    result = service.transfer_dependencies(
        sync_session,
        parent_id=parent.id,
        dependency_mapping={}
    )

    # Assert
    sync_session.refresh(child)
    assert dep1.id in child.dependencies
    assert result["total_children"] == 1


def test_transfer_dependencies_with_mapping(sync_session):
    """测试使用映射传递依赖"""
    # Arrange
    service = DependencyService()
    project = Project(name="测试项目")
    sync_session.add(project)
    sync_session.commit()

    # 创建依赖需求
    dep1 = Requirement(project_id=project.id, content="依赖1")
    dep2 = Requirement(project_id=project.id, content="依赖2")
    sync_session.add_all([dep1, dep2])
    sync_session.commit()

    # 创建父需求
    parent = Requirement(
        project_id=project.id,
        content="父需求",
        dependencies=[dep1.id, dep2.id]
    )
    sync_session.add(parent)
    sync_session.flush()
    flag_modified(parent, 'dependencies')
    sync_session.commit()

    # 创建多个子需求
    child1 = Requirement(project_id=project.id, parent_id=parent.id, content="子需求1")
    child2 = Requirement(project_id=project.id, parent_id=parent.id, content="子需求2")
    sync_session.add_all([child1, child2])
    sync_session.commit()

    # Act: 使用映射指定依赖
    result = service.transfer_dependencies(
        sync_session,
        parent_id=parent.id,
        dependency_mapping={
            child1.id: [dep1.id],
            child2.id: [dep2.id]
        }
    )

    # Assert
    sync_session.refresh(child1)
    sync_session.refresh(child2)
    assert child1.dependencies == [dep1.id]
    assert child2.dependencies == [dep2.id]


def test_add_dependency(sync_session):
    """测试添加依赖关系"""
    # Arrange
    service = DependencyService()
    project = Project(name="测试项目")
    sync_session.add(project)
    sync_session.commit()

    req1 = Requirement(project_id=project.id, content="需求1")
    req2 = Requirement(project_id=project.id, content="需求2")
    sync_session.add_all([req1, req2])
    sync_session.commit()

    # Act
    result = service.add_dependency(
        sync_session,
        requirement_id=req2.id,
        dependency_id=req1.id
    )

    # Assert
    assert req1.id in result["dependencies"]


def test_add_dependency_self_reference(sync_session):
    """测试添加自依赖（应失败）"""
    # Arrange
    service = DependencyService()
    project = Project(name="测试项目")
    sync_session.add(project)
    sync_session.commit()

    req = Requirement(project_id=project.id, content="需求")
    sync_session.add(req)
    sync_session.commit()

    # Act & Assert
    with pytest.raises(ValueError, match="不能添加自依赖"):
        service.add_dependency(sync_session, req.id, req.id)


def test_add_dependency_cycle_detection(sync_session):
    """测试添加依赖时的循环依赖检测"""
    # Arrange
    service = DependencyService()
    project = Project(name="测试项目")
    sync_session.add(project)
    sync_session.commit()

    req1 = Requirement(project_id=project.id, content="需求1")
    sync_session.add(req1)
    sync_session.flush()

    req2 = Requirement(project_id=project.id, content="需求2", dependencies=[req1.id])
    sync_session.add(req2)
    sync_session.flush()
    flag_modified(req2, 'dependencies')

    req3 = Requirement(project_id=project.id, content="需求3", dependencies=[req2.id])
    sync_session.add(req3)
    sync_session.flush()
    flag_modified(req3, 'dependencies')
    sync_session.commit()

    # Act & Assert: 尝试创建循环 req1 -> req3
    with pytest.raises(ValueError, match="循环依赖"):
        service.add_dependency(sync_session, req1.id, req3.id)


def test_remove_dependency(sync_session):
    """测试移除依赖关系"""
    # Arrange
    service = DependencyService()
    project = Project(name="测试项目")
    sync_session.add(project)
    sync_session.commit()

    req1 = Requirement(project_id=project.id, content="需求1")
    sync_session.add(req1)
    sync_session.flush()

    req2 = Requirement(project_id=project.id, content="需求2", dependencies=[req1.id])
    sync_session.add(req2)
    sync_session.flush()
    flag_modified(req2, 'dependencies')
    sync_session.commit()

    # Act
    result = service.remove_dependency(
        sync_session,
        requirement_id=req2.id,
        dependency_id=req1.id
    )

    # Assert
    assert req1.id not in result["dependencies"]


def test_detect_cycle_no_cycle(sync_session):
    """测试检测循环依赖（无循环）"""
    # Arrange
    service = DependencyService()
    project = Project(name="测试项目")
    sync_session.add(project)
    sync_session.commit()

    req1 = Requirement(project_id=project.id, content="需求1")
    sync_session.add(req1)
    sync_session.flush()

    req2 = Requirement(project_id=project.id, content="需求2", dependencies=[req1.id])
    sync_session.add(req2)
    sync_session.flush()
    flag_modified(req2, 'dependencies')

    req3 = Requirement(project_id=project.id, content="需求3", dependencies=[req2.id])
    sync_session.add(req3)
    sync_session.flush()
    flag_modified(req3, 'dependencies')
    sync_session.commit()

    # Act
    cycle = service.detect_cycle(sync_session, project.id)

    # Assert
    assert cycle is None


def test_detect_cycle_with_cycle(sync_session):
    """测试检测循环依赖（有循环）"""
    # Arrange
    service = DependencyService()
    project = Project(name="测试项目")
    sync_session.add(project)
    sync_session.commit()

    req1 = Requirement(project_id=project.id, content="需求1")
    sync_session.add(req1)
    sync_session.flush()

    req2 = Requirement(project_id=project.id, content="需求2", dependencies=[req1.id])
    sync_session.add(req2)
    sync_session.flush()
    flag_modified(req2, 'dependencies')

    req3 = Requirement(project_id=project.id, content="需求3", dependencies=[req2.id])
    sync_session.add(req3)
    sync_session.flush()
    flag_modified(req3, 'dependencies')

    # 创建循环: req1 -> req3
    req1.dependencies = [req3.id]
    flag_modified(req1, 'dependencies')
    sync_session.commit()

    # Act
    cycle = service.detect_cycle(sync_session, project.id)

    # Assert
    assert cycle is not None
    assert len(cycle) > 0


def test_transfer_dependencies_nonexistent_parent(sync_session):
    """测试传递依赖时父需求不存在"""
    # Arrange
    service = DependencyService()

    # Act & Assert
    with pytest.raises(ValueError, match="父需求不存在"):
        service.transfer_dependencies(
            sync_session,
            parent_id="nonexistent-id",
            dependency_mapping={}
        )