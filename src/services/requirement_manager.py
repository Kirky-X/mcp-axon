# Copyright (c) 2026 Kirky.X. All rights reserved.
# Licensed under the MIT License.
# See LICENSE file in the project root for full license information.

"""需求管理服务"""

import logging
import uuid
from typing import Any

import real_ladybug as lb

from src.constants import Chain, ComplexityScoring, Limits
from src.db.graph_models import (
    ProjectStatus,
    RequirementStatus,
    now_utc,
)
from src.db.graph_queries import (
    CREATE_HAS_CHILD,
    CREATE_HAS_REQUIREMENT,
    CREATE_REQUIREMENT,
    DELETE_REQUIREMENT,
    GET_CHILDREN,
    GET_INCOMING_DEPENDENCIES_DETAILS,
    GET_PROJECT_BY_UUID,
    GET_REQUIREMENT_BY_UUID,
    GET_REQUIREMENT_CHAIN_INFO,
    GET_REQUIREMENTS_BY_PARENT,
    GET_REQUIREMENTS_BY_PROJECT,
    GET_REQUIREMENTS_BY_STATUS,
    UPDATE_PROJECT_STATUS,
    UPDATE_REQUIREMENT,
    UPDATE_REQUIREMENT_STATUS,
)
from src.schemas import RequirementUpdate
from src.services.complexity_evaluator import ComplexityEvaluator
from src.services.decomposition_advisor import DecompositionAdvisor
from src.utils.cache import CacheManager
from src.utils.event_logger import log_event
from src.utils.input_validator import InputValidator
from src.utils.metrics import performance_monitor
from src.utils.state_machine import RequirementStateMachine, StateTransitionError

logger = logging.getLogger(__name__)


