# Copyright (c) 2026 Kirky.X. All rights reserved.
# Licensed under the MIT License.
# See LICENSE file in the project root for full license information.

"""链化构建器服务"""

import logging
from typing import Any, Dict, List, Optional

import real_ladybug as lb

from src.db.graph_models import ChainStatus, RequirementStatus, now_utc
from src.db.graph_queries import (
    CREATE_CHAIN_STATE,
    CREATE_HAS_CHAIN_STATE,
    CREATE_NEXT_IN_CHAIN,
    DELETE_ALL_NEXT_IN_CHAIN,
    DETECT_CYCLE_IN_PROJECT,
    GET_CHAIN_STATE_BY_PROJECT,
    GET_DEPENDENCY_GRAPH,
    GET_REQUIREMENTS_BY_STATUS,
    RESET_ALL_CHAIN_ORDERS,
    RESET_CHAIN_STATE,
    UPDATE_CHAIN_STATE,
    UPDATE_REQUIREMENT_CHAIN_ORDER,
)
from src.utils.cache import CacheManager
from src.utils.event_logger import log_event
from src.utils.graph import GraphAlgorithms
from src.utils.metrics import performance_monitor

logger = logging.getLogger(__name__)


class ChainBuilder:
    """链化构建器"""

    def __init__(self, cache: CacheManager, graph_algorithms: GraphAlgorithms):
        """
        初始化链化构建器

        Args:
            cache: 缓存管理器实例
            graph_algorithms: 图算法工具实例
        """
        self._cache = cache
        self.graph_algos = graph_algorithms

    @performance_monitor("build_chain")
    def build_chain(self, conn: lb.Connection, project_uuid: str) -> Dict[str, Any]:
        """
        构建需求链

        Args:
            conn: 数据库连接
            project_uuid: 项目 ID

        Returns:
            链化结果
        """
        logger.info(f"开始构建链: {project_uuid}")

        # 清除旧的缓存结果（确保需求缓存同步）
        self._cache.invalidate_project(project_uuid)

        # 获取所有已验证的需求
        result = conn.execute(
            GET_REQUIREMENTS_BY_STATUS,
            {"project_uuid": project_uuid, "status": RequirementStatus.VALIDATED.value},
        )
        requirements = list(result)

        if not requirements:
            result = {
                "status": "no_requirements",
                "message": "没有已验证的需求需要链化",
            }
            self._cache.set_chain_result(project_uuid, result)
            return result

        # 构建依赖图（使用 Cypher 查询）
        graph = self._build_dependency_graph(conn, project_uuid)

        # 检测循环依赖
        cycle = self._detect_cycle(conn, project_uuid)
        if cycle:
            error_result = {
                "status": "error",
                "message": f"检测到循环依赖: {' -> '.join(cycle)}",
            }
            self._cache.set_chain_result(project_uuid, error_result)
            cycle_str = " -> ".join(cycle)
            raise ValueError(
                f"检测到循环依赖: {cycle_str}。"
                f"循环依赖会导致需求无法按顺序执行。"
                f"请检查依赖关系，移除形成环路的依赖。"
            )

        # 拓扑排序
        layers = self.graph_algos.topological_sort(graph)

        # 检查是否有并行节点
        parallel_nodes = self.graph_algos.get_parallel_nodes(layers)

        if parallel_nodes:
            # 有并行节点，使用默认顺序（按创建时间或ID排序）
            logger.info(f"检测到 {len(parallel_nodes)} 组并行节点，使用默认顺序")

            # 展平分层结果
            sorted_uuids = self.graph_algos.flatten_layers(layers)

            # 构建需求 UUID 到需求的映射
            req_map = {req[0]: req for req in requirements}

            # 使用默认顺序构建链表
            result = self._link_requirements(conn, project_uuid, sorted_uuids, req_map)
        else:
            # 没有并行节点，直接构建链表
            result = self._build_chain_from_sorted(
                conn, project_uuid, layers, requirements
            )

        # 缓存结果
        self._cache.set_chain_result(project_uuid, result)
        return result

    @performance_monitor("build_chain_with_order")
    def build_chain_with_order(
        self, conn: lb.Connection, project_uuid: str, sorted_order: List[str]
    ) -> Dict[str, Any]:
        """
        使用指定的顺序构建链

        Args:
            conn: 数据库连接
            project_uuid: 项目 ID
            sorted_order: 排序后的节点 ID 列表

        Returns:
            链化结果
        """
        logger.info(f"使用指定顺序构建链: {project_uuid}")

        # 清除旧的缓存结果
        self._cache.invalidate_project(project_uuid)

        # 获取所有已验证的需求
        result = conn.execute(
            GET_REQUIREMENTS_BY_STATUS,
            {"project_uuid": project_uuid, "status": RequirementStatus.VALIDATED.value},
        )
        requirements = list(result)

        # 构建需求 UUID 到需求的映射
        req_map = {req[0]: req for req in requirements}

        # 验证排序顺序
        req_uuids = set(req[0] for req in requirements)
        sorted_uuids = set(sorted_order)

        if req_uuids != sorted_uuids:
            missing = req_uuids - sorted_uuids
            extra = sorted_uuids - req_uuids
            error_result = {
                "status": "error",
                "message": f"排序顺序不匹配。缺失: {missing}, 多余: {extra}",
            }
            self._cache.set_chain_result(project_uuid, error_result)
            raise ValueError(f"排序顺序不匹配。缺失: {missing}, 多余: {extra}")

        # 按排序顺序构建链表
        result = self._link_requirements(conn, project_uuid, sorted_order, req_map)

        # 缓存结果
        self._cache.set_chain_result(project_uuid, result)
        return result

    def _build_dependency_graph(
        self, conn: lb.Connection, project_uuid: str
    ) -> Dict[str, List[str]]:
        """
        构建依赖图（使用 Cypher 查询）

        边方向：依赖 -> 节点（表示"节点依赖于依赖"）

        Args:
            conn: 数据库连接
            project_uuid: 项目 ID

        Returns:
            依赖图 {node_id: [dependent_node_ids]}
        """
        # 使用 Cypher 查询获取依赖图
        result = conn.execute(
            GET_DEPENDENCY_GRAPH,
            {"project_uuid": project_uuid, "status": RequirementStatus.VALIDATED.value},
        )

        # 构建反向图（依赖 -> 被依赖）
        graph: Dict[str, List[str]] = {}

        for row in result:
            node_id = row[0]  # r.uuid
            deps = row[1] if row[1] else []  # collect(dep.uuid)

            # 初始化节点
            if node_id not in graph:
                graph[node_id] = []

            # 添加反向边：依赖 -> 节点
            for dep_id in deps:
                if dep_id not in graph:
                    graph[dep_id] = []
                graph[dep_id].append(node_id)

        return graph

    def _detect_cycle(
        self, conn: lb.Connection, project_uuid: str
    ) -> Optional[List[str]]:
        """
        检测循环依赖（使用 Cypher 查询）

        Args:
            conn: 数据库连接
            project_uuid: 项目 ID

        Returns:
            循环起始节点 UUID，如果没有循环则返回 None
        """
        result = conn.execute(DETECT_CYCLE_IN_PROJECT, {"project_uuid": project_uuid})
        rows = list(result)

        if rows:
            return rows[0][0]  # cycle_start

        return None

    def _build_chain_from_sorted(
        self,
        conn: lb.Connection,
        project_uuid: str,
        layers: List[List[str]],
        requirements: List,
    ) -> Dict[str, Any]:
        """
        从分层排序结果构建链

        Args:
            conn: 数据库连接
            project_uuid: 项目 ID
            layers: 分层排序结果
            requirements: 需求列表

        Returns:
            链化结果
        """
        # 展平分层结果
        sorted_uuids = self.graph_algos.flatten_layers(layers)

        # 构建需求 UUID 到需求的映射
        req_map = {req[0]: req for req in requirements}

        return self._link_requirements(conn, project_uuid, sorted_uuids, req_map)

    def _link_requirements(
        self,
        conn: lb.Connection,
        project_uuid: str,
        sorted_uuids: List[str],
        req_map: Dict[str, tuple],
    ) -> Dict[str, Any]:
        """
        构建链表结构（使用 NEXT_IN_CHAIN 边）

        Args:
            conn: 数据库连接
            project_uuid: 项目 ID
            sorted_uuids: 排序后的需求 ID 列表
            req_map: 需求映射

        Returns:
            链化结果
        """
        if not sorted_uuids:
            result = {"status": "completed", "chain_head": None, "total_nodes": 0}
            self._cache.set_chain_result(project_uuid, result)
            return result

        # 清除旧的 NEXT_IN_CHAIN 边
        conn.execute(DELETE_ALL_NEXT_IN_CHAIN, {"project_uuid": project_uuid})

        # 获取或创建链化状态
        result = conn.execute(
            GET_CHAIN_STATE_BY_PROJECT, {"project_uuid": project_uuid}
        )
        chain_state_rows = list(result)

        if not chain_state_rows:
            # 创建新的 ChainState
            import uuid

            chain_state_uuid = str(uuid.uuid4())
            conn.execute(
                CREATE_CHAIN_STATE,
                {
                    "uuid": chain_state_uuid,
                    "project_uuid": project_uuid,
                    "status": ChainStatus.BUILDING.value,
                    "chain_head_uuid": "",
                    "current_node_uuid": "",
                    "total_nodes": 0,
                    "completed_nodes": 0,
                    "progress_percentage": 0,
                    "last_chained_at": "",
                    "chain_version": 1,
                    "created_at": now_utc(),
                    "updated_at": now_utc(),
                },
            )
            # 创建 HAS_CHAIN_STATE 边
            conn.execute(
                CREATE_HAS_CHAIN_STATE,
                {"project_uuid": project_uuid, "chain_state_uuid": chain_state_uuid},
            )
        else:
            chain_state_uuid = chain_state_rows[0][0]

        # 设置链表指针
        chain_head_uuid = sorted_uuids[0]
        updated_at = now_utc()

        for i, req_uuid in enumerate(sorted_uuids):
            if req_uuid not in req_map:
                logger.warning(f"需求不存在: {req_uuid}")
                continue

            # 更新 chain_order 和 status
            conn.execute(
                UPDATE_REQUIREMENT_CHAIN_ORDER,
                {
                    "uuid": req_uuid,
                    "chain_order": i + 1,
                    "status": RequirementStatus.CHAINED.value,
                    "updated_at": updated_at,
                },
            )

            # 创建 NEXT_IN_CHAIN 边
            if i < len(sorted_uuids) - 1:
                next_uuid = sorted_uuids[i + 1]
                conn.execute(
                    CREATE_NEXT_IN_CHAIN,
                    {
                        "from_uuid": req_uuid,
                        "to_uuid": next_uuid,
                        "order": i + 1,
                    },
                )

        # 更新链化状态
        conn.execute(
            UPDATE_CHAIN_STATE,
            {
                "uuid": chain_state_uuid,
                "status": ChainStatus.COMPLETED.value,
                "chain_head_uuid": chain_head_uuid,
                "current_node_uuid": chain_head_uuid,
                "total_nodes": len(sorted_uuids),
                "completed_nodes": 0,
                "progress_percentage": 0,
                "last_chained_at": updated_at,
                "updated_at": updated_at,
            },
        )

        # 记录事件
        log_event(
            conn,
            project_uuid,
            "ChainBuilt",
            project_uuid,
            {
                "chain_head_uuid": chain_head_uuid,
                "total_nodes": len(sorted_uuids),
                "chain_order": sorted_uuids,
            },
        )

        result = {
            "status": "completed",
            "chain_head": chain_head_uuid,
            "total_nodes": len(sorted_uuids),
            "message": "链化构建完成",
        }

        # 缓存结果
        self._cache.set_chain_result(project_uuid, result)

        logger.info(
            f"链构建完成: {project_uuid}, 头节点: {chain_head_uuid}, 节点数: {len(sorted_uuids)}"
        )

        return result

    @performance_monitor("reset_chain")
    def reset_chain(self, conn: lb.Connection, project_uuid: str) -> Dict[str, Any]:
        """
        重置链化状态

        Args:
            conn: 数据库连接
            project_uuid: 项目 ID

        Returns:
            重置结果
        """
        # 获取所有已链化的需求
        result = conn.execute(
            GET_REQUIREMENTS_BY_STATUS,
            {"project_uuid": project_uuid, "status": RequirementStatus.CHAINED.value},
        )
        requirements = list(result)

        # 重置需求状态
        updated_at = now_utc()
        conn.execute(
            RESET_ALL_CHAIN_ORDERS,
            {"project_uuid": project_uuid, "updated_at": updated_at},
        )

        # 删除所有 NEXT_IN_CHAIN 边
        conn.execute(DELETE_ALL_NEXT_IN_CHAIN, {"project_uuid": project_uuid})

        # 重置链化状态
        conn.execute(
            RESET_CHAIN_STATE, {"project_uuid": project_uuid, "updated_at": updated_at}
        )

        # 记录事件
        log_event(
            conn,
            project_uuid,
            "ChainReset",
            project_uuid,
            {"reset_count": len(requirements)},
        )

        # 使缓存失效
        self._cache.invalidate_project(project_uuid)

        logger.info(f"链化状态重置: {project_uuid}")

        return {
            "status": "reset",
            "reset_count": len(requirements),
            "message": "链化状态已重置",
        }
