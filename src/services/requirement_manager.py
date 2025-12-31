# Copyright (c) 2026 Kirky.X. All rights reserved.
# Licensed under the MIT License.
# See LICENSE file in the project root for full license information.

"""需求管理服务"""

import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session
from sqlalchemy import select, and_

from src.db.models import (
    Requirement, RequirementStatus, Project, ProjectStatus, Event, ValidationNode
)
from src.schemas import RequirementCreate, RequirementUpdate
from src.utils.cache import cache_manager
from src.utils.metrics import performance_monitor
from src.utils.event_logger import log_event

logger = logging.getLogger(__name__)


class RequirementManager:
    """需求管理服务"""

    def __init__(self):
        """初始化需求管理器"""
        self.cache = cache_manager

    @performance_monitor("add_requirement")
    def add_requirement(
        self,
        session: Session,
        project_id: str,
        content: str,
        parent_id: Optional[str] = None,
        order_in_parent: int = 0
    ) -> Dict[str, Any]:
        """
        添加需求节点

        Args:
            session: 数据库会话
            project_id: 项目 ID
            content: 需求内容
            parent_id: 父需求 ID（可选）
            order_in_parent: 在父需求中的顺序

        Returns:
            需求信息字典
        """
        # 验证项目存在
        project = session.query(Project).filter_by(id=project_id).first()
        if not project:
            raise ValueError(f"项目不存在: {project_id}")

        # 计算层级
        level = 0
        if parent_id:
            parent = session.query(Requirement).filter_by(id=parent_id).first()
            if not parent:
                raise ValueError(f"父需求不存在（ID: {parent_id}）。请检查父需求 ID 是否正确，或先创建父需求。")
            if parent.project_id != project_id:
                raise ValueError("父需求不属于该项目")
            level = parent.level + 1

            # 更新父需求状态为 DECOMPOSING
            if parent.status == RequirementStatus.DRAFT.value:
                parent.status = RequirementStatus.DECOMPOSING.value
                parent.updated_at = datetime.now(timezone.utc)

        # 创建需求
        requirement = Requirement(
            project_id=project_id,
            parent_id=parent_id,
            content=content,
            status=RequirementStatus.DRAFT.value,
            level=level,
            order_in_parent=order_in_parent
        )
        session.add(requirement)
        session.flush()

        # 如果是根需求（parent_id 为 None），将项目状态更新为 DECOMPOSING
        if parent_id is None and project.status == ProjectStatus.CREATED.value:
            project.status = ProjectStatus.DECOMPOSING.value
            project.updated_at = datetime.now(timezone.utc)
            logger.info(f"项目状态已更新为 DECOMPOSING: {project_id}")

        # 评估复杂度
        complexity_score = self._evaluate_complexity(content, level)
        decompose_hints = []
        needs_decomposition = False

        if complexity_score > 0.7:
            needs_decomposition = True
            decompose_hints = self._generate_decompose_hints(content, level)

        # 记录事件
        log_event(
            session,
            project_id,
            "RequirementAdded",
            requirement.id,
            {
                "content": content,
                "parent_id": parent_id,
                "level": level,
                "complexity_score": complexity_score
            }
        )

        session.commit()

        # 将新创建的需求添加到缓存
        result = {
            "requirement_id": requirement.id,
            "project_id": requirement.project_id,
            "parent_id": requirement.parent_id,
            "content": requirement.content,
            "status": requirement.status,
            "level": requirement.level,
            "complexity_score": complexity_score,
            "needs_decomposition": needs_decomposition,
            "decompose_hints": decompose_hints,
            "created_at": requirement.created_at.isoformat()
        }
        
        self.cache.set_requirement(requirement.id, result, project_id)

        logger.info(f"需求添加成功: {requirement.id} - 复杂度: {complexity_score}")

        return result

    @performance_monitor("update_requirement")
    def update_requirement(
        self,
        session: Session,
        requirement_id: str,
        update_data: RequirementUpdate
    ) -> Dict[str, Any]:
        """
        更新需求

        Args:
            session: 数据库会话
            requirement_id: 需求 ID
            update_data: 更新数据

        Returns:
            更新后的需求信息
        """
        requirement = session.query(Requirement).filter_by(
            id=requirement_id
        ).first()

        if not requirement:
            raise ValueError(f"需求不存在: {requirement_id}")

        # 如果需求已链化，不允许更新
        if requirement.status == RequirementStatus.CHAINED:
            raise ValueError("已链化的需求不允许更新")

        # 更新内容
        if update_data.content is not None:
            old_content = requirement.content
            requirement.content = update_data.content

            # 重新评估复杂度
            complexity_score = self._evaluate_complexity(
                update_data.content,
                requirement.level
            )

            log_event(
                session,
                requirement.project_id,
                "RequirementContentUpdated",
                requirement.id,
                {
                    "old_content": old_content,
                    "new_content": update_data.content,
                    "complexity_score": complexity_score
                }
            )

        # 更新状态
        if update_data.status is not None:
            old_status = requirement.status
            # 确保状态值是字符串，而不是枚举
            # 验证状态值是否是有效的需求状态
            try:
                # 尝试将字符串转换为枚举以验证其有效性
                valid_status = RequirementStatus(update_data.status)
                requirement.status = valid_status.value
            except ValueError:
                valid_statuses = [s.value for s in RequirementStatus]
                raise ValueError(
                    f"无效的需求状态: '{update_data.status}'。"
                    f"有效状态为: {', '.join(valid_statuses)}"
                )

            log_event(
                session,
                requirement.project_id,
                "RequirementStatusChanged",
                requirement.id,
                {
                    "old_status": old_status,
                    "new_status": requirement.status
                }
            )

        requirement.updated_at = datetime.now(timezone.utc)
        session.commit()

        # 使缓存失效
        self.cache.invalidate_project(requirement.project_id)
        # 直接使需求缓存失效
        self.cache.requirement_cache.invalidate(f"req_{requirement_id}")
        
        # 同时使父需求的缓存失效（如果存在）
        if requirement.parent_id:
            self.cache.requirement_cache.invalidate(f"req_{requirement.parent_id}")

        logger.info(f"需求更新成功: {requirement_id}")

        return {
            "requirement_id": requirement.id,
            "content": requirement.content,
            "status": requirement.status,
            "updated_at": requirement.updated_at.isoformat()
        }

    @performance_monitor("mark_as_leaf")
    def mark_as_leaf(
        self,
        session: Session,
        requirement_id: str
    ) -> Dict[str, Any]:
        """
        标记需求为叶子节点

        Args:
            session: 数据库会话
            requirement_id: 需求 ID

        Returns:
            需求信息
        """
        requirement = session.query(Requirement).filter_by(
            id=requirement_id
        ).first()

        if not requirement:
            raise ValueError(f"需求不存在: {requirement_id}")

        # 检查是否有子需求
        children_count = session.query(Requirement).filter_by(
            parent_id=requirement_id
        ).count()

        if children_count > 0:
            raise ValueError(
                f"需求有 {children_count} 个子需求，不能标记为叶子节点"
            )

        # 更新状态
        old_status = requirement.status
        requirement.status = RequirementStatus.LEAF.value
        requirement.updated_at = datetime.now(timezone.utc)

        # 记录事件
        log_event(
            session,
            requirement.project_id,
            "RequirementMarkedAsLeaf",
            requirement.id,
            {
                "old_status": old_status,
                "new_status": RequirementStatus.LEAF.value
            }
        )

        session.commit()

        # 使缓存失效
        self.cache.invalidate_project(requirement.project_id)
        self.cache.requirement_cache.invalidate(f"req_{requirement_id}")

        logger.info(f"需求标记为叶子节点: {requirement_id}")

        return {
            "requirement_id": requirement.id,
            "status": requirement.status,
            "updated_at": requirement.updated_at.isoformat()
        }

    @performance_monitor("delete_requirement")
    def delete_requirement(
        self,
        session: Session,
        requirement_id: str
    ) -> Dict[str, Any]:
        """
        删除需求（级联删除子需求和验证节点）

        Args:
            session: 数据库会话
            requirement_id: 需求 ID

        Returns:
            删除结果
        """
        requirement = session.query(Requirement).filter_by(
            id=requirement_id
        ).first()

        if not requirement:
            raise ValueError(f"需求不存在: {requirement_id}")

        # 检查是否已链化
        if requirement.status == RequirementStatus.CHAINED:
            raise ValueError("已链化的需求不允许删除")

        project_id = requirement.project_id

        # 统计删除数量
        children_count = session.query(Requirement).filter_by(
            parent_id=requirement_id
        ).count()

        # 删除（级联删除会自动处理子需求和验证节点）
        session.delete(requirement)

        # 记录事件
        log_event(
            session,
            project_id,
            "RequirementDeleted",
            requirement_id,
            {
                "content": requirement.content,
                "children_deleted": children_count
            }
        )

        session.commit()

        # 使缓存失效
        self.cache.invalidate_project(requirement.project_id)
        self.cache.requirement_cache.invalidate(f"req_{requirement_id}")

        logger.info(f"需求删除成功: {requirement_id}（级联删除 {children_count} 个子需求）")

        return {
            "requirement_id": requirement_id,
            "deleted": True,
            "children_deleted": children_count
        }

    @performance_monitor("get_requirement")
    def get_requirement(
        self,
        session: Session,
        requirement_id: str
    ) -> Dict[str, Any]:
        """
        获取需求信息

        Args:
            session: 数据库会话
            requirement_id: 需求 ID

        Returns:
            需求信息
        """
        # 尝试从缓存获取
        cached_req = self.cache.get_requirement(requirement_id)
        if cached_req:
            logger.debug(f"从缓存获取需求: {requirement_id}")
            return cached_req

        requirement = session.query(Requirement).filter_by(
            id=requirement_id
        ).first()

        if not requirement:
            raise ValueError(f"需求不存在: {requirement_id}")

        result = {
            "requirement_id": requirement.id,
            "project_id": requirement.project_id,
            "parent_id": requirement.parent_id,
            "content": requirement.content,
            "decompose_reason": requirement.decompose_reason,
            "status": requirement.status,
            "level": requirement.level,
            "order_in_parent": requirement.order_in_parent,
            "dependencies": requirement.dependencies,
            "chain_order": requirement.chain_order,
            "next_requirement_id": requirement.next_requirement_id,
            "created_at": requirement.created_at.isoformat(),
            "updated_at": requirement.updated_at.isoformat(),
            "version": requirement.version
        }

        # 将结果存入缓存
        self.cache.set_requirement(requirement_id, result, requirement.project_id)

        return result

    def _evaluate_complexity(self, content: str, level: int) -> float:
        """
        评估需求复杂度（优化版）

        评分规则:
        - 内容长度:
          * 50-100 字符: +0.1
          * 100-200 字符: +0.2
          * 200-500 字符: +0.3
          * > 500 字符: +0.4
        - 关键词匹配（每个 +0.1）:
          * 模块、系统、平台、管理、集成、框架、服务
          * 设计、开发、测试、部署、运维
          * 优化、重构、迁移、扩展
        - 层级:
          * 根节点 (level=0): +0.2
          * 第一层 (level=1): +0.1
        - 特殊标记:
          * 包含"多个": +0.1
          * 包含"复杂": +0.1
          * 包含"集成": +0.1

        Args:
            content: 需求内容
            level: 层级

        Returns:
            复杂度分数 [0.0, 1.0]
        """
        score = 0.0

        # 规则 1: 内容长度（更细粒度）
        content_len = len(content)
        if content_len > 500:
            score += 0.4
        elif content_len > 200:
            score += 0.3
        elif content_len > 100:
            score += 0.2
        elif content_len > 50:
            score += 0.1

        # 规则 2: 关键词检测（扩展关键词）
        complex_keywords = [
            "模块", "系统", "平台", "管理", "集成", "框架", "服务",
            "设计", "开发", "测试", "部署", "运维",
            "优化", "重构", "迁移", "扩展"
        ]
        for keyword in complex_keywords:
            if keyword in content:
                score += 0.1

        # 规则 2.5: 功能词检测
        function_keywords = ["注册", "登录", "权限", "角色", "验证", "统计", "分析", "监控"]
        for keyword in function_keywords:
            if keyword in content:
                score += 0.1

        # 规则 3: 层级判断
        if level == 0:
            score += 0.2
        elif level == 1:
            score += 0.1

        # 规则 4: 特殊标记
        if "多个" in content:
            score += 0.1
        if "复杂" in content:
            score += 0.1
        if "集成" in content:
            score += 0.1

        return min(score, 1.0)

    def _generate_decompose_hints(self, content: str, level: int) -> List[str]:
        """
        生成分解提示

        Args:
            content: 需求内容
            level: 层级

        Returns:
            分解提示列表
        """
        hints = []

        # 基于内容生成提示
        if "模块" in content:
            hints.append("建议按功能模块分解")
        if "系统" in content:
            hints.append("建议按子系统分解")
        if "平台" in content:
            hints.append("建议按平台层次分解")
        if "管理" in content:
            hints.append("建议按管理对象分解（增删改查）")
        if "集成" in content:
            hints.append("建议按集成接口分解")
        if "框架" in content:
            hints.append("建议按框架层次分解")
        if "服务" in content:
            hints.append("建议按服务功能分解")

        # 基于层级生成提示
        if level == 0:
            hints.append("根需求建议分解为 3-7 个主要子需求")
        elif level == 1:
            hints.append("子需求建议分解为具体可执行的任务")

        # 如果没有匹配关键词，提供通用提示
        if not hints:
            hints.append("建议将复杂需求分解为多个简单的可执行任务")
            hints.append("每个子需求应该可以在 1-2 天内完成")

        return hints