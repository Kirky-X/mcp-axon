# Copyright (c) 2026 Kirky.X. All rights reserved.
# Licensed under the MIT License.
# See LICENSE file in the project root for full license information.

"""图算法工具类测试"""

import pytest
from src.utils.graph import GraphAlgorithms


def test_tc011_topological_sort_basic():
    """TC-011: 测试基本拓扑排序"""

    # Arrange - 构建正确的依赖图：D -> B, D -> C, B -> A, C -> A
    # 表示：A 依赖于 B 和 C，B 依赖于 D，C 依赖于 D
    graph = {
        "D": ["B", "C"],  # D 是 B 和 C 的依赖
        "B": ["A"],      # B 是 A 的依赖
        "C": ["A"],      # C 是 A 的依赖
        "A": []          # A 没有依赖其他节点
    }

    # Act
    graph_algo = GraphAlgorithms()
    layers = graph_algo.topological_sort(graph)

    # Assert
    assert len(layers) == 3
    assert layers[0] == ["D"]
    assert set(layers[1]) == {"B", "C"}
    assert layers[2] == ["A"]


def test_tc012_topological_sort_complex():
    """TC-012: 测试复杂拓扑排序"""
    # Arrange - 构建正确的依赖图
    # req1 依赖于 req2 和 req3
    # req2 依赖于 req4  
    # req3 依赖于 req4 和 req5
    # req4 依赖于 req6
    # req5 依赖于 req6
    # req6 没有依赖
    graph = {
        "req6": ["req4", "req5"],  # req6 是 req4 和 req5 的依赖
        "req4": ["req2"],         # req4 是 req2 的依赖
        "req5": ["req3"],         # req5 是 req3 的依赖
        "req2": ["req1"],         # req2 是 req1 的依赖
        "req3": ["req1"],         # req3 是 req1 的依赖
        "req1": []                # req1 没有依赖其他节点
    }

    # Act
    graph_algo = GraphAlgorithms()
    layers = graph_algo.topological_sort(graph)

    # Assert
    assert len(layers) == 4
    assert layers[0] == ["req6"]
    assert "req1" in layers[-1]


def test_tc013_cycle_detection():
    """TC-013: 测试循环依赖检测"""
    # Arrange
    graph = {
        "A": ["B"],
        "B": ["C"],
        "C": ["A"]  # 环路
    }

    # Act & Assert
    with pytest.raises(ValueError, match="循环依赖"):
        graph_algo = GraphAlgorithms()
        graph_algo.topological_sort(graph)


def test_tc014_dfs_cycle_detection():
    """TC-014: 测试 DFS 环路检测"""
    # Arrange
    graph = {
        "A": ["B"],
        "B": ["C"],
        "C": ["D"],
        "D": ["B"]  # B -> C -> D -> B
    }

    # Act
    graph_algo = GraphAlgorithms()
    cycle = graph_algo.detect_cycle_dfs(graph)

    # Assert
    assert cycle is not None
    assert "B" in cycle
    assert cycle[0] == cycle[-1]  # 环路首尾相同


def test_topological_sort_single_node():
    """测试单节点拓扑排序"""
    # Arrange
    graph = {"A": []}

    # Act
    graph_algo = GraphAlgorithms()
    layers = graph_algo.topological_sort(graph)

    # Assert
    assert len(layers) == 1
    assert layers[0] == ["A"]


def test_topological_sort_linear_chain():
    """测试线性链拓扑排序"""
    # Arrange - D -> C -> B -> A (A 依赖于 B，B 依赖于 C，C 依赖于 D)
    graph = {
        "D": ["C"],  # D 是 C 的依赖
        "C": ["B"],  # C 是 B 的依赖
        "B": ["A"],  # B 是 A 的依赖
        "A": []      # A 没有依赖其他节点
    }

    # Act
    graph_algo = GraphAlgorithms()
    layers = graph_algo.topological_sort(graph)

    # Assert
    assert len(layers) == 4
    assert layers[0] == ["D"]
    assert layers[1] == ["C"]
    assert layers[2] == ["B"]
    assert layers[3] == ["A"]


def test_dfs_cycle_detection_no_cycle():
    """测试 DFS 循环检测（无循环）"""
    # Arrange
    graph = {
        "A": ["B", "C"],
        "B": ["D"],
        "C": ["D"],
        "D": []
    }

    # Act
    graph_algo = GraphAlgorithms()
    cycle = graph_algo.detect_cycle_dfs(graph)

    # Assert
    assert cycle is None


def test_build_dependency_graph():
    """测试构建依赖图"""
    # Arrange
    nodes = [
        {"id": "A", "deps": ["B"]},
        {"id": "B", "deps": ["C"]},
        {"id": "C", "deps": []}
    ]

    # Act
    graph = GraphAlgorithms.build_dependency_graph(
        nodes,
        lambda n: n["id"],
        lambda n: n["deps"]
    )

    # Assert
    # 图表示：依赖 -> 节点
    # A 依赖 B，所以 B -> A
    # B 依赖 C，所以 C -> B
    # C 没有依赖，所以 C -> []
    assert graph == {
        "A": [],
        "B": ["A"],
        "C": ["B"]
    }


def test_flatten_layers():
    """测试展平分层结果"""
    # Arrange
    layers = [["A"], ["B", "C"], ["D"]]

    # Act
    result = GraphAlgorithms.flatten_layers(layers)

    # Assert
    assert result == ["A", "B", "C", "D"]


def test_get_parallel_nodes():
    """测试获取并行节点"""
    # Arrange
    layers = [["A"], ["B", "C"], ["D"], ["E", "F", "G"], ["H"]]

    # Act
    parallel_nodes = GraphAlgorithms.get_parallel_nodes(layers)

    # Assert
    assert len(parallel_nodes) == 2
    assert set(parallel_nodes[0]) == {"B", "C"}
    assert set(parallel_nodes[1]) == {"E", "F", "G"}


def test_validate_order_consistency():
    """测试验证排序一致性"""
    # Arrange
    parallel_nodes = ["A", "B", "C"]
    sorted_order = ["B", "A", "C"]

    # Act
    result = GraphAlgorithms.validate_order_consistency(parallel_nodes, sorted_order)

    # Assert
    assert result is True


def test_validate_order_consistency_invalid():
    """测试验证排序一致性（不一致）"""
    # Arrange
    parallel_nodes = ["A", "B", "C"]
    sorted_order = ["A", "B"]  # 缺少 C

    # Act
    result = GraphAlgorithms.validate_order_consistency(parallel_nodes, sorted_order)

    # Assert
    assert result is False


def test_topological_sort_with_custom_in_degree():
    """测试使用自定义入度表的拓扑排序"""
    # Arrange - D -> B, D -> C, B -> A, C -> A
    graph = {
        "D": ["B", "C"],  # D 是 B 和 C 的依赖
        "B": ["A"],      # B 是 A 的依赖
        "C": ["A"],      # C 是 A 的依赖
        "A": []          # A 没有依赖其他节点
    }
    in_degree = {"D": 0, "B": 1, "C": 1, "A": 2}

    # Act
    graph_algo = GraphAlgorithms()
    layers = graph_algo.topological_sort(graph, in_degree)

    # Assert
    assert layers[0] == ["D"]
    assert set(layers[1]) == {"B", "C"}