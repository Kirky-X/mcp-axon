# Copyright (c) 2026 Kirky.X. All rights reserved.
# Licensed under the MIT License.
# See LICENSE file in the project root for full license information.

"""链化构建器测试"""

import pytest

from src.db.graph_models import ChainStatus, RequirementStatus
from src.db.graph_queries import CREATE_DEPENDS_ON, GET_CHAIN_STATE_BY_PROJECT


def test_tc015_build_linked_list(
    graph_connection,
    project_manager,
    requirement_manager,
    validation_service,
    chain_builder,
):
    """TC-015: 测试链表构建"""

    # Arrange
    project = project_manager.create_project(graph_connection, "测试项目")
    project_id = project["project_id"]

    # 创建需求
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

    ordered_ids = [
        req1["requirement_id"],
        req2["requirement_id"],
        req3["requirement_id"],
    ]

    # Act
    result = chain_builder.build_chain_with_order(
        graph_connection, project_id, ordered_ids
    )

    # Assert
    assert result["status"] == "completed"
    assert result["chain_head"] == req1["requirement_id"]
    assert result["total_nodes"] == 3

    # 验证链表指针
    updated_req1 = requirement_manager.get_requirement(
        graph_connection, req1["requirement_id"]
    )
    updated_req2 = requirement_manager.get_requirement(
        graph_connection, req2["requirement_id"]
    )
    updated_req3 = requirement_manager.get_requirement(
        graph_connection, req3["requirement_id"]
    )

    assert updated_req1["chain_order"] == 1
    assert updated_req1["status"] == RequirementStatus.CHAINED.value

    assert updated_req2["chain_order"] == 2
    assert updated_req2["status"] == RequirementStatus.CHAINED.value

    assert updated_req3["chain_order"] == 3
    assert updated_req3["status"] == RequirementStatus.CHAINED.value


def test_build_chain_no_requirements(
    graph_connection,
    project_manager,
    chain_builder,
):
    """测试构建空链"""
    # Arrange
    project = project_manager.create_project(graph_connection, "测试项目")
    project_id = project["project_id"]

    # Act
    result = chain_builder.build_chain(graph_connection, project_id)

    # Assert
    assert result["status"] == "no_requirements"
    assert "没有已验证的需求" in result["message"]


def test_build_chain_with_dependencies(
    graph_connection,
    project_manager,
    requirement_manager,
    validation_service,
    chain_builder,
    dependency_service,
):
    """测试构建有依赖关系的链"""
    # Arrange
    project = project_manager.create_project(graph_connection, "测试项目")
    project_id = project["project_id"]

    # 创建需求（req2 依赖 req1, req3 依赖 req2）
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

    dependency_service.add_dependency(
        graph_connection, req2["requirement_id"], req1["requirement_id"]
    )
    dependency_service.add_dependency(
        graph_connection, req3["requirement_id"], req2["requirement_id"]
    )

    # Act
    result = chain_builder.build_chain(graph_connection, project_id)

    # Assert
    assert result["status"] == "completed"
    assert result["total_nodes"] == 3

    # 验证顺序应该是 req1 -> req2 -> req3
    updated_req1 = requirement_manager.get_requirement(
        graph_connection, req1["requirement_id"]
    )
    updated_req2 = requirement_manager.get_requirement(
        graph_connection, req2["requirement_id"]
    )
    updated_req3 = requirement_manager.get_requirement(
        graph_connection, req3["requirement_id"]
    )

    assert updated_req1["chain_order"] == 1
    assert updated_req2["chain_order"] == 2
    assert updated_req3["chain_order"] == 3


def test_build_chain_with_parallel_nodes(
    graph_connection,
    project_manager,
    requirement_manager,
    validation_service,
    chain_builder,
    dependency_service,
):
    """测试构建有并行节点的链"""
    # Arrange
    project = project_manager.create_project(graph_connection, "测试项目")
    project_id = project["project_id"]

    # 创建需求（req2 和 req3 都依赖 req1，是并行节点）
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

    dependency_service.add_dependency(
        graph_connection, req2["requirement_id"], req1["requirement_id"]
    )
    dependency_service.add_dependency(
        graph_connection, req3["requirement_id"], req1["requirement_id"]
    )

    # Act
    result = chain_builder.build_chain(graph_connection, project_id)

    # Assert
    assert result["status"] == "completed"
    assert result["total_nodes"] == 3

    # 验证 req1 是头节点
    updated_req1 = requirement_manager.get_requirement(
        graph_connection, req1["requirement_id"]
    )
    assert updated_req1["chain_order"] == 1


