# Copyright (c) 2026 Kirky.X. All rights reserved.
# Licensed under the MIT License.
# See LICENSE file in the project root for full license information.

"""依赖关系管理服务测试"""

import pytest


def test_tc009_dependency_single_child_inheritance(
    graph_connection, project_manager, requirement_manager, dependency_service
):
    """TC-009: 测试单子需求依赖继承"""

    # Arrange
    project = project_manager.create_project(graph_connection, "测试项目")
    project_id = project["project_id"]

    # 创建依赖需求
    dep1 = requirement_manager.add_requirement(graph_connection, project_id, "依赖1")

    # 创建父需求并添加依赖
    parent = requirement_manager.add_requirement(graph_connection, project_id, "父需求")
    dependency_service.add_dependency(
        graph_connection, parent["requirement_id"], dep1["requirement_id"]
    )

    # 创建子需求
    child = requirement_manager.add_requirement(
        graph_connection, project_id, "子需求", parent_uuid=parent["requirement_id"]
    )

    # Act: 传递依赖（单子需求自动继承）
    result = dependency_service.transfer_dependencies(
        graph_connection, parent_uuid=parent["requirement_id"], dependency_mapping={}
    )

    # Assert
    child_deps = dependency_service.get_dependencies(
        graph_connection, child["requirement_id"]
    )
    assert dep1["requirement_id"] in child_deps
    assert result["total_children"] == 1


def test_transfer_dependencies_with_mapping(
    graph_connection, project_manager, requirement_manager, dependency_service
):
    """测试使用映射传递依赖"""
    # Arrange
    project = project_manager.create_project(graph_connection, "测试项目")
    project_id = project["project_id"]

    # 创建依赖需求
    dep1 = requirement_manager.add_requirement(graph_connection, project_id, "依赖1")
    dep2 = requirement_manager.add_requirement(graph_connection, project_id, "依赖2")

    # 创建父需求并添加依赖
    parent = requirement_manager.add_requirement(graph_connection, project_id, "父需求")
    dependency_service.add_dependency(
        graph_connection, parent["requirement_id"], dep1["requirement_id"]
    )
    dependency_service.add_dependency(
        graph_connection, parent["requirement_id"], dep2["requirement_id"]
    )

    # 创建多个子需求
    child1 = requirement_manager.add_requirement(
        graph_connection, project_id, "子需求1", parent_uuid=parent["requirement_id"]
    )
    child2 = requirement_manager.add_requirement(
        graph_connection, project_id, "子需求2", parent_uuid=parent["requirement_id"]
    )

    # Act: 使用映射指定依赖
    dependency_service.transfer_dependencies(
        graph_connection,
        parent_uuid=parent["requirement_id"],
        dependency_mapping={
            child1["requirement_id"]: [dep1["requirement_id"]],
            child2["requirement_id"]: [dep2["requirement_id"]],
        },
    )

    # Assert
    child1_deps = dependency_service.get_dependencies(
        graph_connection, child1["requirement_id"]
    )
    child2_deps = dependency_service.get_dependencies(
        graph_connection, child2["requirement_id"]
    )
    assert child1_deps == [dep1["requirement_id"]]
    assert child2_deps == [dep2["requirement_id"]]


def test_add_dependency(
    graph_connection, project_manager, requirement_manager, dependency_service
):
    """测试添加依赖关系"""
    # Arrange
    project = project_manager.create_project(graph_connection, "测试项目")
    project_id = project["project_id"]

    req1 = requirement_manager.add_requirement(graph_connection, project_id, "需求1")
    req2 = requirement_manager.add_requirement(graph_connection, project_id, "需求2")

    # Act
    result = dependency_service.add_dependency(
        graph_connection,
        requirement_uuid=req2["requirement_id"],
        dependency_uuid=req1["requirement_id"],
    )

    # Assert
    assert req1["requirement_id"] in result["dependencies"]


def test_add_dependency_self_reference(
    graph_connection, project_manager, requirement_manager, dependency_service
):
    """测试添加自依赖（应失败）"""
    # Arrange
    project = project_manager.create_project(graph_connection, "测试项目")
    project_id = project["project_id"]

    req = requirement_manager.add_requirement(graph_connection, project_id, "需求")

    # Act & Assert
    with pytest.raises(ValueError, match="不能添加自依赖"):
        dependency_service.add_dependency(
            graph_connection, req["requirement_id"], req["requirement_id"]
        )


