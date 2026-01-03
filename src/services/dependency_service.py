# Copyright (c) 2026 Kirky.X. All rights reserved.
# Licensed under the MIT License.
# See LICENSE file in the project root for full license information.

"""依赖关系管理服务"""

import logging
from typing import Any, Dict, List, Optional, Set

from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from src.db.models import Requirement
from src.utils.event_logger import log_event
from src.utils.metrics import performance_monitor

logger = logging.getLogger(__name__)


class DependencyService:
    """依赖关系管理服务"""

    def __init__(self):
        """初始化依赖服务"""
        pass

    @performance_monitor("transfer_dependencies")
    def transfer_dependencies(
        self, session: Session, parent_id: str, dependency_mapping: Dict[str, List[str]]
    ) -> Dict[str, Any]:
        """
        应用依赖传递映射

        当一个父需求被分解为多个子需求时，需要将父需求的依赖关系传递给子需求。

        规则:
        - 单子需求: 自动继承父需求的所有依赖
        - 多子需求: 使用 dependency_mapping 指定每个子需求的依赖

        Args:
            session: 数据库会话
            parent_id: 父需求 ID
            dependency_mapping: 依赖映射 {子需求ID: [依赖ID列表]}

        Returns:
            操作结果
        """
        # 获取父需求
        parent = session.query(Requirement).filter_by(id=parent_id).first()
        if not parent:
            raise ValueError(f"父需求不存在: {parent_id}")

        project_id = parent.project_id

        # 获取所有子需求
        children = session.query(Requirement).filter_by(parent_id=parent_id).all()

        if not children:
            raise ValueError(f"父需求没有子需求: {parent_id}")

        children_ids = [child.id for child in children]

        # 检查映射的完整性
        for child_id in dependency_mapping.keys():
            if child_id not in children_ids:
                raise ValueError(f"映射中的子需求不存在: {child_id}")

        # 验证所有依赖 ID 存在
        all_dep_ids = set()
        for dep_ids in dependency_mapping.values():
            all_dep_ids.update(dep_ids)

        if all_dep_ids:
            existing_deps = (
                session.query(Requirement.id)
                .filter(Requirement.id.in_(all_dep_ids))
                .all()
            )
            existing_dep_ids = {dep[0] for dep in existing_deps}

            missing_deps = all_dep_ids - existing_dep_ids
            if missing_deps:
                raise ValueError(f"依赖需求不存在: {missing_deps}")

        # 应用依赖映射
        updated_children = []
        for child in children:
            if child.id in dependency_mapping:
                # 使用映射指定的依赖
                child.dependencies = dependency_mapping[child.id]
            elif len(children) == 1 and parent.dependencies:
                # 单子需求：自动继承父需求的所有依赖
                child.dependencies = parent.dependencies.copy()

            flag_modified(child, "dependencies")

            updated_children.append(
                {"child_id": child.id, "dependencies": child.dependencies}
            )

        # 记录事件
        log_event(
            session,
            project_id,
            "DependenciesTransferred",
            parent_id,
            {
                "parent_id": parent_id,
                "mapping": dependency_mapping,
                "updated_children": updated_children,
            },
        )

        session.commit()

        logger.info(f"依赖传递完成: {parent_id}")

        return {
            "parent_id": parent_id,
            "updated_children": updated_children,
            "total_children": len(children),
        }

    @performance_monitor("add_dependency")
    def add_dependency(
        self, session: Session, requirement_id: str, dependency_id: str
    ) -> Dict[str, Any]:
        """
        添加依赖关系

        Args:
            session: 数据库会话
            requirement_id: 需求 ID
            dependency_id: 依赖的需求 ID

        Returns:
            操作结果
        """
        # 获取需求
        requirement = session.query(Requirement).filter_by(id=requirement_id).first()

        if not requirement:
            raise ValueError(f"需求不存在: {requirement_id}")

        # 获取依赖需求
        dependency = session.query(Requirement).filter_by(id=dependency_id).first()

        if not dependency:
            raise ValueError(f"依赖需求不存在: {dependency_id}")

        # 检查是否属于同一项目
        if requirement.project_id != dependency.project_id:
            raise ValueError("依赖需求必须属于同一项目")

        # 检查是否自依赖
        if requirement_id == dependency_id:
            raise ValueError("不能添加自依赖")

        # 检查是否已存在
        if dependency_id in requirement.dependencies:
            raise ValueError("依赖关系已存在")

        # 检查循环依赖
        if self._would_create_cycle(session, requirement_id, dependency_id):
            raise ValueError(
                f"添加依赖会创建循环依赖: {requirement_id} -> {dependency_id}"
            )

        # 添加依赖
        requirement.dependencies.append(dependency_id)
        flag_modified(requirement, "dependencies")

        # 记录事件
        log_event(
            session,
            requirement.project_id,
            "DependencyAdded",
            requirement_id,
            {"requirement_id": requirement_id, "dependency_id": dependency_id},
        )

        session.commit()

        logger.info(f"依赖添加成功: {requirement_id} -> {dependency_id}")

        return {
            "requirement_id": requirement_id,
            "dependency_id": dependency_id,
            "dependencies": requirement.dependencies,
        }

    def remove_dependency(
        self, session: Session, requirement_id: str, dependency_id: str
    ) -> Dict[str, Any]:
        """
        移除依赖关系

        Args:
            session: 数据库会话
            requirement_id: 需求 ID
            dependency_id: 依赖的需求 ID

        Returns:
            操作结果
        """
        requirement = session.query(Requirement).filter_by(id=requirement_id).first()

        if not requirement:
            raise ValueError(f"需求不存在: {requirement_id}")

        if dependency_id not in requirement.dependencies:
            raise ValueError("依赖关系不存在")

        # 移除依赖
        requirement.dependencies.remove(dependency_id)
        flag_modified(requirement, "dependencies")

        # 记录事件
        log_event(
            session,
            requirement.project_id,
            "DependencyRemoved",
            requirement_id,
            {"requirement_id": requirement_id, "dependency_id": dependency_id},
        )

        session.commit()

        logger.info(f"依赖移除成功: {requirement_id} -> {dependency_id}")

        return {
            "requirement_id": requirement_id,
            "dependency_id": dependency_id,
            "dependencies": requirement.dependencies,
        }

    def detect_cycle(self, session: Session, project_id: str) -> Optional[List[str]]:
        """
        检测项目中的循环依赖

        Args:
            session: 数据库会话
            project_id: 项目 ID

        Returns:
            循环路径，如果没有循环则返回 None
        """
        # 获取所有需求
        requirements = session.query(Requirement).filter_by(project_id=project_id).all()

        # 构建依赖图
        graph: Dict[str, List[str]] = {}
        for req in requirements:
            graph[req.id] = req.dependencies

        # 使用 DFS 检测环路
        return self._detect_cycle_dfs(graph)

    def _would_create_cycle(
        self, session: Session, requirement_id: str, dependency_id: str
    ) -> bool:
        """
        检查添加依赖是否会创建循环依赖（优化版本）

        Args:
            session: 数据库会话
            requirement_id: 需求 ID
            dependency_id: 依赖的需求 ID

        Returns:
            是否会创建循环依赖
        """
        # 快速检查：如果两个ID相同，直接返回True
        if requirement_id == dependency_id:
            return True

        # 获取依赖需求对象
        req_obj = session.query(Requirement).filter_by(id=dependency_id).first()
        if not req_obj:
            raise ValueError(f"依赖需求不存在: {dependency_id}")

        project_id = req_obj.project_id

        # 使用优化的查询只获取需要的字段，并添加行锁防止竞态条件
        all_reqs = (
            session.query(Requirement.id, Requirement.dependencies)
            .filter_by(project_id=project_id)
            .with_for_update()
            .all()
        )

        # 构建内存中的依赖图
        dependency_graph = {req.id: req.dependencies for req in all_reqs}

        # 检查从 dependency_id 是否能到达 requirement_id
        # 使用迭代DFS避免递归栈溢出
        visited = set()
        stack = [dependency_id]

        while stack:
            current = stack.pop()
            if current == requirement_id:
                return True

            if current in visited:
                continue
            visited.add(current)

            # 获取当前节点的依赖
            dependencies = dependency_graph.get(current, [])
            stack.extend(dependencies)

        return False

    def _detect_cycle_dfs(self, graph: Dict[str, List[str]]) -> Optional[List[str]]:
        """
        使用 DFS 检测环路

        Args:
            graph: 依赖图 {node_id: [neighbor_ids]}

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
