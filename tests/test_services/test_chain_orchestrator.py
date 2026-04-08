# Copyright (c) 2026 Kirky.X. All rights reserved.
# Licensed under the MIT License.
# See LICENSE file in the project root for full license information.

"""链化编排器服务测试"""

import pytest

from src.db.graph_models import ProjectStatus


def test_should_trigger_chaining_no_project(graph_connection, chain_orchestrator):
    """测试项目不存在时的链化触发检查"""
    # Act & Assert
    with pytest.raises(ValueError, match="项目不存在"):
        chain_orchestrator.should_trigger_chaining(
            graph_connection, "nonexistent-project-id"
        )


def test_should_trigger_chaining_wrong_status(
    graph_connection, chain_orchestrator, project_manager
):
    """测试项目状态不正确时的链化触发检查"""
    # Arrange
    project = project_manager.create_project(graph_connection, "测试项目")
    project_id = project["project_id"]

    # Act
    result = chain_orchestrator.should_trigger_chaining(graph_connection, project_id)

    # Assert
    assert result is False


def test_should_trigger_chaining_no_requirements(
    graph_connection, chain_orchestrator, project_manager
):
    """测试无需求时的链化触发检查"""
    # Arrange
    project = project_manager.create_project(graph_connection, "测试项目")
    project_id = project["project_id"]

    # 更新项目状态为 DECOMPOSING
    project_manager.update_project_status(
        graph_connection, project_id, ProjectStatus.DECOMPOSING
    )

    # Act
    result = chain_orchestrator.should_trigger_chaining(graph_connection, project_id)

    # Assert
    assert result is False


def test_should_trigger_chaining_no_leaf_requirements(
    graph_connection,
    chain_orchestrator,
    project_manager,
    requirement_manager,
):
    """测试无叶子节点时的链化触发检查"""
    # Arrange
    project = project_manager.create_project(graph_connection, "测试项目")
    project_id = project["project_id"]

    # 创建父需求和子需求（没有叶子节点）
    parent = requirement_manager.add_requirement(graph_connection, project_id, "父需求")
    requirement_manager.add_requirement(
        graph_connection,
        project_id,
        "子需求",
        parent_uuid=parent["requirement_id"],
    )

    # 更新项目状态为 DECOMPOSING
    project_manager.update_project_status(
        graph_connection, project_id, ProjectStatus.DECOMPOSING
    )

    # Act
    result = chain_orchestrator.should_trigger_chaining(graph_connection, project_id)

    # Assert
    assert result is False


def test_should_trigger_chaining_with_validated_leaf(
    graph_connection,
    chain_orchestrator,
    project_manager,
    requirement_manager,
    validation_service,
):
    """测试有已验证叶子节点时的链化触发检查"""
    # Arrange
    project = project_manager.create_project(graph_connection, "测试项目")
    project_id = project["project_id"]

    # 创建叶子需求并添加验证
    req = requirement_manager.add_requirement(graph_connection, project_id, "叶子需求")
    validation_service.add_validation(
        graph_connection, req["requirement_id"], [{"name": "测试"}]
    )

    # 更新项目状态为 DECOMPOSING
    project_manager.update_project_status(
        graph_connection, project_id, ProjectStatus.DECOMPOSING
    )

    # Act
    result = chain_orchestrator.should_trigger_chaining(graph_connection, project_id)

    # Assert
    assert result is True


def test_trigger_chaining_not_ready(
    graph_connection, chain_orchestrator, project_manager
):
    """测试链化未就绪时的触发"""
    # Arrange
    project = project_manager.create_project(graph_connection, "测试项目")
    project_id = project["project_id"]

    # Act
    result = chain_orchestrator.trigger_chaining(
        graph_connection, project_id, "test-session-123456789"
    )

    # Assert
    assert result["status"] == "not_ready"
    assert "未准备好链化" in result["message"]


def test_trigger_chaining_success(
    graph_connection,
    chain_orchestrator,
    project_manager,
    requirement_manager,
    validation_service,
):
    """测试成功触发链化"""
    # Arrange
    project = project_manager.create_project(graph_connection, "测试项目")
    project_id = project["project_id"]

    # 创建叶子需求并添加验证
    req1 = requirement_manager.add_requirement(graph_connection, project_id, "需求1")
    req2 = requirement_manager.add_requirement(graph_connection, project_id, "需求2")

    validation_service.add_validation(
        graph_connection, req1["requirement_id"], [{"name": "测试1"}]
    )
    validation_service.add_validation(
        graph_connection, req2["requirement_id"], [{"name": "测试2"}]
    )

    # 更新项目状态
    project_manager.update_project_status(
        graph_connection, project_id, ProjectStatus.DECOMPOSING
    )

    # Act
    result = chain_orchestrator.trigger_chaining(
        graph_connection, project_id, "test-session-123456789"
    )

    # Assert
    assert result["status"] in ["completed", "partial"]

    # 验证项目状态已更新
    updated_project = project_manager.get_project(graph_connection, project_id)
    assert updated_project["status"] == ProjectStatus.READY.value


