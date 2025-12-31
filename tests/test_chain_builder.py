# Copyright (c) 2026 Kirky.X. All rights reserved.
# Licensed under the MIT License.
# See LICENSE file in the project root for full license information.

"""链化构建器测试"""

import pytest
from src.db.models import Project, Requirement, RequirementStatus, ChainState, ChainStatus
from src.services.chain_builder import ChainBuilder


def test_tc015_build_linked_list(sync_session):
    """TC-015: 测试链表构建"""

    # Arrange
    builder = ChainBuilder()
    project = Project(name="测试项目")
    sync_session.add(project)
    sync_session.commit()

    # 创建需求
    req1 = Requirement(
        project_id=project.id,
        content="需求1",
        status=RequirementStatus.VALIDATED.value
    )
    req2 = Requirement(
        project_id=project.id,
        content="需求2",
        status=RequirementStatus.VALIDATED.value
    )
    req3 = Requirement(
        project_id=project.id,
        content="需求3",
        status=RequirementStatus.VALIDATED.value
    )
    sync_session.add_all([req1, req2, req3])
    sync_session.commit()

    ordered_ids = [req1.id, req2.id, req3.id]

    # Act
    result = builder.build_chain_with_order(
        sync_session,
        project.id,
        ordered_ids
    )

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
    assert req1.status == RequirementStatus.CHAINED.value

    assert req2.chain_order == 2
    assert req2.next_requirement_id == req3.id
    assert req2.status == RequirementStatus.CHAINED.value

    assert req3.chain_order == 3
    assert req3.next_requirement_id is None
    assert req3.status == RequirementStatus.CHAINED.value


def test_build_chain_no_requirements(sync_session):
    """测试构建空链"""
    # Arrange
    builder = ChainBuilder()
    project = Project(name="测试项目")
    sync_session.add(project)
    sync_session.commit()

    # Act
    result = builder.build_chain(sync_session, project.id)

    # Assert
    assert result["status"] == "no_requirements"
    assert "没有已验证的需求" in result["message"]


def test_build_chain_with_dependencies(sync_session):
    """测试构建有依赖关系的链"""
    # Arrange
    builder = ChainBuilder()
    project = Project(name="测试项目")
    sync_session.add(project)
    sync_session.commit()

    # 创建需求（req2 依赖 req1, req3 依赖 req2）
    req1 = Requirement(
        project_id=project.id,
        content="需求1",
        status=RequirementStatus.VALIDATED.value,
        dependencies=[]
    )
    req2 = Requirement(
        project_id=project.id,
        content="需求2",
        status=RequirementStatus.VALIDATED.value,
        dependencies=[]
    )
    req3 = Requirement(
        project_id=project.id,
        content="需求3",
        status=RequirementStatus.VALIDATED.value,
        dependencies=[]
    )
    sync_session.add_all([req1, req2, req3])
    sync_session.flush()  # Flush to get IDs

    # Now set dependencies
    req2.dependencies = [req1.id]
    req3.dependencies = [req2.id]
    sync_session.commit()

    # Act
    result = builder.build_chain(sync_session, project.id)

    # Assert
    assert result["status"] == "completed"
    assert result["total_nodes"] == 3

    # 验证顺序应该是 req1 -> req2 -> req3
    sync_session.refresh(req1)
    sync_session.refresh(req2)
    sync_session.refresh(req3)

    assert req1.chain_order == 1
    assert req1.next_requirement_id == req2.id

    assert req2.chain_order == 2
    assert req2.next_requirement_id == req3.id

    assert req3.chain_order == 3


def test_build_chain_with_parallel_nodes(sync_session):
    """测试构建有并行节点的链"""
    # Arrange
    builder = ChainBuilder()
    project = Project(name="测试项目")
    sync_session.add(project)
    sync_session.commit()

    # 创建需求（req2 和 req3 都依赖 req1，是并行节点）
    req1 = Requirement(
        project_id=project.id,
        content="需求1",
        status=RequirementStatus.VALIDATED.value,
        dependencies=[]
    )
    req2 = Requirement(
        project_id=project.id,
        content="需求2",
        status=RequirementStatus.VALIDATED.value,
        dependencies=[]
    )
    req3 = Requirement(
        project_id=project.id,
        content="需求3",
        status=RequirementStatus.VALIDATED.value,
        dependencies=[]
    )
    sync_session.add_all([req1, req2, req3])
    sync_session.flush()  # Flush to get IDs

    # Now set dependencies
    req2.dependencies = [req1.id]
    req3.dependencies = [req1.id]
    sync_session.commit()

    # Act
    result = builder.build_chain(sync_session, project.id)

    # Assert
    assert result["status"] == "completed"
    assert result["total_nodes"] == 3

    # 验证 req1 是头节点
    sync_session.refresh(req1)
    assert req1.chain_order == 1


