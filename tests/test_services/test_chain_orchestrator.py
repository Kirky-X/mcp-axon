# Copyright (c) 2026 Kirky.X. All rights reserved.
# Licensed under the MIT License.
# See LICENSE file in the project root for full license information.

"""链化编排器服务测试"""

import pytest
from sqlalchemy.orm.attributes import flag_modified

from src.db.models import (
    Project,
    ProjectStatus,
    Requirement,
    RequirementStatus,
    ValidationNode,
)
from src.services.chain_orchestrator import ChainOrchestrator


def test_should_trigger_chaining_no_project(sync_session):
    """测试项目不存在时的链化触发检查"""
    # Arrange
    orchestrator = ChainOrchestrator()

    # Act & Assert
    with pytest.raises(ValueError, match="项目不存在"):
        orchestrator.should_trigger_chaining(sync_session, "nonexistent-project-id")


def test_should_trigger_chaining_wrong_status(sync_session):
    """测试项目状态不正确时的链化触发检查"""
    # Arrange
    orchestrator = ChainOrchestrator()
    project = Project(name="测试项目", status=ProjectStatus.CREATED.value)
    sync_session.add(project)
    sync_session.commit()

    # Act
    result = orchestrator.should_trigger_chaining(sync_session, project.id)

    # Assert
    assert result is False


def test_should_trigger_chaining_no_requirements(sync_session):
    """测试无需求时的链化触发检查"""
    # Arrange
    orchestrator = ChainOrchestrator()
    project = Project(name="测试项目", status=ProjectStatus.DECOMPOSING.value)
    sync_session.add(project)
    sync_session.commit()

    # Act
    result = orchestrator.should_trigger_chaining(sync_session, project.id)

    # Assert
    assert result is False


def test_should_trigger_chaining_no_leaf_requirements(sync_session):
    """测试无叶子节点时的链化触发检查"""
    # Arrange
    orchestrator = ChainOrchestrator()
    project = Project(name="测试项目", status=ProjectStatus.DECOMPOSING.value)
    sync_session.add(project)
    sync_session.commit()

    # 创建父需求和子需求（没有叶子节点）
    parent = Requirement(project_id=project.id, content="父需求")
    sync_session.add(parent)
    sync_session.flush()

    child = Requirement(project_id=project.id, parent_id=parent.id, content="子需求")
    sync_session.add(child)
    sync_session.commit()

    # Act
    result = orchestrator.should_trigger_chaining(sync_session, project.id)

    # Assert
    assert result is False


def test_should_trigger_chaining_with_validated_leaf(sync_session):
    """测试有已验证叶子节点时的链化触发检查"""
    # Arrange
    orchestrator = ChainOrchestrator()
    project = Project(name="测试项目", status=ProjectStatus.DECOMPOSING.value)
    sync_session.add(project)
    sync_session.commit()

    # 创建叶子需求并添加验证
    req = Requirement(project_id=project.id, content="叶子需求")
    sync_session.add(req)
    sync_session.flush()

    validation = ValidationNode(requirement_id=req.id)
    sync_session.add(validation)
    sync_session.commit()

    # Act
    result = orchestrator.should_trigger_chaining(sync_session, project.id)

    # Assert
    assert result is True


def test_trigger_chaining_not_ready(sync_session):
    """测试链化未就绪时的触发"""
    # Arrange
    orchestrator = ChainOrchestrator()
    project = Project(name="测试项目", status=ProjectStatus.CREATED.value)
    sync_session.add(project)
    sync_session.commit()

    # Act
    result = orchestrator.trigger_chaining(
        sync_session, project.id, "test-session-123456789"
    )

    # Assert
    assert result["status"] == "not_ready"
    assert "未准备好链化" in result["message"]


