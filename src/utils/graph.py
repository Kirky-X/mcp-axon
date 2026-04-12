# Copyright (c) 2026 Kirky.X. All rights reserved.
# Licensed under the MIT License.
# See LICENSE file in the project root for full license information.

"""图算法工具类"""

import hashlib
import logging
from collections import deque
from typing import Any, Dict, List, Optional, Set

logger = logging.getLogger(__name__)

# 图大小限制，防止 DoS 攻击
MAX_GRAPH_NODES = 10000
MAX_GRAPH_EDGES = 50000


def _graph_key(graph: Dict[str, List[str]]) -> str:
    """生成图的缓存键"""
    # 将图转换为排序后的字符串表示
    # 对节点和边进行排序以确保一致性
    sorted_items = sorted(graph.items())
    graph_str = str(sorted_items)
    # 使用哈希作为键
    return hashlib.md5(graph_str.encode(), usedforsecurity=False).hexdigest()


class GraphAlgorithms:
    """图算法工具类"""

    # 图大小限制（类常量）
    MAX_NODES = MAX_GRAPH_NODES
    MAX_EDGES = MAX_GRAPH_EDGES

    def __init__(self):
        """初始化图算法类，优先使用 NetworkX 版本（如果可用）"""
        # 检查 NetworkXGraphAlgorithms 是否可用（不是 None）
        self.use_networkx = NetworkXGraphAlgorithms is not None

        # 缓存字典
        self._topological_sort_cache: Dict[str, List[List[str]]] = {}
        self._detect_cycle_cache: Dict[str, Optional[List[str]]] = {}

    def _validate_graph_size(self, graph: Dict[str, List[str]]) -> None:
        """
        验证图大小是否在限制范围内

        Args:
            graph: 邻接表

        Raises:
            ValueError: 图过大
        """
        node_count = len(graph)
        edge_count = sum(len(neighbors) for neighbors in graph.values())

        if node_count > self.MAX_NODES:
            raise ValueError(f"图节点数 ({node_count}) 超过限制 ({self.MAX_NODES})")

        if edge_count > self.MAX_EDGES:
            raise ValueError(f"图边数 ({edge_count}) 超过限制 ({self.MAX_EDGES})")

    def topological_sort(
        self, graph: Dict[str, List[str]], in_degree: Optional[Dict[str, int]] = None
    ) -> List[List[str]]:
        """
        Kahn 算法拓扑排序（分层）

        时间复杂度: O(V + E)
        空间复杂度: O(V)

        Args:
            graph: 邻接表 {node_id: [neighbor_ids]}
            in_degree: 入度表 {node_id: degree}，如果为 None 则自动计算

        Returns:
            分层结果 [[layer0], [layer1], ...]，每层的节点可以并行执行

        Raises:
            ValueError: 检测到循环依赖或图过大
        """
        # 验证图大小
        self._validate_graph_size(graph)

        # 检查缓存
        cache_key = _graph_key(graph)
        if cache_key in self._topological_sort_cache:
            logger.debug(f"拓扑排序缓存命中: {cache_key}")
            return self._topological_sort_cache[cache_key]

        if self.use_networkx:
            # 将图转换为 NetworkX 格式
            nodes_data = [{"id": node_id} for node_id in graph.keys()]

            def get_id_func(node):
                return node["id"]

            def get_deps_func(node):
                return graph[node["id"]]

            if NetworkXGraphAlgorithms is None:
                # 使用纯 Python 实现
                result = self._topological_sort_fallback(graph, in_degree)
            else:
                nx_graph = NetworkXGraphAlgorithms.build_networkx_graph(
                    nodes_data, get_id_func, get_deps_func
                )
                result = NetworkXGraphAlgorithms.topological_sort_with_layers(nx_graph)
        else:
            # 使用纯 Python 实现
            result = self._topological_sort_fallback(graph, in_degree)

        # 缓存结果
        self._topological_sort_cache[cache_key] = result

        # 限制缓存大小（最多缓存 100 个图）
        if len(self._topological_sort_cache) > 100:
            # 删除最旧的缓存
            oldest_key = next(iter(self._topological_sort_cache))
            del self._topological_sort_cache[oldest_key]

        return result

    @staticmethod
    def _topological_sort_fallback(
        graph: Dict[str, List[str]], in_degree: Optional[Dict[str, int]] = None
    ) -> List[List[str]]:
        """
        回退用的纯 Python 拓扑排序实现

        Args:
            graph: 邻接表 {node_id: [neighbor_ids]}
            in_degree: 入度表 {node_id: degree}，如果为 None 则自动计算

        Returns:
            分层结果 [[layer0], [layer1], ...]，每层的节点可以并行执行

        Raises:
            ValueError: 检测到循环依赖
        """
        # 计算入度
        if in_degree is None:
            in_degree = GraphAlgorithms._calculate_in_degree(graph)

        # 找出入度为 0 的节点（第一层）
        queue = deque([node for node, degree in in_degree.items() if degree == 0])
        layers = []

        while queue:
            # 当前层所有节点（可并行）
            current_layer = []
            layer_size = len(queue)

            for _ in range(layer_size):
                node = queue.popleft()
                current_layer.append(node)

                # 更新邻居节点入度
                for neighbor in graph.get(node, []):
                    in_degree[neighbor] -= 1
                    if in_degree[neighbor] == 0:
                        queue.append(neighbor)

            layers.append(current_layer)

        # 检测环路
        if sum(in_degree.values()) > 0:
            cycle_nodes = [node for node, degree in in_degree.items() if degree > 0]
            raise ValueError(f"检测到循环依赖，节点: {cycle_nodes}")

        return layers

    def detect_cycle_dfs(self, graph: Dict[str, List[str]]) -> Optional[List[str]]:
        """
        使用 DFS 检测环路

        时间复杂度: O(V + E)

        Args:
            graph: 邻接表 {node_id: [neighbor_ids]}

        Returns:
            环路路径 [node1, node2, ..., node1] 或 None

        Raises:
            ValueError: 图过大
        """
        # 验证图大小
        self._validate_graph_size(graph)

        # 检查缓存
        cache_key = _graph_key(graph)
        if cache_key in self._detect_cycle_cache:
            logger.debug(f"环路检测缓存命中: {cache_key}")
            return self._detect_cycle_cache[cache_key]

        if self.use_networkx:
            # 将图转换为 NetworkX 格式
            nodes_data = [{"id": node_id} for node_id in graph.keys()]

            def get_id_func(node):
                return node["id"]

            def get_deps_func(node):
                return graph[node["id"]]

            if NetworkXGraphAlgorithms is None:
                # 使用纯 Python 实现
                result = self._detect_cycle_dfs_fallback(graph)
            else:
                nx_graph = NetworkXGraphAlgorithms.build_networkx_graph(
                    nodes_data, get_id_func, get_deps_func
                )
                result = NetworkXGraphAlgorithms.find_cycle(nx_graph)
        else:
            # 使用纯 Python 实现
            result = self._detect_cycle_dfs_fallback(graph)

        # 缓存结果
        self._detect_cycle_cache[cache_key] = result

        # 限制缓存大小（最多缓存 100 个图）
        if len(self._detect_cycle_cache) > 100:
            # 删除最旧的缓存
            oldest_key = next(iter(self._detect_cycle_cache))
            del self._detect_cycle_cache[oldest_key]

        return result

    @staticmethod
    def _detect_cycle_dfs_fallback(graph: Dict[str, List[str]]) -> Optional[List[str]]:
        """
        回退用的纯 Python 环路检测实现

        Args:
            graph: 邻接表 {node_id: [neighbor_ids]}

        Returns:
            环路路径 [node1, node2, ..., node1] 或 None
        """
        visited: Set[str] = set()
        rec_stack: Set[str] = set()
        path: List[str] = []

        def dfs(node: str) -> Optional[List[str]]:
            visited.add(node)
            rec_stack.add(node)
            path.append(node)

            for neighbor in graph.get(node, []):
                if neighbor not in visited:
                    result = dfs(neighbor)
                    if result:
                        return result
                elif neighbor in rec_stack:
                    # 找到环路
                    cycle_start = path.index(neighbor)
                    return path[cycle_start:] + [neighbor]

            rec_stack.remove(node)
            path.pop()
            return None

        for node in graph:
            if node not in visited:
                result = dfs(node)
                if result:
                    return result

        return None

    @staticmethod
    def build_dependency_graph(
        nodes: List[Any], get_id_func, get_deps_func
    ) -> Dict[str, List[str]]:
        """
        构建依赖图（邻接表）

        边方向：依赖 -> 节点（表示"节点依赖于依赖"）

        Args:
            nodes: 节点列表
            get_id_func: 获取节点 ID 的函数
            get_deps_func: 获取节点依赖列表的函数

        Returns:
            邻接表 {node_id: [dependent_node_ids]}
        """
        graph: Dict[str, List[str]] = {}

        # 初始化所有节点
        for node in nodes:
            node_id = get_id_func(node)
            graph[node_id] = []

        # 构建反向边：依赖 -> 节点
        for node in nodes:
            node_id = get_id_func(node)
            deps = get_deps_func(node)
            for dep_id in deps:
                if dep_id not in graph:
                    graph[dep_id] = []
                graph[dep_id].append(node_id)

        return graph

    @staticmethod
    def _calculate_in_degree(graph: Dict[str, List[str]]) -> Dict[str, int]:
        """
        计算图中所有节点的入度

        Args:
            graph: 邻接表 {node_id: [neighbor_ids]}

        Returns:
            入度表 {node_id: degree}
        """
        in_degree: Dict[str, int] = {}

        # 初始化所有节点的入度为 0
        for node in graph:
            in_degree[node] = 0

        # 计算入度
        for node, neighbors in graph.items():
            for neighbor in neighbors:
                if neighbor not in in_degree:
                    in_degree[neighbor] = 0
                in_degree[neighbor] += 1

        return in_degree

    @staticmethod
    def flatten_layers(layers: List[List[str]]) -> List[str]:
        """
        将分层结果展平为单一列表

        Args:
            layers: 分层结果 [[layer0], [layer1], ...]

        Returns:
            展平后的节点列表 [node1, node2, ...]
        """
        result = []
        for layer in layers:
            result.extend(layer)
        return result

    @staticmethod
    def assign_parallel_groups(layers: List[List[str]]) -> Dict[str, int]:
        """
        将拓扑分层转换为节点并行组映射

        同层节点拥有相同的并行组号，可并行执行。
        层号即拓扑层级（0=无依赖，1=依赖层0，...）。

        Args:
            layers: 分层结果 [[layer0], [layer1], ...]

        Returns:
            节点到并行组号的映射 {node_id: group_index}
        """
        groups: Dict[str, int] = {}
        for layer_index, layer in enumerate(layers):
            for node_id in layer:
                groups[node_id] = layer_index
        return groups

    @staticmethod
    def get_parallel_nodes(layers: List[List[str]]) -> List[List[str]]:
        """
        获取所有并行节点组

        Args:
            layers: 分层结果 [[layer0], [layer1], ...]

        Returns:
            并行节点组列表，每个组包含可以并行执行的节点
        """
        # 过滤掉单节点层，只返回有多个节点的层
        return [layer for layer in layers if len(layer) > 1]

    @staticmethod
    def validate_order_consistency(
        parallel_nodes: List[str], sorted_order: List[str]
    ) -> bool:
        """
        验证排序一致性

        Args:
            parallel_nodes: 并行节点列表
            sorted_order: 排序后的节点列表

        Returns:
            True: 一致
            False: 不一致
        """
        return set(parallel_nodes) == set(sorted_order)


