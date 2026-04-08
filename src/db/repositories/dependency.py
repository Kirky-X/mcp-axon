# Copyright (c) 2026 Kirky.X. All rights reserved.
# Licensed under the MIT License.
# See LICENSE file in the project root for full license information.

"""依赖 Repository - 依赖关系数据访问层"""

import logging
from typing import Any, Dict, List, Optional, Set

import real_ladybug as lb

from src.db.graph_queries import (
    CREATE_DEPENDS_ON,
    DELETE_DEPENDS_ON,
    GET_DEPENDENCIES,
    GET_DEPENDENTS,
    GET_REQUIREMENTS_BY_PROJECT,
)
from src.db.repositories.base import BaseRepository

logger = logging.getLogger(__name__)

# 尝试导入 NetworkX
try:
    import networkx as nx

    NETWORKX_AVAILABLE = True
except ImportError:
    NETWORKX_AVAILABLE = False


class DependencyRepository(BaseRepository):
    """依赖 Repository

    封装所有依赖关系相关的数据库操作。
    """

    def __init__(self, connection: lb.Connection):
        super().__init__(connection)
        self._use_networkx = NETWORKX_AVAILABLE
        self._graph_cache: Optional[Any] = None
        self._cache_project_uuid: Optional[str] = None

    def get_dependencies(self, requirement_uuid: str) -> List[str]:
        """获取需求的所有依赖

        Args:
            requirement_uuid: 需求 ID

        Returns:
            依赖 ID 列表
        """
        rows = self.execute_query(
            GET_DEPENDENCIES, {"requirement_uuid": requirement_uuid}
        )
        return [row[0] for row in rows]  # type: ignore[index]

    def get_dependents(self, requirement_uuid: str) -> List[str]:
        """获取依赖于此需求的所有需求

        Args:
            requirement_uuid: 需求 ID

        Returns:
            依赖者 ID 列表
        """
        rows = self.execute_query(
            GET_DEPENDENTS, {"requirement_uuid": requirement_uuid}
        )
        return [row[0] for row in rows]  # type: ignore[index]

    def add_dependency(self, requirement_uuid: str, dependency_uuid: str) -> bool:
        """添加依赖关系

        Args:
            requirement_uuid: 需求 ID
            dependency_uuid: 依赖的需求 ID

        Returns:
            是否成功
        """
        try:
            self.execute_write(
                CREATE_DEPENDS_ON,
                {
                    "requirement_uuid": requirement_uuid,
                    "dependency_uuid": dependency_uuid,
                },
            )
            # 清除缓存
            self._graph_cache = None
            return True
        except Exception as e:
            logger.error(f"添加依赖失败: {e}")
            return False

    def remove_dependency(self, requirement_uuid: str, dependency_uuid: str) -> bool:
        """移除依赖关系

        Args:
            requirement_uuid: 需求 ID
            dependency_uuid: 依赖的需求 ID

        Returns:
            是否成功
        """
        result = self.execute_write(
            DELETE_DEPENDS_ON,
            {
                "requirement_uuid": requirement_uuid,
                "dependency_uuid": dependency_uuid,
            },
        )
        if result:
            self._graph_cache = None
        return result

    def build_dependency_graph(
        self, project_uuid: str, use_networkx: bool = True
    ) -> Any:
        """构建项目依赖图

        Args:
            project_uuid: 项目 ID
            use_networkx: 是否使用 NetworkX（推荐）

        Returns:
            如果 use_networkx=True，返回 NetworkX DiGraph
            否则返回邻接表字典 {node_id: [dependent_node_ids]}
        """
        if use_networkx and self._use_networkx:
            return self._build_nx_graph(project_uuid)
        return self._build_adjacency_graph(project_uuid)

    def _build_nx_graph(self, project_uuid: str) -> Any:
        """使用 NetworkX 构建依赖图

        Args:
            project_uuid: 项目 ID

        Returns:
            NetworkX DiGraph
        """
        if not self._use_networkx:
            return None

        # 检查缓存
        if self._cache_project_uuid == project_uuid and self._graph_cache is not None:
            return self._graph_cache

        # 查询所有需求
        rows = self.execute_query(
            GET_REQUIREMENTS_BY_PROJECT, {"project_uuid": project_uuid}
        )

        G = nx.DiGraph()

        # 添加所有节点
        for row in rows:
            req_uuid = row[0]  # type: ignore[index]
            G.add_node(req_uuid)

        # 添加依赖边
        for row in rows:
            req_uuid = row[0]  # type: ignore[index]
            deps = row[12] if len(row) > 12 and row[12] else []  # type: ignore[index]
            for dep_uuid in deps:
                G.add_edge(req_uuid, dep_uuid)

        # 更新缓存
        self._graph_cache = G
        self._cache_project_uuid = project_uuid

        return G

    def _build_adjacency_graph(self, project_uuid: str) -> Dict[str, List[str]]:
        """构建邻接表形式的依赖图

        Args:
            project_uuid: 项目 ID

        Returns:
            邻接表 {node_id: [dependent_node_ids]}
        """
        rows = self.execute_query(
            GET_REQUIREMENTS_BY_PROJECT, {"project_uuid": project_uuid}
        )

        graph: Dict[str, List[str]] = {}

        # 初始化所有节点
        for row in rows:
            req_uuid = row[0]  # type: ignore[index]
            graph[req_uuid] = []

        # 构建边
        for row in rows:
            req_uuid = row[0]  # type: ignore[index]
            deps = row[12] if len(row) > 12 and row[12] else []  # type: ignore[index]
            for dep_uuid in deps:
                if dep_uuid in graph:
                    graph[dep_uuid].append(req_uuid)

        return graph

    def detect_cycle_with_networkx(self, project_uuid: str) -> Optional[List[str]]:
        """使用 NetworkX 检测循环依赖（无深度限制）

        Args:
            project_uuid: 项目 ID

        Returns:
            循环路径列表，无循环返回 None
        """
        if not self._use_networkx:
            logger.warning("NetworkX 不可用，无法执行无深度限制的循环检测")
            return None

        G = self._build_nx_graph(project_uuid)
        if G is None or G.number_of_nodes() == 0:
            return None

        try:
            cycle = nx.find_cycle(G, orientation="original")
            cycle_nodes: List[str] = []
            for edge in cycle:
                if edge[0] not in cycle_nodes:
                    cycle_nodes.append(edge[0])
                if edge[1] not in cycle_nodes:
                    cycle_nodes.append(edge[1])
            if cycle_nodes and cycle_nodes[0] != cycle_nodes[-1]:
                cycle_nodes.append(cycle_nodes[0])
            return cycle_nodes
        except nx.NetworkXNoCycle:
            return None

    def would_create_cycle_with_networkx(
        self,
        requirement_uuid: str,
        dependency_uuid: str,
        project_uuid: str,
    ) -> bool:
        """使用 NetworkX 检查添加依赖是否会创建循环

        Args:
            requirement_uuid: 需求 ID
            dependency_uuid: 依赖的需求 ID
            project_uuid: 项目 ID

        Returns:
            是否会创建循环
        """
        if not self._use_networkx:
            return False

        G = self._build_nx_graph(project_uuid)
        if G is None:
            return False

        try:
            return nx.has_path(G, dependency_uuid, requirement_uuid)
        except nx.NodeNotFound:
            return False

    def get_dependency_chain(
        self,
        requirement_uuid: str,
        direction: str = "upstream",
        max_depth: int = 10,
    ) -> Dict[str, Any]:
        """获取需求的依赖链

        Args:
            requirement_uuid: 需求 ID
            direction: 方向 - "upstream", "downstream", "both"
            max_depth: 最大深度

        Returns:
            依赖链信息
        """
        result: Dict[str, Any] = {
            "requirement_id": requirement_uuid,
            "upstream": [],
            "downstream": [],
        }

        visited: Set[str] = {requirement_uuid}

        def get_upstream(uuid: str, depth: int) -> List[Dict[str, Any]]:
            if depth > max_depth:
                return []
            deps = []
            for dep_uuid in self.get_dependencies(uuid):
                if dep_uuid not in visited:
                    visited.add(dep_uuid)
                    deps.append(
                        {
                            "uuid": dep_uuid,
                            "depth": depth,
                            "upstream": get_upstream(dep_uuid, depth + 1),
                        }
                    )
            return deps

        def get_downstream(uuid: str, depth: int) -> List[Dict[str, Any]]:
            if depth > max_depth:
                return []
            dependents = []
            for dep_uuid in self.get_dependents(uuid):
                if dep_uuid not in visited:
                    visited.add(dep_uuid)
                    dependents.append(
                        {
                            "uuid": dep_uuid,
                            "depth": depth,
                            "downstream": get_downstream(dep_uuid, depth + 1),
                        }
                    )
            return dependents

        if direction in ["upstream", "both"]:
            result["upstream"] = get_upstream(requirement_uuid, 1)

        if direction in ["downstream", "both"]:
            result["downstream"] = get_downstream(requirement_uuid, 1)

        return result

    def invalidate_cache(self):
        """清除依赖图缓存"""
        self._graph_cache = None
        self._cache_project_uuid = None