def test_trigger_chaining_success(sync_session):
    """测试成功触发链化"""
    # Arrange
    orchestrator = ChainOrchestrator()
    project = Project(name="测试项目", status=ProjectStatus.DECOMPOSING.value)
    sync_session.add(project)
    sync_session.commit()

    # 创建叶子需求并添加验证
    req1 = Requirement(
        project_id=project.id, content="需求1", status=RequirementStatus.VALIDATED.value
    )
    req2 = Requirement(
        project_id=project.id, content="需求2", status=RequirementStatus.VALIDATED.value
    )
    sync_session.add_all([req1, req2])
    sync_session.flush()

    # 为需求添加验证节点（通过直接设置状态）
    req1.status = RequirementStatus.VALIDATED.value
    req2.status = RequirementStatus.VALIDATED.value

    # 创建验证节点
    validation1 = ValidationNode(requirement_id=req1.id)
    validation2 = ValidationNode(requirement_id=req2.id)
    sync_session.add_all([validation1, validation2])
    sync_session.commit()

    # Act
    result = orchestrator.trigger_chaining(
        sync_session, project.id, "test-session-123456789"
    )

    # Assert
    assert result["status"] in ["completed", "partial"]

    # 验证项目状态已更新
    sync_session.refresh(project)
    assert project.status == ProjectStatus.READY.value


def test_resolve_parallel_order_success(sync_session):
    """测试成功应用并行节点排序"""
    # Arrange
    orchestrator = ChainOrchestrator()
    project = Project(name="测试项目", status=ProjectStatus.DECOMPOSING.value)
    sync_session.add(project)
    sync_session.commit()

    # 创建叶子需求
    req1 = Requirement(
        project_id=project.id, content="需求1", status=RequirementStatus.VALIDATED.value
    )
    req2 = Requirement(
        project_id=project.id, content="需求2", status=RequirementStatus.VALIDATED.value
    )
    req3 = Requirement(
        project_id=project.id, content="需求3", status=RequirementStatus.VALIDATED.value
    )
    sync_session.add_all([req1, req2, req3])
    sync_session.flush()

    # 创建验证节点
    validation1 = ValidationNode(requirement_id=req1.id)
    validation2 = ValidationNode(requirement_id=req2.id)
    validation3 = ValidationNode(requirement_id=req3.id)
    sync_session.add_all([validation1, validation2, validation3])
    sync_session.commit()

    # Act
    parallel_nodes = [req1.id, req2.id, req3.id]
    sorted_order = [req1.id, req2.id, req3.id]

    result = orchestrator.resolve_parallel_order(
        sync_session, project.id, parallel_nodes, sorted_order
    )

    # Assert
    assert result["status"] == "completed"

    # 验证项目状态已更新
    sync_session.refresh(project)
    assert project.status == ProjectStatus.READY.value


def test_resolve_parallel_order_invalid_order(sync_session):
    """测试无效的并行节点排序"""
    # Arrange
    orchestrator = ChainOrchestrator()
    project = Project(name="测试项目", status=ProjectStatus.DECOMPOSING.value)
    sync_session.add(project)
    sync_session.commit()

    # 创建需求
    req1 = Requirement(project_id=project.id, content="需求1")
    req2 = Requirement(project_id=project.id, content="需求2")
    req3 = Requirement(project_id=project.id, content="需求3")
    sync_session.add_all([req1, req2, req3])
    sync_session.commit()

    # Act & Assert: 排序后的节点与并行节点不一致
    with pytest.raises(ValueError, match="必须与并行节点一致"):
        orchestrator.resolve_parallel_order(
            sync_session,
            project.id,
            [req1.id, req2.id, req3.id],
            [req1.id, req2.id],  # 缺少 req3
        )


def test_get_next_requirement_not_chained(sync_session):
    """测试获取下一个需求（未链化）"""
    # Arrange
    orchestrator = ChainOrchestrator()
    project = Project(name="测试项目", status=ProjectStatus.DECOMPOSING.value)
    sync_session.add(project)
    sync_session.commit()

    # Act & Assert
    with pytest.raises(ValueError, match="未准备好链化"):
        orchestrator.get_next_requirement(
            sync_session, project.id, "test-session-123456789"
        )


