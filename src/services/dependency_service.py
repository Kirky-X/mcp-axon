# Copyright (c) 2026 Kirky.X. All rights reserved.
# Licensed under the MIT License.
# See LICENSE file in the project root for full license information.

"""依赖关系管理服务"""

import logging
import threading
from typing import Any, Dict, List, Optional, Set

import real_ladybug as lb

from src.db.graph_queries import (
    CHECK_WOULD_CREATE_CYCLE,
    CREATE_DEPENDS_ON,
    DELETE_DEPENDS_ON,
    DETECT_CYCLE_IN_PROJECT,
    GET_DEPENDENCIES,
    GET_DEPENDENTS,
    GET_REQUIREMENT_BY_UUID,
    GET_REQUIREMENTS_BY_PROJECT,
)
from src.utils.cache import CacheManager
from src.utils.event_logger import log_event
from src.utils.metrics import performance_monitor

logger = logging.getLogger(__name__)

# 尝试导入 NetworkX（用于无深度限制的循环检测）
try:
    import networkx as nx

    NETWORKX_AVAILABLE = True
except ImportError:
    NETWORKX_AVAILABLE = False
    logger.warning("NetworkX 未安装，将使用 Cypher 查询进行循环检测（有深度限制）")


class DependencyService:
    """依赖关系管理服务"""

    def __init__(self, cache: CacheManager):
        """初始化依赖服务

        Args:
            cache: 缓存管理器实例
        """
        self.cache = cache
        self._use_networkx = NETWORKX_AVAILABLE
        # 缓存项目依赖图，避免重复构建
        self._graph_cache: Optional[Any] = None  # nx.DiGraph 或 None
        self._cache_project_uuid: Optional[str] = None
        self._cache_lock = threading.RLock()  # 保护缓存的线程安全

    @performance_monitor("transfer_dependencies")
    def transfer_dependencies(
        self,
        conn: lb.Connection,
        parent_uuid: str,
        dependency_mapping: Dict[str, List[str]],
    ) -> Dict[str, Any]:
        """
        应用依赖传递映射

        当一个父需求被分解为多个子需求时，需要将父需求的依赖关系传递给子需求。

        规则:
        - 单子需求: 自动继承父需求的所有依赖
        - 多子需求: 使用 dependency_mapping 指定每个子需求的依赖

        Args:
            conn: 数据库连接
            parent_uuid: 父需求 ID
            dependency_mapping: 依赖映射 {子需求ID: [依赖ID列表]}

        Returns:
            操作结果
        """
        # 获取父需求
        result = conn.execute(GET_REQUIREMENT_BY_UUID, {"uuid": parent_uuid})
        rows = list(result)
        if not rows:
            raise ValueError(f"父需求不存在: {parent_uuid}")

        parent_row = rows[0]
        project_uuid = parent_row[1]  # project_uuid
        parent_deps = (
            parent_row[13] if len(parent_row) > 13 and parent_row[13] else []
        )  # dependencies

        # 获取所有子需求
        result = conn.execute(
            GET_REQUIREMENTS_BY_PROJECT, {"project_uuid": project_uuid}
        )
        children = [row for row in result if row[2] == parent_uuid]  # parent_uuid

        if not children:
            raise ValueError(f"父需求没有子需求: {parent_uuid}")

        children_uuids = [child[0] for child in children]

        # 检查映射的完整性
        for child_uuid in dependency_mapping.keys():
            if child_uuid not in children_uuids:
                raise ValueError(f"映射中的子需求不存在: {child_uuid}")

        # 验证所有依赖 ID 存在
        all_dep_uuids = set()
        for dep_uuids in dependency_mapping.values():
            all_dep_uuids.update(dep_uuids)

        if all_dep_uuids:
            # 查询所有需求 ID
            result = conn.execute(
                GET_REQUIREMENTS_BY_PROJECT, {"project_uuid": project_uuid}
            )
            existing_uuids = {row[0] for row in result}
            missing_deps = all_dep_uuids - existing_uuids
            if missing_deps:
                raise ValueError(f"依赖需求不存在: {missing_deps}")

        # 应用依赖映射
        updated_children = []
        for child in children:
            child_uuid = child[0]
            deps_to_add = []

            if child_uuid in dependency_mapping:
                # 使用映射指定的依赖
                deps_to_add = dependency_mapping[child_uuid]
            elif len(children) == 1 and parent_deps:
                # 单子需求：自动继承父需求的所有依赖
                deps_to_add = list(parent_deps)

            # 添加依赖边
            for dep_uuid in deps_to_add:
                try:
                    conn.execute(
                        CREATE_DEPENDS_ON,
                        {"requirement_uuid": child_uuid, "dependency_uuid": dep_uuid},
                    )
                except Exception as e:
                    if "already exists" not in str(e).lower():
                        raise

            updated_children.append(
                {"child_uuid": child_uuid, "dependencies": deps_to_add}
            )

            # 刷新该子需求的缓存
            self.cache.invalidate_requirement(child_uuid, project_uuid)

        # 刷新项目缓存
        self.cache.invalidate_project(project_uuid)

        # 记录事件
        log_event(
            conn,
            project_uuid,
            "DependenciesTransferred",
            parent_uuid,
            {
                "parent_uuid": parent_uuid,
                "mapping": dependency_mapping,
                "updated_children": updated_children,
            },
        )

        logger.info(f"依赖传递完成: {parent_uuid}")

        return {
            "parent_id": parent_uuid,
            "updated_children": updated_children,
            "total_children": len(children),
        }

    @performance_monitor("add_dependency")
    def add_dependency(
        self, conn: lb.Connection, requirement_uuid: str, dependency_uuid: str
    ) -> Dict[str, Any]:
        """
        添加依赖关系

        Args:
            conn: 数据库连接
            requirement_uuid: 需求 ID
            dependency_uuid: 依赖的需求 ID

        Returns:
            操作结果
        """
        # 获取需求
        result = conn.execute(GET_REQUIREMENT_BY_UUID, {"uuid": requirement_uuid})
        rows = list(result)
        if not rows:
            raise ValueError(f"需求不存在: {requirement_uuid}")

        requirement = rows[0]
        project_uuid = requirement[1]

        # 获取依赖需求
        result = conn.execute(GET_REQUIREMENT_BY_UUID, {"uuid": dependency_uuid})
        rows = list(result)
        if not rows:
            raise ValueError(f"依赖需求不存在: {dependency_uuid}")

        dependency = rows[0]
        dep_project_uuid = dependency[1]

        # 检查是否属于同一项目
        if project_uuid != dep_project_uuid:
            raise ValueError("依赖需求必须属于同一项目")

        # 检查是否自依赖
        if requirement_uuid == dependency_uuid:
            raise ValueError("不能添加自依赖")

        # 检查是否已存在
        result = conn.execute(GET_DEPENDENCIES, {"requirement_uuid": requirement_uuid})
        existing_deps = [row[0] for row in result]
        if dependency_uuid in existing_deps:
            raise ValueError("依赖关系已存在")

        # 检查循环依赖（使用 Cypher 查询）
        if self._would_create_cycle(conn, requirement_uuid, dependency_uuid):
            raise ValueError(
                f"添加依赖会创建循环依赖: {requirement_uuid} -> {dependency_uuid}"
            )

        # 添加依赖边
        conn.execute(
            CREATE_DEPENDS_ON,
            {"requirement_uuid": requirement_uuid, "dependency_uuid": dependency_uuid},
        )

        # 记录事件
        log_event(
            conn,
            project_uuid,
            "DependencyAdded",
            requirement_uuid,
            {"requirement_uuid": requirement_uuid, "dependency_uuid": dependency_uuid},
        )

        logger.info(f"依赖添加成功: {requirement_uuid} -> {dependency_uuid}")

        # 获取更新后的依赖列表
        result = conn.execute(GET_DEPENDENCIES, {"requirement_uuid": requirement_uuid})
        dependencies = [row[0] for row in result]

        return {
            "requirement_uuid": requirement_uuid,
            "dependency_uuid": dependency_uuid,
            "dependencies": dependencies,
        }

    def remove_dependency(
        self, conn: lb.Connection, requirement_uuid: str, dependency_uuid: str
    ) -> Dict[str, Any]:
        """
        移除依赖关系

        Args:
            conn: 数据库连接
            requirement_uuid: 需求 ID
            dependency_uuid: 依赖的需求 ID

        Returns:
            操作结果
        """
        # 获取需求
        result = conn.execute(GET_REQUIREMENT_BY_UUID, {"uuid": requirement_uuid})
        rows = list(result)
        if not rows:
            raise ValueError(f"需求不存在: {requirement_uuid}")

        project_uuid = rows[0][1]

        # 检查依赖是否存在
        result = conn.execute(GET_DEPENDENCIES, {"requirement_uuid": requirement_uuid})
        existing_deps = [row[0] for row in result]
        if dependency_uuid not in existing_deps:
            raise ValueError("依赖关系不存在")

        # 移除依赖边
        conn.execute(
            DELETE_DEPENDS_ON,
            {"requirement_uuid": requirement_uuid, "dependency_uuid": dependency_uuid},
        )

        # 记录事件
        log_event(
            conn,
            project_uuid,
            "DependencyRemoved",
            requirement_uuid,
            {"requirement_uuid": requirement_uuid, "dependency_uuid": dependency_uuid},
        )

        logger.info(f"依赖移除成功: {requirement_uuid} -> {dependency_uuid}")

        # 获取更新后的依赖列表
        result = conn.execute(GET_DEPENDENCIES, {"requirement_uuid": requirement_uuid})
        dependencies = [row[0] for row in result]

        return {
            "requirement_uuid": requirement_uuid,
            "dependency_uuid": dependency_uuid,
            "dependencies": dependencies,
        }

    def detect_cycle(
        self, conn: lb.Connection, project_uuid: str
    ) -> Optional[List[str]]:
        """
        检测项目中的循环依赖

        Args:
            conn: 数据库连接
            project_uuid: 项目 ID

        Returns:
            循环路径，如果没有循环则返回 None
        """
        result = conn.execute(DETECT_CYCLE_IN_PROJECT, {"project_uuid": project_uuid})
        rows = list(result)

        if rows:
            cycle_start = rows[0][0]  # cycle_start 节点
            if cycle_start:
                return [cycle_start]

        return None

    def _would_create_cycle(
        self, conn: lb.Connection, requirement_uuid: str, dependency_uuid: str
    ) -> bool:
        """
        检查添加依赖是否会创建循环依赖（使用 Cypher 查询）

        检查逻辑：从 dependency_uuid 是否能通过 DEPENDS_ON 边到达 requirement_uuid
        如果能到达，说明添加依赖后会形成环

        Args:
            conn: 数据库连接
            requirement_uuid: 需求 ID
            dependency_uuid: 依赖的需求 ID

        Returns:
            是否会创建循环依赖
        """
        # 快速检查：如果两个ID相同，直接返回True
        if requirement_uuid == dependency_uuid:
            return True

        # 使用 Cypher 查询检测：从 dependency_uuid 能否到达 requirement_uuid
        result = conn.execute(
            CHECK_WOULD_CREATE_CYCLE,
            {"dependency_uuid": dependency_uuid, "requirement_uuid": requirement_uuid},
        )
        rows = list(result)

        # 如果返回结果，说明存在路径，添加后会形成环
        return len(rows) > 0

    def get_dependencies(self, conn: lb.Connection, requirement_uuid: str) -> List[str]:
        """
        获取需求的所有依赖

        Args:
            conn: 数据库连接
            requirement_uuid: 需求 ID

        Returns:
            依赖 ID 列表
        """
        result = conn.execute(GET_DEPENDENCIES, {"requirement_uuid": requirement_uuid})
        return [row[0] for row in result]

    def get_dependents(self, conn: lb.Connection, requirement_uuid: str) -> List[str]:
        """
        获取依赖于此需求的所有需求

        Args:
            conn: 数据库连接
            requirement_uuid: 需求 ID

        Returns:
            依赖者 ID 列表
        """
        result = conn.execute(GET_DEPENDENTS, {"requirement_uuid": requirement_uuid})
        return [row[0] for row in result]

    # ============ NetworkX 增强方法（无深度限制）============

    def _build_dependency_graph_nx(self, conn: lb.Connection, project_uuid: str) -> Any:
        """
        使用 NetworkX 构建项目依赖图（无深度限制）

        Args:
            conn: 数据库连接
            project_uuid: 项目 ID

        Returns:
            NetworkX DiGraph 对象
        """
        if not self._use_networkx:
            return None

        # 检查缓存（线程安全）
        with self._cache_lock:
            if self._cache_project_uuid == project_uuid and self._graph_cache:
                # 返回副本避免并发修改
                return self._graph_cache.copy()

        # 查询所有需求
        result = conn.execute(
            GET_REQUIREMENTS_BY_PROJECT, {"project_uuid": project_uuid}
        )
        requirements = list(result)

        # 构建 NetworkX 图
        G: Any = nx.DiGraph()

        # 添加所有节点
        for req in requirements:
            req_uuid = req[0]
            G.add_node(req_uuid, content=req[3], status=req[5])

        # 添加依赖边
        for req in requirements:
            req_uuid = req[0]
            # 查询该需求的依赖
            dep_result = conn.execute(GET_DEPENDENCIES, {"requirement_uuid": req_uuid})
            for dep_row in dep_result:
                dep_uuid = dep_row[0]
                # 边方向：req_uuid -> dep_uuid（表示 req_uuid 依赖于 dep_uuid）
                G.add_edge(req_uuid, dep_uuid)

        # 更新缓存（线程安全）
        with self._cache_lock:
            self._graph_cache = G
            self._cache_project_uuid = project_uuid

        return G

    def get_dependency_chain(
        self,
        conn: lb.Connection,
        requirement_uuid: str,
        direction: str = "upstream",
        max_depth: int = 10,
    ) -> Dict[str, Any]:
        """
        获取需求的依赖链

        Args:
            conn: 数据库连接
            requirement_uuid: 需求 ID
            direction: 方向 - "upstream"(上游依赖), "downstream"(下游被依赖), "both"
            max_depth: 最大遍历深度

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
            dep_result = conn.execute(GET_DEPENDENCIES, {"requirement_uuid": uuid})
            for dep_row in dep_result:
                dep_uuid = dep_row[0]
                if dep_uuid not in visited:
                    visited.add(dep_uuid)
                    # 获取需求详情
                    req_result = conn.execute(
                        GET_REQUIREMENT_BY_UUID, {"uuid": dep_uuid}
                    )
                    req_rows = list(req_result)
                    if req_rows:
                        content = req_rows[0][3]
                        deps.append(
                            {
                                "uuid": dep_uuid,
                                "content": (
                                    content[:50] + "..."
                                    if len(content) > 50
                                    else content
                                ),
                                "status": req_rows[0][5],
                                "depth": depth,
                                "upstream": get_upstream(dep_uuid, depth + 1),
                            }
                        )
            return deps

        def get_downstream(uuid: str, depth: int) -> List[Dict[str, Any]]:
            if depth > max_depth:
                return []
            dependents = []
            dep_result = conn.execute(GET_DEPENDENTS, {"requirement_uuid": uuid})
            for dep_row in dep_result:
                dep_uuid = dep_row[0]
                if dep_uuid not in visited:
                    visited.add(dep_uuid)
                    # 获取需求详情
                    req_result = conn.execute(
                        GET_REQUIREMENT_BY_UUID, {"uuid": dep_uuid}
                    )
                    req_rows = list(req_result)
                    if req_rows:
                        content = req_rows[0][3]
                        dependents.append(
                            {
                                "uuid": dep_uuid,
                                "content": (
                                    content[:50] + "..."
                                    if len(content) > 50
                                    else content
                                ),
                                "status": req_rows[0][5],
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