# 使用 NetworkX 优化的版本（可选）
NetworkXGraphAlgorithms: type[Any] | None = None

try:
    import networkx as nx

    class _NetworkXGraphAlgorithmsImpl:
        """使用 NetworkX 的图算法（性能更优）"""

        @staticmethod
        def build_networkx_graph(
            nodes: List[Any], get_id_func, get_deps_func
        ) -> nx.DiGraph:
            """
            构建 NetworkX 有向图

            Args:
                nodes: 节点列表
                get_id_func: 获取节点 ID 的函数
                get_deps_func: 获取节点依赖列表的函数

            Returns:
                NetworkX 有向图
            """
            G: nx.DiGraph = nx.DiGraph()

            for node in nodes:
                node_id = get_id_func(node)
                deps = get_deps_func(node)
                G.add_node(node_id, data=node)

                for dep_id in deps:
                    G.add_edge(node_id, dep_id)

            return G

        @staticmethod
        def topological_sort(G: nx.DiGraph) -> List[str]:
            """
            使用 NetworkX 的拓扑排序

            Args:
                G: NetworkX 有向图

            Returns:
                拓扑排序结果

            Raises:
                ValueError: 检测到循环依赖
            """
            try:
                return list(nx.topological_sort(G))
            except nx.NetworkXUnfeasible as e:
                cycle = _NetworkXGraphAlgorithmsImpl.find_cycle(G)
                raise ValueError(f"检测到循环依赖: {cycle}") from e

        @staticmethod
        def find_cycle(G: nx.DiGraph) -> Optional[List[str]]:
            """
            查找环路

            Args:
                G: NetworkX 有向图

            Returns:
                环路路径
            """
            try:
                cycle = nx.find_cycle(G, orientation="original")
                # 转换为节点列表，保持循环顺序
                cycle_nodes: List[str] = []
                visited_edges = set()
                for edge in cycle:
                    edge_key = (edge[0], edge[1])
                    if edge_key not in visited_edges:
                        if not cycle_nodes or cycle_nodes[-1] != edge[0]:
                            cycle_nodes.append(edge[0])
                        cycle_nodes.append(edge[1])
                        visited_edges.add(edge_key)
                # 去除重复并保持环路结构
                result = []
                for node in cycle_nodes:
                    if node not in result:
                        result.append(node)
                # 确保环路回到起点
                if result and result[0] != result[-1]:
                    result.append(result[0])
                return result
            except nx.NetworkXNoCycle:
                return None

        @staticmethod
        def topological_sort_with_layers(G: nx.DiGraph) -> List[List[str]]:
            """
            分层拓扑排序

            Args:
                G: NetworkX 有向图

            Returns:
                分层结果 [[layer0], [layer1], ...]

            Raises:
                ValueError: 检测到循环依赖
            """
            if not G.nodes():
                return []

            # 使用改进的 Kahn 算法进行分层排序
            in_degree = {node: G.in_degree(node) for node in G.nodes()}
            queue = deque([node for node, degree in in_degree.items() if degree == 0])
            layers = []

            while queue:
                current_layer = []
                layer_size = len(queue)

                for _ in range(layer_size):
                    node = queue.popleft()
                    current_layer.append(node)

                    for neighbor in G.successors(node):
                        in_degree[neighbor] -= 1
                        if in_degree[neighbor] == 0:
                            queue.append(neighbor)

                layers.append(current_layer)

            # 检测环路
            if sum(in_degree.values()) > 0:
                cycle_nodes = [node for node, degree in in_degree.items() if degree > 0]
                raise ValueError(f"检测到循环依赖，节点: {cycle_nodes}")

            return layers

    # 赋值给全局变量
    NetworkXGraphAlgorithms = _NetworkXGraphAlgorithmsImpl

except ImportError:
    # NetworkX 是必需依赖（pyproject.toml），此分支理论上不会触发
    logger.debug("NetworkX 导入失败（不应发生）")
    NetworkXGraphAlgorithms = None  # type: ignore