def test_get_next_requirement_success(sync_session):
    """测试成功获取下一个需求"""
    # Arrange
    orchestrator = ChainOrchestrator()
    project = Project(name="测试项目", status=ProjectStatus.DECOMPOSING.value)
    sync_session.add(project)
    sync_session.commit()

    # 创建叶子需求并添加验证
    req1 = Requirement(
        project_id=project.id, content="需求1", status=RequirementStatus.VALIDATED.value
    )
    req2 = Requirement(
        project_id=project.id, content="需求2", status=RequirementStatus.VALIDATED.value
    )
    sync_session.add_all([req1, req2])
    sync_session.flush()

    validation1 = ValidationNode(requirement_id=req1.id)
    validation2 = ValidationNode(requirement_id=req2.id)
    sync_session.add_all([validation1, validation2])
    sync_session.commit()

    # 触发链化
    orchestrator.trigger_chaining(sync_session, project.id, "test-session-123456789")

    # Act
    result = orchestrator.get_next_requirement(
        sync_session, project.id, "test-session-123456789"
    )

    # Assert
    assert result["requirement_id"] is not None
    assert result["content"] is not None
    assert result["chain_order"] is not None
    assert "progress_percentage" in result


def test_get_next_requirement_all_completed(sync_session):
    """测试所有需求已完成时的获取"""
    # Arrange
    orchestrator = ChainOrchestrator()
    project = Project(name="测试项目", status=ProjectStatus.DECOMPOSING.value)
    sync_session.add(project)
    sync_session.commit()

    # 创建叶子需求并添加验证
    req1 = Requirement(
        project_id=project.id, content="需求1", status=RequirementStatus.VALIDATED.value
    )
    sync_session.add(req1)
    sync_session.flush()

    validation1 = ValidationNode(requirement_id=req1.id)
    sync_session.add(validation1)
    sync_session.commit()

    # 触发链化
    orchestrator.trigger_chaining(sync_session, project.id, "test-session-123456789")

    # 标记需求为已完成
    orchestrator.mark_requirement_completed(sync_session, project.id, req1.id)

    # Act
    result = orchestrator.get_next_requirement(
        sync_session, project.id, "test-session-123456789"
    )

    # Assert
    assert result["requirement_id"] is None
    assert result["is_last"] is True
    assert result["progress_percentage"] == 100
    assert "所有需求已完成" in result["message"]


def test_mark_requirement_completed_success(sync_session):
    """测试成功标记需求为已完成"""
    # Arrange
    orchestrator = ChainOrchestrator()
    project = Project(name="测试项目", status=ProjectStatus.DECOMPOSING.value)
    sync_session.add(project)
    sync_session.commit()

    # 创建叶子需求并添加验证
    req1 = Requirement(
        project_id=project.id, content="需求1", status=RequirementStatus.VALIDATED.value
    )
    req2 = Requirement(
        project_id=project.id, content="需求2", status=RequirementStatus.VALIDATED.value
    )
    sync_session.add_all([req1, req2])
    sync_session.flush()

    # 设置链表关系
    req1.next_requirement_id = req2.id
    req1.chain_order = 1
    req2.chain_order = 2
    sync_session.flush()
    flag_modified(req1, "next_requirement_id")
    flag_modified(req1, "chain_order")
    flag_modified(req2, "chain_order")
    sync_session.commit()

    # 创建验证节点
    validation1 = ValidationNode(requirement_id=req1.id)
    validation2 = ValidationNode(requirement_id=req2.id)
    sync_session.add_all([validation1, validation2])
    sync_session.commit()

    # 触发链化
    orchestrator.trigger_chaining(sync_session, project.id, "test-session-123456789")

    # Act
    result = orchestrator.mark_requirement_completed(sync_session, project.id, req1.id)

    # Assert
    assert result["requirement_id"] == req1.id
    assert result["next_requirement_id"] == req2.id
    assert result["completed_nodes"] == 1
    assert result["total_nodes"] == 2
    assert "message" in result