def test_resolve_parallel_order_success(
    graph_connection,
    chain_orchestrator,
    project_manager,
    requirement_manager,
    validation_service,
):
    """测试成功应用并行节点排序"""
    # Arrange
    project = project_manager.create_project(graph_connection, "测试项目")
    project_id = project["project_id"]

    # 创建叶子需求
    req1 = requirement_manager.add_requirement(graph_connection, project_id, "需求1")
    req2 = requirement_manager.add_requirement(graph_connection, project_id, "需求2")
    req3 = requirement_manager.add_requirement(graph_connection, project_id, "需求3")

    validation_service.add_validation(
        graph_connection, req1["requirement_id"], [{"name": "测试1"}]
    )
    validation_service.add_validation(
        graph_connection, req2["requirement_id"], [{"name": "测试2"}]
    )
    validation_service.add_validation(
        graph_connection, req3["requirement_id"], [{"name": "测试3"}]
    )

    # 更新项目状态
    project_manager.update_project_status(
        graph_connection, project_id, ProjectStatus.DECOMPOSING
    )

    # Act
    parallel_nodes = [
        req1["requirement_id"],
        req2["requirement_id"],
        req3["requirement_id"],
    ]
    sorted_order = [
        req1["requirement_id"],
        req2["requirement_id"],
        req3["requirement_id"],
    ]

    result = chain_orchestrator.resolve_parallel_order(
        graph_connection, project_id, parallel_nodes, sorted_order
    )

    # Assert
    assert result["status"] == "completed"

    # 验证项目状态已更新
    updated_project = project_manager.get_project(graph_connection, project_id)
    assert updated_project["status"] == ProjectStatus.READY.value


def test_resolve_parallel_order_invalid_order(
    graph_connection,
    chain_orchestrator,
    project_manager,
    requirement_manager,
):
    """测试无效的并行节点排序"""
    # Arrange
    project = project_manager.create_project(graph_connection, "测试项目")
    project_id = project["project_id"]

    req1 = requirement_manager.add_requirement(graph_connection, project_id, "需求1")
    req2 = requirement_manager.add_requirement(graph_connection, project_id, "需求2")
    req3 = requirement_manager.add_requirement(graph_connection, project_id, "需求3")

    # Act & Assert: 排序后的节点与并行节点不一致
    with pytest.raises(ValueError, match="必须与并行节点一致"):
        chain_orchestrator.resolve_parallel_order(
            graph_connection,
            project_id,
            [
                req1["requirement_id"],
                req2["requirement_id"],
                req3["requirement_id"],
            ],
            [req1["requirement_id"], req2["requirement_id"]],  # 缺少 req3
        )


def test_get_next_requirement_not_chained(
    graph_connection, chain_orchestrator, project_manager
):
    """测试获取下一个需求（未链化）"""
    # Arrange
    project = project_manager.create_project(graph_connection, "测试项目")
    project_id = project["project_id"]

    # Act & Assert
    with pytest.raises(ValueError, match="未准备好链化"):
        chain_orchestrator.get_next_requirement(
            graph_connection, project_id, "test-session-123456789"
        )


def test_get_next_requirement_success(
    graph_connection,
    chain_orchestrator,
    project_manager,
    requirement_manager,
    validation_service,
):
    """测试成功获取下一个需求"""
    # Arrange
    project = project_manager.create_project(graph_connection, "测试项目")
    project_id = project["project_id"]

    # 创建叶子需求并添加验证
    req1 = requirement_manager.add_requirement(graph_connection, project_id, "需求1")
    req2 = requirement_manager.add_requirement(graph_connection, project_id, "需求2")

    validation_service.add_validation(
        graph_connection, req1["requirement_id"], [{"name": "测试1"}]
    )
    validation_service.add_validation(
        graph_connection, req2["requirement_id"], [{"name": "测试2"}]
    )

    # 更新项目状态
    project_manager.update_project_status(
        graph_connection, project_id, ProjectStatus.DECOMPOSING
    )

    # 触发链化
    chain_orchestrator.trigger_chaining(
        graph_connection, project_id, "test-session-123456789"
    )

    # Act
    result = chain_orchestrator.get_next_requirement(
        graph_connection, project_id, "test-session-123456789"
    )

    # Assert
    assert result["requirement_id"] is not None
    assert result["content"] is not None
    assert result["chain_order"] is not None
    assert "progress_percentage" in result


def test_get_next_requirement_all_completed(
    graph_connection,
    chain_orchestrator,
    project_manager,
    requirement_manager,
    validation_service,
):
    """测试所有需求已完成时的获取"""
    # Arrange
    project = project_manager.create_project(graph_connection, "测试项目")
    project_id = project["project_id"]

    # 创建叶子需求并添加验证
    req1 = requirement_manager.add_requirement(graph_connection, project_id, "需求1")
    validation_service.add_validation(
        graph_connection, req1["requirement_id"], [{"name": "测试1"}]
    )

    # 更新项目状态
    project_manager.update_project_status(
        graph_connection, project_id, ProjectStatus.DECOMPOSING
    )

    # 触发链化
    chain_orchestrator.trigger_chaining(
        graph_connection, project_id, "test-session-123456789"
    )

    # 标记需求为已完成
    chain_orchestrator.mark_requirement_completed(
        graph_connection, project_id, req1["requirement_id"]
    )

    # Act
    result = chain_orchestrator.get_next_requirement(
        graph_connection, project_id, "test-session-123456789"
    )

    # Assert
    assert result["requirement_id"] is None
    assert result["is_last"] is True
    assert result["progress_percentage"] == 100
    assert "所有需求已完成" in result["message"]


def test_mark_requirement_completed_nonexistent(
    graph_connection, chain_orchestrator, project_manager
):
    """测试标记不存在的需求为已完成"""
    # Arrange
    project = project_manager.create_project(graph_connection, "测试项目")
    project_id = project["project_id"]

    # Act & Assert
    with pytest.raises(ValueError, match="需求不存在"):
        chain_orchestrator.mark_requirement_completed(
            graph_connection, project_id, "nonexistent-req-id"
        )