def test_build_chain_cycle_detection(
    graph_connection,
    project_manager,
    requirement_manager,
    validation_service,
    chain_builder,
    dependency_service,
):
    """测试构建链时的循环依赖检测"""
    # Arrange
    project = project_manager.create_project(graph_connection, "测试项目")
    project_id = project["project_id"]

    # 创建需求
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

    # 创建依赖链
    dependency_service.add_dependency(
        graph_connection, req2["requirement_id"], req1["requirement_id"]
    )
    dependency_service.add_dependency(
        graph_connection, req3["requirement_id"], req2["requirement_id"]
    )

    # 创建循环: 直接在数据库中创建循环依赖
    graph_connection.execute(
        CREATE_DEPENDS_ON,
        {
            "requirement_uuid": req1["requirement_id"],
            "dependency_uuid": req3["requirement_id"],
        },
    )

    # Act & Assert
    with pytest.raises(ValueError, match="循环依赖"):
        chain_builder.build_chain(graph_connection, project_id)


def test_build_chain_with_invalid_order(
    graph_connection,
    project_manager,
    requirement_manager,
    validation_service,
    chain_builder,
):
    """测试使用无效的顺序构建链"""
    # Arrange
    project = project_manager.create_project(graph_connection, "测试项目")
    project_id = project["project_id"]

    req1 = requirement_manager.add_requirement(graph_connection, project_id, "需求1")
    req2 = requirement_manager.add_requirement(graph_connection, project_id, "需求2")

    validation_service.add_validation(
        graph_connection, req1["requirement_id"], [{"name": "测试1"}]
    )
    validation_service.add_validation(
        graph_connection, req2["requirement_id"], [{"name": "测试2"}]
    )

    # Act & Assert: 顺序中缺少 req2
    with pytest.raises(ValueError, match="排序顺序不匹配"):
        chain_builder.build_chain_with_order(
            graph_connection,
            project_id,
            [req1["requirement_id"]],  # 缺少 req2
        )


def test_reset_chain(
    graph_connection,
    project_manager,
    requirement_manager,
    validation_service,
    chain_builder,
):
    """测试重置链化状态"""
    # Arrange
    project = project_manager.create_project(graph_connection, "测试项目")
    project_id = project["project_id"]

    req1 = requirement_manager.add_requirement(graph_connection, project_id, "需求1")
    req2 = requirement_manager.add_requirement(graph_connection, project_id, "需求2")

    validation_service.add_validation(
        graph_connection, req1["requirement_id"], [{"name": "测试1"}]
    )
    validation_service.add_validation(
        graph_connection, req2["requirement_id"], [{"name": "测试2"}]
    )

    chain_builder.build_chain(graph_connection, project_id)

    # Act
    result = chain_builder.reset_chain(graph_connection, project_id)

    # Assert
    assert result["status"] == "reset"
    assert result["reset_count"] == 2

    # 验证需求状态已重置
    updated_req1 = requirement_manager.get_requirement(
        graph_connection, req1["requirement_id"]
    )
    updated_req2 = requirement_manager.get_requirement(
        graph_connection, req2["requirement_id"]
    )

    assert updated_req1["status"] == RequirementStatus.VALIDATED.value
    assert updated_req1["chain_order"] is None

    assert updated_req2["status"] == RequirementStatus.VALIDATED.value
    assert updated_req2["chain_order"] is None


def test_build_chain_updates_chain_state(
    graph_connection,
    project_manager,
    requirement_manager,
    validation_service,
    chain_builder,
):
    """测试构建链时更新链化状态"""
    # Arrange
    project = project_manager.create_project(graph_connection, "测试项目")
    project_id = project["project_id"]

    req1 = requirement_manager.add_requirement(graph_connection, project_id, "需求1")
    validation_service.add_validation(
        graph_connection, req1["requirement_id"], [{"name": "测试1"}]
    )

    # Act
    chain_builder.build_chain(graph_connection, project_id)

    # Assert
    result = graph_connection.execute(
        GET_CHAIN_STATE_BY_PROJECT, {"project_uuid": project_id}
    )
    chain_state = list(result)[0]

    assert chain_state is not None
    assert chain_state[2] == ChainStatus.COMPLETED.value  # status
    assert chain_state[3] == req1["requirement_id"]  # chain_head_uuid
    assert chain_state[4] == req1["requirement_id"]  # current_node_uuid
    assert chain_state[5] == 1  # total_nodes
    assert chain_state[6] == 0  # completed_nodes
    assert chain_state[7] == 0  # progress_percentage
    assert chain_state[8] is not None  # last_chained_at
