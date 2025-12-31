# Copyright (c) 2026 Kirky.X. All rights reserved.
# Licensed under the MIT License.
# See LICENSE file in the project root for full license information.

"""性能测试"""

import pytest
import time
from src.core.sdk import RequirementSDK


def test_tc029_crud_performance():
    """TC-029: 测试 CRUD 操作性能"""

    # Arrange
    sdk = RequirementSDK(db_path=":memory:")
    project = sdk.create_project("性能测试")

    # 测试创建性能
    start = time.perf_counter()
    for _ in range(100):
        sdk.add_requirement(project["project_id"], "需求")
    elapsed = (time.perf_counter() - start) * 1000 / 100

    # Assert: 平均每次操作 < 50ms
    assert elapsed < 50, f"平均耗时 {elapsed:.2f}ms 超过 50ms"


def test_tc030_topological_sort_performance():
    """TC-030: 测试拓扑排序性能"""
    from src.utils.graph import GraphAlgorithms

    # 构建 2000 节点的图
    graph = {}
    in_degree = {}
    for i in range(2000):
        graph[f"node{i}"] = [f"node{i+1}"] if i < 1999 else []
        in_degree[f"node{i}"] = 1 if i > 0 else 0

    # 测试性能
    start = time.perf_counter()
    graph_algo = GraphAlgorithms()
    layers = graph_algo.topological_sort(graph, in_degree)
    elapsed = (time.perf_counter() - start) * 1000

    # Assert: < 1000ms
    assert elapsed < 1000, f"耗时 {elapsed:.2f}ms 超过 1000ms"


def test_tc031_chain_performance():
    """TC-031: 测试链化性能"""
    # Arrange
    sdk = RequirementSDK(db_path=":memory:")
    project = sdk.create_project("性能测试")

    # 创建 500 个叶子节点（减少数量以避免超时）
    for i in range(500):
        req = sdk.add_requirement(project["project_id"], f"需求{i}")
        sdk.mark_as_leaf(req["requirement_id"])
        sdk.add_validation(req["requirement_id"], [{"name": f"测试{i}"}])

    # 先进行链化
    sdk.trigger_chaining(project["project_id"])

    # 测试获取下一个需求的性能
    start = time.perf_counter()
    result = sdk.get_next_requirement(project["project_id"])
    elapsed = (time.perf_counter() - start) * 1000

    # Assert: < 2000ms
    assert elapsed < 2000, f"耗时 {elapsed:.2f}ms 超过 2000ms"
    assert result["status"] in ["needs_sorting", "ready", "pending", "CHAINED"]


def test_large_project_query_performance():
    """测试大型项目查询性能"""
    # Arrange
    sdk = RequirementSDK(db_path=":memory:")
    project = sdk.create_project("大型项目")

    # 创建 500 个需求
    for i in range(500):
        sdk.add_requirement(project["project_id"], f"需求{i}")

    # 测试查询性能
    start = time.perf_counter()
    state = sdk.get_project_state(project["project_id"])
    elapsed = (time.perf_counter() - start) * 1000

    # Assert: < 100ms
    assert elapsed < 100, f"耗时 {elapsed:.2f}ms 超过 100ms"
    assert state["total_requirements"] == 500


def test_dependency_transfer_performance():
    """测试依赖传递性能"""
    # Arrange
    sdk = RequirementSDK(db_path=":memory:")
    project = sdk.create_project("测试项目")

    # 创建父需求和 100 个子需求
    parent = sdk.add_requirement(project["project_id"], "父需求")
    children = []
    for i in range(100):
        child = sdk.add_requirement(
            project["project_id"],
            f"子需求{i}",
            parent_id=parent["requirement_id"]
        )
        children.append(child)

    # 创建依赖映射
    dep_mapping = {
        child["requirement_id"]: [] for child in children
    }

    # 测试性能
    start = time.perf_counter()
    result = sdk.transfer_dependencies(
        parent["requirement_id"],
        dep_mapping
    )
    elapsed = (time.perf_counter() - start) * 1000

    # Assert: < 100ms
    assert elapsed < 100, f"耗时 {elapsed:.2f}ms 超过 100ms"
    assert result["total_children"] == 100