class RequirementManager:
    """需求管理服务"""

    def __init__(
        self,
        cache: CacheManager,
        complexity_evaluator: ComplexityEvaluator,
        decomposition_advisor: DecompositionAdvisor,
    ):
        """
        初始化需求管理器

        Args:
            cache: 缓存管理器实例
            complexity_evaluator: 复杂度评估器实例
            decomposition_advisor: 分解建议器实例
        """
        self.cache = cache
        self.complexity_evaluator = complexity_evaluator
        self.decomposition_advisor = decomposition_advisor

    @performance_monitor("add_requirement")
    def add_requirement(
        self,
        conn: lb.Connection,
        project_uuid: str,
        content: str,
        parent_uuid: str | None = None,
        order_in_parent: int = 0,
    ) -> dict[str, Any]:
        """
        添加需求节点

        Args:
            conn: 数据库连接
            project_uuid: 项目 ID
            content: 需求内容
            parent_uuid: 父需求 ID（可选）
            order_in_parent: 在父需求中的顺序

        Returns:
            需求信息字典
        """
        # 验证需求内容
        content = InputValidator.validate_requirement_content(content)

        # 验证项目存在
        result = conn.execute(GET_PROJECT_BY_UUID, {"uuid": project_uuid})
        project_rows = list(result)
        if not project_rows:
            raise ValueError(f"项目不存在: {project_uuid}")

        project = project_rows[0]
        project_status = project[3]  # status

        # 计算层级
        level = 0
        if parent_uuid:
            result = conn.execute(GET_REQUIREMENT_BY_UUID, {"uuid": parent_uuid})
            parent_rows = list(result)
            if not parent_rows:
                raise ValueError(
                    f"父需求不存在（ID: {parent_uuid}）。请检查父需求 ID 是否正确，或先创建父需求。"
                )
            parent = parent_rows[0]
            parent_project_uuid = parent[1]  # project_uuid
            if parent_project_uuid != project_uuid:
                raise ValueError("父需求不属于该项目")
            level = parent[6] + 1  # level

            # 检查深度限制
            if level > Limits.MAX_DEPTH:
                raise ValueError(
                    f"需求层级超过限制（当前: {level}, 最大: {Limits.MAX_DEPTH}）。"
                    f"无法继续分解，请考虑重新组织需求结构。"
                )

            # 如果父节点是叶子节点，取消其叶子状态
            parent_status = parent[5]  # status
            if parent_status == RequirementStatus.LEAF.value:
                old_status = parent_status
                conn.execute(
                    UPDATE_REQUIREMENT_STATUS,
                    {
                        "uuid": parent_uuid,
                        "status": RequirementStatus.DECOMPOSING.value,
                        "updated_at": now_utc(),
                    },
                )

                # 使父节点缓存失效
                self.cache.invalidate_requirement(parent_uuid, project_uuid)
                self.cache.invalidate_project(project_uuid)

                # 记录父节点状态变更事件
                log_event(
                    conn,
                    project_uuid,
                    "ParentStatusChanged",
                    parent_uuid,
                    {
                        "old_status": old_status,
                        "new_status": RequirementStatus.DECOMPOSING.value,
                        "child_requirement_uuid": None,
                    },
                )

        # 创建需求节点（初始状态为 DRAFT，符合状态机约定）
        requirement_uuid = str(uuid.uuid4())
        created_at = now_utc()

        conn.execute(
            CREATE_REQUIREMENT,
            {
                "uuid": requirement_uuid,
                "project_uuid": project_uuid,
                "parent_uuid": parent_uuid or "",
                "content": content,
                "decompose_reason": "",
                "status": RequirementStatus.DRAFT.value,  # 初始状态为 DRAFT
                "level": level,
                "order_in_parent": order_in_parent,
                "chain_order": -1,  # NULL
                "created_at": created_at,
                "updated_at": created_at,
                "version": 1,
            },
        )

        # 创建 HAS_REQUIREMENT 边
        conn.execute(
            CREATE_HAS_REQUIREMENT,
            {"project_uuid": project_uuid, "requirement_uuid": requirement_uuid},
        )

        # 如果有父需求，创建 HAS_CHILD 边
        if parent_uuid:
            conn.execute(
                CREATE_HAS_CHILD,
                {
                    "parent_uuid": parent_uuid,
                    "child_uuid": requirement_uuid,
                    "order": order_in_parent,
                },
            )

        # 如果是根需求，将项目状态更新为 DECOMPOSING
        if parent_uuid is None and project_status == ProjectStatus.CREATED.value:
            conn.execute(
                UPDATE_PROJECT_STATUS,
                {
                    "uuid": project_uuid,
                    "status": ProjectStatus.DECOMPOSING.value,
                    "updated_at": now_utc(),
                },
            )
            logger.info(f"项目状态已更新为 DECOMPOSING: {project_uuid}")

        # 评估复杂度
        complexity_score = self._evaluate_complexity(content, level)
        decompose_hints = []
        needs_decomposition = False
        current_status = RequirementStatus.DRAFT.value

        if complexity_score > ComplexityScoring.DECOMPOSE_THRESHOLD:
            needs_decomposition = True
            decompose_hints = self._generate_decompose_hints(content, level)
            # 触发分解状态转换
            current_status = RequirementStatus.DECOMPOSING.value
            conn.execute(
                UPDATE_REQUIREMENT_STATUS,
                {
                    "uuid": requirement_uuid,
                    "status": RequirementStatus.DECOMPOSING.value,
                    "updated_at": now_utc(),
                },
            )
            logger.info(
                f"需求复杂度 {complexity_score:.2f} 超过阈值 {ComplexityScoring.DECOMPOSE_THRESHOLD}，"
                f"自动触发分解流程: {requirement_uuid}"
            )
        else:
            # 低复杂度需求直接标记为叶子节点
            current_status = RequirementStatus.LEAF.value
            conn.execute(
                UPDATE_REQUIREMENT_STATUS,
                {
                    "uuid": requirement_uuid,
                    "status": RequirementStatus.LEAF.value,
                    "updated_at": now_utc(),
                },
            )

        # 记录事件
        log_event(
            conn,
            project_uuid,
            "RequirementAdded",
            requirement_uuid,
            {
                "content": content,
                "parent_uuid": parent_uuid,
                "level": level,
                "complexity_score": complexity_score,
                "initial_status": current_status,
            },
        )

        # 将新创建的需求添加到缓存
        result = {
            "requirement_id": requirement_uuid,
            "project_id": project_uuid,
            "parent_id": parent_uuid,
            "content": content,
            "status": current_status,
            "level": level,
            "complexity_score": complexity_score,
            "needs_decomposition": needs_decomposition,
            "decompose_hints": decompose_hints,
            "created_at": created_at,
        }

        self.cache.set_requirement(requirement_uuid, result, project_uuid)

        logger.info(f"需求添加成功: {requirement_uuid} - 复杂度: {complexity_score}")

        return result

    @performance_monitor("update_requirement")
    def update_requirement(
        self, conn: lb.Connection, requirement_uuid: str, update_data: RequirementUpdate
    ) -> dict[str, Any]:
        """
        更新需求

        Args:
            conn: 数据库连接
            requirement_uuid: 需求 ID
            update_data: 更新数据

        Returns:
            更新后的需求信息
        """
        result = conn.execute(GET_REQUIREMENT_BY_UUID, {"uuid": requirement_uuid})
        rows = list(result)
        if not rows:
            raise ValueError(f"需求不存在: {requirement_uuid}")

        requirement = rows[0]
        project_uuid = requirement[1]  # project_uuid
        current_status = requirement[5]  # status
        current_content = requirement[3]  # content
        level = requirement[6]  # level

        # 如果需求已链化，不允许更新
        if current_status == RequirementStatus.CHAINED.value:
            raise ValueError("已链化的需求不允许更新")

        # 更新内容
        if update_data.content is not None:
            old_content = current_content

            # 重新评估复杂度
            complexity_score = self._evaluate_complexity(update_data.content, level)

            log_event(
                conn,
                project_uuid,
                "RequirementContentUpdated",
                requirement_uuid,
                {
                    "old_content": old_content,
                    "new_content": update_data.content,
                    "complexity_score": complexity_score,
                },
            )

        # 更新状态
        if update_data.status is not None:
            old_status = current_status
            # 验证状态值是否是有效的需求状态
            try:
                RequirementStatus(update_data.status)
            except ValueError:
                valid_statuses = [s.value for s in RequirementStatus]
                raise ValueError(
                    f"无效的需求状态: '{update_data.status}'。"
                    f"有效状态为: {', '.join(valid_statuses)}"
                )

            # 使用状态机验证状态转换
            try:
                RequirementStateMachine.validate_transition(
                    current_status, update_data.status
                )
            except StateTransitionError as e:
                raise ValueError(str(e))

            log_event(
                conn,
                project_uuid,
                "RequirementStatusChanged",
                requirement_uuid,
                {"old_status": old_status, "new_status": update_data.status},
            )

        # 执行更新
        conn.execute(
            UPDATE_REQUIREMENT,
            {
                "uuid": requirement_uuid,
                "content": update_data.content or current_content,
                "decompose_reason": requirement[4] or "",  # 保持原值
                "status": update_data.status or current_status,
                "updated_at": now_utc(),
            },
        )

        # 使缓存失效
        self.cache.invalidate_requirement(requirement_uuid, project_id=project_uuid)

        logger.info(f"需求更新成功: {requirement_uuid}")

        return {
            "requirement_id": requirement_uuid,
            "content": update_data.content or current_content,
            "status": update_data.status or current_status,
            "updated_at": now_utc(),
        }

    @performance_monitor("delete_requirement")
    def delete_requirement(
        self, conn: lb.Connection, requirement_uuid: str
    ) -> dict[str, Any]:
        """
        删除需求（级联删除子需求和验证节点）

        Args:
            conn: 数据库连接
            requirement_uuid: 需求 ID

        Returns:
            删除结果

        Raises:
            ValueError: 需求不存在、已链化、被依赖或在执行链中
        """
        result = conn.execute(GET_REQUIREMENT_BY_UUID, {"uuid": requirement_uuid})
        rows = list(result)
        if not rows:
            raise ValueError(f"需求不存在: {requirement_uuid}")

        requirement = rows[0]
        project_uuid = requirement[1]  # project_uuid
        current_status = requirement[5]  # status
        content = requirement[3]  # content

        # 检查是否已链化
        if current_status == RequirementStatus.CHAINED.value:
            raise ValueError("已链化的需求不允许删除")

        # 新增：检查是否有入边依赖（被其他需求依赖）
        incoming_deps = self._check_incoming_dependencies(conn, requirement_uuid)
        if incoming_deps:
            dep_details = ", ".join(
                [f"{d['uuid']} ({d['content'][:30]}...)" for d in incoming_deps[:5]]
            )
            raise ValueError(f"无法删除：被以下需求依赖 [{dep_details}]")

        # 新增：检查是否在执行链中
        chain_info = self._check_chain_position(conn, requirement_uuid)
        if chain_info and chain_info.get("chain_order") is not None:
            raise ValueError(
                f"无法删除：需求在执行链中（位置: {chain_info['chain_order']}）"
            )

        # 统计子需求数量
        children_result = conn.execute(GET_CHILDREN, {"parent_uuid": requirement_uuid})
        children_count = len(list(children_result))

        # 删除（DETACH DELETE 会级联删除所有关系和相关节点）
        conn.execute(DELETE_REQUIREMENT, {"uuid": requirement_uuid})

        # 记录事件
        log_event(
            conn,
            project_uuid,
            "RequirementDeleted",
            requirement_uuid,
            {"content": content, "children_deleted": children_count},
        )

        # 使缓存失效
        self.cache.invalidate_requirement(requirement_uuid, project_id=project_uuid)

        logger.info(
            f"需求删除成功: {requirement_uuid}（级联删除 {children_count} 个子需求）"
        )

        return {
            "requirement_id": requirement_uuid,
            "deleted": True,
            "children_deleted": children_count,
        }

    @performance_monitor("get_requirement")
    def get_requirement(
        self, conn: lb.Connection, requirement_uuid: str
    ) -> dict[str, Any]:
        """
        获取需求信息

        Args:
            conn: 数据库连接
            requirement_uuid: 需求 ID

        Returns:
            需求信息
        """
        # 尝试从缓存获取
        cached_req = self.cache.get_requirement(requirement_uuid)
        if cached_req:
            logger.debug(f"从缓存获取需求: {requirement_uuid}")
            return cached_req

        result = conn.execute(GET_REQUIREMENT_BY_UUID, {"uuid": requirement_uuid})
        rows = list(result)
        if not rows:
            raise ValueError(f"需求不存在: {requirement_uuid}")

        row = rows[0]
        req_result = {
            "requirement_id": row[0],  # uuid
            "project_id": row[1],  # project_uuid
            "parent_id": row[2] if row[2] else None,  # parent_uuid
            "content": row[3],  # content
            "decompose_reason": row[4] if row[4] else None,  # decompose_reason
            "status": row[5],  # status
            "level": row[6],  # level
            "order_in_parent": row[7],  # order_in_parent
            "chain_order": row[8] if row[8] != -1 else None,  # chain_order
            "parallel_group": row[9] if row[9] is not None else None,  # parallel_group
            "created_at": row[10],  # created_at
            "updated_at": row[11],  # updated_at
            "version": row[12] if len(row) > 12 else 1,  # version
            "dependencies": row[13]
            if len(row) > 13 and row[13]
            else [],  # dependencies
            "next_requirement_id": row[14]
            if len(row) > 14 and row[14]
            else None,  # next_requirement_uuid
        }

        # 将结果存入缓存
        self.cache.set_requirement(requirement_uuid, req_result, row[1])

        return req_result

    def _evaluate_complexity(self, content: str, level: int) -> float:
        """
        评估需求复杂度（使用 ComplexityEvaluator 服务）

        Args:
            content: 需求内容
            level: 层级

        Returns:
            复杂度分数 [0.0, 1.0]
        """
        return self.complexity_evaluator.evaluate(content, level)

    def _generate_decompose_hints(self, content: str, level: int) -> list[str]:
        """
        生成分解提示（使用 DecompositionAdvisor 服务）

        Args:
            content: 需求内容
            level: 层级

        Returns:
            分解提示列表
        """
        return self.decomposition_advisor.generate_hints(content, level)

    def _check_incoming_dependencies(
        self, conn: lb.Connection, requirement_uuid: str
    ) -> list[dict[str, str]]:
        """
        检查需求是否被其他需求依赖（入边依赖检查）

        Args:
            conn: 数据库连接
            requirement_uuid: 需求 ID

        Returns:
            依赖此需求的需求数据列表，无依赖时返回空列表
        """
        result = conn.execute(
            GET_INCOMING_DEPENDENCIES_DETAILS, {"requirement_uuid": requirement_uuid}
        )
        rows = list(result)
        dependencies = []
        for row in rows:
            dependencies.append(
                {
                    "uuid": row[0],
                    "content": row[1],
                    "status": row[2],
                }
            )
        return dependencies

    def _check_chain_position(
        self, conn: lb.Connection, requirement_uuid: str
    ) -> dict[str, Any] | None:
        """
        检查需求是否在执行链中

        Args:
            conn: 数据库连接
            requirement_uuid: 需求 ID

        Returns:
            链信息字典，不在链中时返回 None
        """
        result = conn.execute(
            GET_REQUIREMENT_CHAIN_INFO, {"requirement_uuid": requirement_uuid}
        )
        rows = list(result)
        if not rows:
            return None

        row = rows[0]
        chain_order = row[0]
        prev_uuid = row[1]
        next_uuid = row[2]

        # 如果 chain_order 不为空，或者有 prev/next 节点，说明在链中
        if chain_order is not None and chain_order >= 0:
            return {
                "chain_order": chain_order,
                "prev_uuid": prev_uuid,
                "next_uuid": next_uuid,
            }

        # 如果有前驱或后继节点，也在链中
        if prev_uuid or next_uuid:
            return {
                "chain_order": chain_order,
                "prev_uuid": prev_uuid,
                "next_uuid": next_uuid,
            }

        return None

    @performance_monitor("batch_add_requirements")
    def batch_add_requirements(
        self,
        conn: lb.Connection,
        project_uuid: str,
        requirements: list[dict[str, Any]],
        parent_uuid: str | None = None,
    ) -> dict[str, Any]:
        """
        批量添加需求（带事务保护）

        使用补偿机制确保数据一致性：如果某个需求创建失败，
        会回滚已创建的所有需求。

        Args:
            conn: 数据库连接
            project_uuid: 项目 ID
            requirements: 需求列表，每个元素包含 content 和可选的 order_in_parent
            parent_uuid: 父需求 ID（可选）

        Returns:
            批量操作结果
        """
        created_requirements: list[dict[str, Any]] = []
        failed_requirements: list[dict[str, Any]] = []
        created_uuids: list[str] = []  # 记录已创建的 UUID 用于回滚

        # 限制批量大小
        batch_size = min(len(requirements), Chain.DEFAULT_BATCH_SIZE)

        # 验证项目存在
        result = conn.execute(GET_PROJECT_BY_UUID, {"uuid": project_uuid})
        if not list(result):
            raise ValueError(f"项目不存在: {project_uuid}")

        # 如果有父需求，验证父需求存在并获取层级
        parent_level = 0
        if parent_uuid:
            result = conn.execute(GET_REQUIREMENT_BY_UUID, {"uuid": parent_uuid})
            parent_rows = list(result)
            if not parent_rows:
                raise ValueError(f"父需求不存在: {parent_uuid}")
            if parent_rows[0][1] != project_uuid:
                raise ValueError("父需求不属于当前项目")
            parent_level = parent_rows[0][6] + 1  # level + 1

            # 检查深度限制
            if parent_level > Limits.MAX_DEPTH:
                raise ValueError(
                    f"需求层级超过限制（当前: {parent_level}, 最大: {Limits.MAX_DEPTH}）。"
                    f"无法继续分解。"
                )

        def rollback_created():
            """回滚已创建的需求"""
            for uuid_to_delete in created_uuids:
                try:
                    conn.execute(DELETE_REQUIREMENT, {"uuid": uuid_to_delete})
                    logger.info(f"回滚删除需求: {uuid_to_delete}")
                except Exception as e:
                    logger.error(f"回滚失败 {uuid_to_delete}: {e}")

        # 批量创建需求
        for i, req_data in enumerate(requirements[:batch_size]):
            try:
                content = req_data.get("content", "").strip()
                if not content:
                    raise ValueError("需求内容不能为空")

                order = req_data.get("order_in_parent", i)
                level = parent_level if parent_uuid else 0

                # 评估复杂度
                complexity_score = self._evaluate_complexity(content, level)

                # 根据复杂度决定初始状态
                needs_decomp = self.complexity_evaluator.should_decompose(
                    complexity_score
                )
                initial_status = (
                    RequirementStatus.DECOMPOSING.value
                    if needs_decomp
                    else RequirementStatus.LEAF.value
                )

                # 创建需求（初始状态为 DRAFT 或 DECOMPOSING）
                req_uuid = str(uuid.uuid4())
                created_at = now_utc()

                conn.execute(
                    CREATE_REQUIREMENT,
                    {
                        "uuid": req_uuid,
                        "project_uuid": project_uuid,
                        "parent_uuid": parent_uuid or "",
                        "content": content,
                        "decompose_reason": "",
                        "status": initial_status,
                        "level": level,
                        "order_in_parent": order,
                        "chain_order": -1,
                        "created_at": created_at,
                        "updated_at": created_at,
                        "version": 1,
                    },
                )

                # 记录已创建的 UUID（在创建边之前）
                created_uuids.append(req_uuid)

                # 创建边
                conn.execute(
                    CREATE_HAS_REQUIREMENT,
                    {"project_uuid": project_uuid, "requirement_uuid": req_uuid},
                )

                if parent_uuid:
                    conn.execute(
                        CREATE_HAS_CHILD,
                        {
                            "parent_uuid": parent_uuid,
                            "child_uuid": req_uuid,
                            "order": order,
                        },
                    )

                result_item = {
                    "requirement_id": req_uuid,
                    "project_id": project_uuid,
                    "parent_id": parent_uuid,
                    "content": content,
                    "status": RequirementStatus.LEAF.value,
                    "level": level,
                    "order_in_parent": order,
                    "dependencies": [],
                    "complexity_score": complexity_score,
                    "needs_decomposition": self.complexity_evaluator.should_decompose(
                        complexity_score
                    ),
                    "decompose_hints": self.decomposition_advisor.generate_hints(
                        content, level
                    ),
                    "created_at": created_at,
                    "updated_at": created_at,
                }
                created_requirements.append(result_item)

                # 记录事件
                log_event(
                    conn,
                    project_uuid,
                    "RequirementCreated",
                    req_uuid,
                    {"content": content, "level": level},
                )

            except Exception as e:
                logger.error(f"批量添加需求失败（索引 {i}）: {e}")
                failed_requirements.append({"index": i, "error": str(e)})

                # 执行回滚
                logger.warning(f"开始回滚已创建的 {len(created_uuids)} 个需求")
                rollback_created()

                # 使缓存失效
                self.cache.invalidate_project(project_uuid)

                # 返回失败结果
                return {
                    "total": len(requirements),
                    "success": 0,
                    "failed": len(failed_requirements),
                    "created": [],
                    "failed_details": failed_requirements,
                    "rolled_back": True,
                    "rolled_back_count": len(created_uuids),
                }

        # 全部成功，使缓存失效
        self.cache.invalidate_project(project_uuid)

        return {
            "total": len(requirements),
            "success": len(created_requirements),
            "failed": len(failed_requirements),
            "created": created_requirements,
            "failed_details": failed_requirements,
            "rolled_back": False,
        }

    @performance_monitor("batch_update_requirements")
    def batch_update_requirements(
        self,
        conn: lb.Connection,
        updates: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """
        批量更新需求

        Args:
            conn: 数据库连接
            updates: 更新列表，每个元素包含 requirement_id 和可选的 content、status

        Returns:
            批量操作结果
        """
        updated_requirements = []
        failed_requirements = []

        for update_data in updates:
            try:
                # 创建 RequirementUpdate 对象
                update_obj = RequirementUpdate(
                    content=update_data.get("content"),
                    status=update_data.get("status"),
                )
                result = self.update_requirement(
                    conn=conn,
                    requirement_uuid=update_data["requirement_id"],
                    update_data=update_obj,
                )
                updated_requirements.append(result)
            except Exception as e:
                logger.error(f"批量更新需求失败: {e}")
                failed_requirements.append(
                    {
                        "requirement_id": update_data.get("requirement_id"),
                        "error": str(e),
                    }
                )

        return {
            "total": len(updates),
            "success": len(updated_requirements),
            "failed": len(failed_requirements),
            "updated": updated_requirements,
            "failed_details": failed_requirements,
        }

    def list_requirements(
        self,
        conn: lb.Connection,
        project_uuid: str,
        status: str | None = None,
        is_leaf: bool | None = None,
        parent_uuid: str | None = None,
    ) -> dict[str, Any]:
        """
        列出项目的所有需求

        Args:
            conn: 数据库连接
            project_uuid: 项目 ID
            status: 按状态过滤（可选）
            is_leaf: 是否只返回叶子节点（可选）
            parent_uuid: 父需求 ID（可选，只返回直接子需求）

        Returns:
            需求列表
        """
        # 验证项目存在
        result = conn.execute(GET_PROJECT_BY_UUID, {"uuid": project_uuid})
        if not list(result):
            raise ValueError(f"项目不存在: {project_uuid}")

        # 根据过滤条件选择查询
        if parent_uuid:
            # 验证 parent_uuid 属于该项目
            parent_result = conn.execute(GET_REQUIREMENT_BY_UUID, {"uuid": parent_uuid})
            parent_rows = list(parent_result)
            if parent_rows:
                parent_project_uuid = parent_rows[0][1]
                if parent_project_uuid != project_uuid:
                    raise ValueError(f"父需求不属于该项目: {parent_uuid}")

            result = conn.execute(
                GET_REQUIREMENTS_BY_PARENT, {"parent_uuid": parent_uuid}
            )
            # 过滤：只返回属于该项目的子需求
            requirements = [r for r in list(result) if r[1] == project_uuid]
        elif status:
            result = conn.execute(
                GET_REQUIREMENTS_BY_STATUS,
                {"project_uuid": project_uuid, "status": status},
            )
            requirements = list(result)
        else:
            result = conn.execute(
                GET_REQUIREMENTS_BY_PROJECT, {"project_uuid": project_uuid}
            )
            requirements = list(result)

        # 过滤叶子节点
        if is_leaf is not None:
            if is_leaf:
                requirements = [
                    r for r in requirements if r[5] == RequirementStatus.LEAF.value
                ]
            else:
                requirements = [
                    r for r in requirements if r[5] != RequirementStatus.LEAF.value
                ]

        # 构建返回结果
        requirement_list = [
            {
                "id": req[0],  # uuid
                "content": req[3],  # content
                "status": req[5],  # status
                "level": req[6],  # level
                "parent_id": req[2] if req[2] else None,  # parent_uuid
                "order_in_parent": req[7],  # order_in_parent
                "created_at": req[9],  # created_at
                "updated_at": req[10],  # updated_at
            }
            for req in requirements
        ]

        return {
            "project_id": project_uuid,
            "total": len(requirement_list),
            "requirements": requirement_list,
        }

    def mark_as_leaf(
        self, conn: lb.Connection, requirement_uuid: str
    ) -> dict[str, Any]:
        """
        将需求标记为叶子节点

        Args:
            conn: 数据库连接
            requirement_uuid: 需求 ID

        Returns:
            操作结果

        Raises:
            ValueError: 需求不存在、存在子需求、或已经是叶子节点
        """
        result = conn.execute(GET_REQUIREMENT_BY_UUID, {"uuid": requirement_uuid})
        rows = list(result)
        if not rows:
            raise ValueError(f"需求不存在: {requirement_uuid}")

        requirement = rows[0]
        project_uuid = requirement[1]  # project_uuid
        current_status = requirement[5]  # status

        # 如果已经是叶子节点，直接返回成功
        if current_status == RequirementStatus.LEAF.value:
            logger.info(f"需求已是叶子节点: {requirement_uuid}")
            return {
                "requirement_id": requirement_uuid,
                "status": current_status,
                "message": "该需求已经是叶子节点",
                "next_action": "manage_validation",
            }

        # 检查是否存在子需求
        children_result = conn.execute(GET_CHILDREN, {"parent_uuid": requirement_uuid})
        children_count = len(list(children_result))

        if children_count > 0:
            raise ValueError(
                f"该需求存在子需求，无法标记为叶子节点（子需求数量: {children_count}）。"
                f"请先处理所有子需求。"
            )

        # 更新状态为 LEAF
        old_status = current_status
        conn.execute(
            UPDATE_REQUIREMENT_STATUS,
            {
                "uuid": requirement_uuid,
                "status": RequirementStatus.LEAF.value,
                "updated_at": now_utc(),
            },
        )

        # 记录事件
        log_event(
            conn,
            project_uuid,
            "RequirementMarkedAsLeaf",
            requirement_uuid,
            {
                "old_status": old_status,
                "new_status": RequirementStatus.LEAF.value,
            },
        )

        # 使缓存失效
        self.cache.invalidate_requirement(requirement_uuid, project_id=project_uuid)
        self.cache.invalidate_project(project_uuid)

        logger.info(f"需求已标记为叶子节点: {requirement_uuid} ({old_status} -> LEAF)")

        return {
            "requirement_id": requirement_uuid,
            "status": RequirementStatus.LEAF.value,
            "message": "需求已标记为叶子节点，请配置验证节点",
            "next_action": "manage_validation",
        }