def test_mark_requirement_completed_last_node(sync_session):
    """测试标记最后一个需求为已完成"""
    # Arrange
    orchestrator = ChainOrchestrator()
    project = Project(name="测试项目", status=ProjectStatus.DECOMPOSING.value)
    sync_session.add(project)
    sync_session.commit()

    # 创建叶子需求并添加验证
    req1 = Requirement(
        project_id=project.id, content="需求1", status=RequirementStatus.VALIDATED.value
    )
    sync_session.add(req1)
    sync_session.flush()

    # 设置链表关系
    req1.chain_order = 1
    sync_session.flush()
    flag_modified(req1, "chain_order")
    sync_session.commit()

    # 创建验证节点
    validation1 = ValidationNode(requirement_id=req1.id)
    sync_session.add(validation1)
    sync_session.commit()

    # 触发链化
    orchestrator.trigger_chaining(sync_session, project.id, "test-session-123456789")

    # Act
    result = orchestrator.mark_requirement_completed(sync_session, project.id, req1.id)

    # Assert
    assert result["requirement_id"] == req1.id
    assert result["next_requirement_id"] is None
    assert result["completed_nodes"] == 1
    assert result["total_nodes"] == 1
    assert result["progress_percentage"] == 100
    assert "项目已完成" in result["message"]

    # 验证项目状态已更新为 COMPLETED
    sync_session.refresh(project)
    assert project.status == ProjectStatus.COMPLETED.value


def test_mark_requirement_completed_nonexistent(sync_session):
    """测试标记不存在的需求为已完成"""
    # Arrange
    orchestrator = ChainOrchestrator()
    project = Project(name="测试项目")
    sync_session.add(project)
    sync_session.commit()

    # Act & Assert
    with pytest.raises(ValueError, match="需求不存在"):
        orchestrator.mark_requirement_completed(
            sync_session, project.id, "nonexistent-req-id"
        )


def test_tc015_linked_list_construction(sync_session):
    """TC-015: 测试链表构建"""
    # Arrange
    from src.db.models import ChainState, ChainStatus
    from src.services.chain_builder import ChainBuilder

    builder = ChainBuilder()

    # 创建项目
    project = Project(name="测试项目")
    sync_session.add(project)
    sync_session.commit()

    # 创建需求
    req1 = Requirement(project_id=project.id, content="需求1")
    req2 = Requirement(project_id=project.id, content="需求2")
    req3 = Requirement(project_id=project.id, content="需求3")
    sync_session.add_all([req1, req2, req3])
    sync_session.commit()

    # 创建链状态
    chain_state = ChainState(project_id=project.id)
    sync_session.add(chain_state)
    sync_session.commit()

    # 创建需求映射
    req_map = {req1.id: req1, req2.id: req2, req3.id: req3}

    # Act: 构建链表
    ordered_ids = [req1.id, req2.id, req3.id]
    result = builder._link_requirements(sync_session, project.id, ordered_ids, req_map)

    # Assert
    assert result["status"] == "completed"
    assert result["chain_head"] == req1.id
    assert result["total_nodes"] == 3

    # 验证链表指针
    sync_session.refresh(req1)
    sync_session.refresh(req2)
    sync_session.refresh(req3)

    assert req1.chain_order == 1
    assert req1.next_requirement_id == req2.id

    assert req2.chain_order == 2
    assert req2.next_requirement_id == req3.id

    assert req3.chain_order == 3
    assert req3.next_requirement_id is None

    # 验证链状态已更新
    sync_session.refresh(chain_state)
    assert chain_state.status == ChainStatus.COMPLETED.value
    assert chain_state.chain_head_id == req1.id
    assert chain_state.total_nodes == 3