def test_add_dependency_cycle_detection(
    graph_connection, project_manager, requirement_manager, dependency_service
):
    """测试添加依赖时的循环依赖检测"""
    # Arrange
    project = project_manager.create_project(graph_connection, "测试项目")
    project_id = project["project_id"]

    req1 = requirement_manager.add_requirement(graph_connection, project_id, "需求1")
    req2 = requirement_manager.add_requirement(graph_connection, project_id, "需求2")
    req3 = requirement_manager.add_requirement(graph_connection, project_id, "需求3")

    # 创建依赖链: req1 <- req2 <- req3
    dependency_service.add_dependency(
        graph_connection, req2["requirement_id"], req1["requirement_id"]
    )
    dependency_service.add_dependency(
        graph_connection, req3["requirement_id"], req2["requirement_id"]
    )

    # Act & Assert: 尝试创建循环 req1 -> req3
    with pytest.raises(ValueError, match="循环依赖"):
        dependency_service.add_dependency(
            graph_connection, req1["requirement_id"], req3["requirement_id"]
        )


def test_remove_dependency(
    graph_connection, project_manager, requirement_manager, dependency_service
):
    """测试移除依赖关系"""
    # Arrange
    project = project_manager.create_project(graph_connection, "测试项目")
    project_id = project["project_id"]

    req1 = requirement_manager.add_requirement(graph_connection, project_id, "需求1")
    req2 = requirement_manager.add_requirement(graph_connection, project_id, "需求2")

    dependency_service.add_dependency(
        graph_connection, req2["requirement_id"], req1["requirement_id"]
    )

    # Act
    result = dependency_service.remove_dependency(
        graph_connection,
        requirement_uuid=req2["requirement_id"],
        dependency_uuid=req1["requirement_id"],
    )

    # Assert
    assert req1["requirement_id"] not in result["dependencies"]


def test_detect_cycle_no_cycle(
    graph_connection, project_manager, requirement_manager, dependency_service
):
    """测试检测循环依赖（无循环）"""
    # Arrange
    project = project_manager.create_project(graph_connection, "测试项目")
    project_id = project["project_id"]

    req1 = requirement_manager.add_requirement(graph_connection, project_id, "需求1")
    req2 = requirement_manager.add_requirement(graph_connection, project_id, "需求2")
    req3 = requirement_manager.add_requirement(graph_connection, project_id, "需求3")

    dependency_service.add_dependency(
        graph_connection, req2["requirement_id"], req1["requirement_id"]
    )
    dependency_service.add_dependency(
        graph_connection, req3["requirement_id"], req2["requirement_id"]
    )

    # Act
    cycle = dependency_service.detect_cycle(graph_connection, project_id)

    # Assert
    assert cycle is None


def test_detect_cycle_with_cycle(
    graph_connection, project_manager, requirement_manager, dependency_service
):
    """测试检测循环依赖（有循环）"""
    # Arrange
    project = project_manager.create_project(graph_connection, "测试项目")
    project_id = project["project_id"]

    req1 = requirement_manager.add_requirement(graph_connection, project_id, "需求1")
    req2 = requirement_manager.add_requirement(graph_connection, project_id, "需求2")
    req3 = requirement_manager.add_requirement(graph_connection, project_id, "需求3")

    dependency_service.add_dependency(
        graph_connection, req2["requirement_id"], req1["requirement_id"]
    )
    dependency_service.add_dependency(
        graph_connection, req3["requirement_id"], req2["requirement_id"]
    )

    # 直接创建循环依赖
    from src.db.graph_queries import CREATE_DEPENDS_ON

    graph_connection.execute(
        CREATE_DEPENDS_ON,
        {
            "requirement_uuid": req1["requirement_id"],
            "dependency_uuid": req3["requirement_id"],
        },
    )

    # Act
    cycle = dependency_service.detect_cycle(graph_connection, project_id)

    # Assert
    assert cycle is not None
    assert len(cycle) > 0


def test_transfer_dependencies_nonexistent_parent(graph_connection, dependency_service):
    """测试传递依赖时父需求不存在"""

    # Act & Assert
    with pytest.raises(ValueError, match="父需求不存在"):
        dependency_service.transfer_dependencies(
            graph_connection, parent_uuid="nonexistent-id", dependency_mapping={}
        )
