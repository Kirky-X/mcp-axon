# Copyright (c) 2026 Kirky.X. All rights reserved.
# Licensed under the MIT License.
# See LICENSE file in the project root for full license information.

"""需求状态机验证器"""

import logging
from typing import Set, Dict

from src.db.graph_models import RequirementStatus, ProjectStatus

logger = logging.getLogger(__name__)


class StateTransitionError(Exception):
    """状态转换错误"""

    def __init__(self, current: str, target: str, message: str = ""):
        self.current = current
        self.target = target
        super().__init__(message or f"不允许从 {current} 转换到 {target}")


class RequirementStateMachine:
    """
    需求状态机

    定义合法的状态转换规则，防止非法状态转换
    """

    # 定义合法的状态转换: {当前状态: {允许转换的目标状态}}
    VALID_TRANSITIONS: Dict[RequirementStatus, Set[RequirementStatus]] = {
        RequirementStatus.DRAFT: {
            RequirementStatus.DECOMPOSING,
            RequirementStatus.LEAF,
        },
        RequirementStatus.DECOMPOSING: {
            RequirementStatus.LEAF,
            RequirementStatus.DRAFT,  # 允许回到草稿重新分解
        },
        RequirementStatus.LEAF: {
            RequirementStatus.VALIDATED,
            RequirementStatus.DECOMPOSING,  # 允许重新分解
        },
        RequirementStatus.VALIDATED: {
            RequirementStatus.CHAINED,
            RequirementStatus.LEAF,  # 允许退回修改验证
        },
        RequirementStatus.CHAINED: {
            RequirementStatus.COMPLETED,
            RequirementStatus.VALIDATED,  # 允许退回重新验证
        },
        RequirementStatus.COMPLETED: set(),  # 终态，不允许任何转换
    }

    @classmethod
    def validate_transition(cls, current: str, target: str) -> bool:
        """
        验证状态转换是否合法

        Args:
            current: 当前状态
            target: 目标状态

        Returns:
            是否允许转换

        Raises:
            StateTransitionError: 如果不允许转换
        """
        try:
            current_status = RequirementStatus(current)
            target_status = RequirementStatus(target)
        except ValueError as e:
            raise StateTransitionError(current, target, f"无效的状态值: {e}")

        allowed_targets = cls.VALID_TRANSITIONS.get(current_status)
        if allowed_targets is None:
            raise StateTransitionError(current, target, f"未知的当前状态: {current}")

        if target_status not in allowed_targets:
            allowed_names = {s.value for s in allowed_targets}
            raise StateTransitionError(
                current,
                target,
                f"不允许从 {current} 转换到 {target}。"
                f"允许的目标状态: {', '.join(allowed_names) if allowed_names else '无（终态）'}",
            )

        return True

    @classmethod
    def get_allowed_transitions(cls, current: str) -> Set[str]:
        """
        获取当前状态允许的所有目标状态

        Args:
            current: 当前状态

        Returns:
            允许的目标状态集合
        """
        try:
            current_status = RequirementStatus(current)
        except ValueError:
            return set()

        allowed = cls.VALID_TRANSITIONS.get(current_status, set())
        return {s.value for s in allowed}

    @classmethod
    def is_terminal_state(cls, status: str) -> bool:
        """
        检查是否为终态

        Args:
            status: 状态值

        Returns:
            是否为终态
        """
        try:
            status_enum = RequirementStatus(status)
            return len(cls.VALID_TRANSITIONS.get(status_enum, set())) == 0
        except ValueError:
            return False


class ProjectStateMachine:
    """
    项目状态机

    定义项目生命周期的合法状态转换
    """

    VALID_TRANSITIONS: Dict[ProjectStatus, Set[ProjectStatus]] = {
        ProjectStatus.CREATED: {
            ProjectStatus.DECOMPOSING,
        },
        ProjectStatus.DECOMPOSING: {
            ProjectStatus.CHAINING,
            ProjectStatus.CREATED,  # 允许重置
        },
        ProjectStatus.CHAINING: {
            ProjectStatus.READY,
            ProjectStatus.DECOMPOSING,  # 链化失败回退
        },
        ProjectStatus.READY: {
            ProjectStatus.EXECUTING,
        },
        ProjectStatus.EXECUTING: {
            ProjectStatus.COMPLETED,
            ProjectStatus.READY,  # 允许暂停后继续
        },
        ProjectStatus.COMPLETED: set(),  # 终态
    }

    @classmethod
    def validate_transition(cls, current: str, target: str) -> bool:
        """验证项目状态转换"""
        try:
            current_status = ProjectStatus(current)
            target_status = ProjectStatus(target)
        except ValueError as e:
            raise StateTransitionError(current, target, f"无效的状态值: {e}")

        allowed_targets = cls.VALID_TRANSITIONS.get(current_status)
        if allowed_targets is None:
            raise StateTransitionError(current, target, f"未知的当前状态: {current}")

        if target_status not in allowed_targets:
            allowed_names = {s.value for s in allowed_targets}
            raise StateTransitionError(
                current,
                target,
                f"不允许项目从 {current} 转换到 {target}。"
                f"允许的目标状态: {', '.join(allowed_names) if allowed_names else '无（终态）'}",
            )

        return True