def test_build_chain_cycle_detection(sync_session):
    """测试构建链时的循环依赖检测"""
    # Arrange
    builder = ChainBuilder()
    project = Project(name="测试项目")
    sync_session.add(project)
    sync_session.commit()

    # 创建循环依赖
    req1 = Requirement(
        project_id=project.id,
        content="需求1",
        status=RequirementStatus.VALIDATED.value,
        dependencies=[]
    )
    req2 = Requirement(
        project_id=project.id,
        content="需求2",
        status=RequirementStatus.VALIDATED.value,
        dependencies=[]
    )
    req3 = Requirement(
        project_id=project.id,
        content="需求3",
        status=RequirementStatus.VALIDATED.value,
        dependencies=[]
    )
    sync_session.add_all([req1, req2, req3])
    sync_session.flush()  # Flush to get IDs

    # 创建循环: req1 -> req3
    req1.dependencies = [req3.id]
    req2.dependencies = [req1.id]
    req3.dependencies = [req2.id]
    sync_session.commit()

    # Act & Assert
    with pytest.raises(ValueError, match="循环依赖"):
        builder.build_chain(sync_session, project.id)


def test_build_chain_with_invalid_order(sync_session):
    """测试使用无效的顺序构建链"""
    # Arrange
    builder = ChainBuilder()
    project = Project(name="测试项目")
    sync_session.add(project)
    sync_session.commit()

    req1 = Requirement(
        project_id=project.id,
        content="需求1",
        status=RequirementStatus.VALIDATED.value
    )
    req2 = Requirement(
        project_id=project.id,
        content="需求2",
        status=RequirementStatus.VALIDATED.value
    )
    sync_session.add_all([req1, req2])
    sync_session.commit()

    # Act & Assert: 顺序中缺少 req2
    with pytest.raises(ValueError, match="排序顺序不匹配"):
        builder.build_chain_with_order(
            sync_session,
            project.id,
            [req1.id]  # 缺少 req2
        )


def test_reset_chain(sync_session):
    """测试重置链化状态"""
    # Arrange
    builder = ChainBuilder()
    project = Project(name="测试项目")
    sync_session.add(project)
    sync_session.commit()

    # 构建链
    req1 = Requirement(
        project_id=project.id,
        content="需求1",
        status=RequirementStatus.VALIDATED.value
    )
    req2 = Requirement(
        project_id=project.id,
        content="需求2",
        status=RequirementStatus.VALIDATED.value
    )
    sync_session.add_all([req1, req2])
    sync_session.commit()

    builder.build_chain(sync_session, project.id)

    # Act
    result = builder.reset_chain(sync_session, project.id)

    # Assert
    assert result["status"] == "reset"
    assert result["reset_count"] == 2

    # 验证需求状态已重置
    sync_session.refresh(req1)
    sync_session.refresh(req2)

    assert req1.status == RequirementStatus.VALIDATED.value
    assert req1.chain_order is None
    assert req1.next_requirement_id is None

    assert req2.status == RequirementStatus.VALIDATED.value
    assert req2.chain_order is None
    assert req2.next_requirement_id is None

    # 验证链化状态已重置
    chain_state = sync_session.query(ChainState).filter_by(
        project_id=project.id
    ).first()
    assert chain_state.status == ChainStatus.IDLE.value
    assert chain_state.chain_head_id is None


def test_build_chain_updates_chain_state(sync_session):
    """测试构建链时更新链化状态"""
    # Arrange
    builder = ChainBuilder()
    project = Project(name="测试项目")
    sync_session.add(project)
    sync_session.commit()

    req1 = Requirement(
        project_id=project.id,
        content="需求1",
        status=RequirementStatus.VALIDATED.value
    )
    sync_session.add(req1)
    sync_session.commit()

    # Act
    builder.build_chain(sync_session, project.id)

    # Assert
    chain_state = sync_session.query(ChainState).filter_by(
        project_id=project.id
    ).first()

    assert chain_state is not None
    assert chain_state.status == ChainStatus.COMPLETED.value
    assert chain_state.chain_head_id == req1.id
    assert chain_state.current_node_id == req1.id
    assert chain_state.total_nodes == 1
    assert chain_state.completed_nodes == 0
    assert chain_state.progress_percentage == 0
    assert chain_state.last_chained_at is not None