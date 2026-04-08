# Copyright (c) 2026 Kirky.X. All rights reserved.
# Licensed under the MIT License.
# See LICENSE file in the project root for full license information.

"""状态机定义 - 使用 transitions 库实现统一状态转换验证"""

from typing import List

from transitions import Machine

from src.db.graph_models import ProjectStatus, RequirementStatus, ChainStatus


class ProjectStateMachine:
    """项目状态机 - 定义合法的状态转换路径

    使用 transitions 库实现声明式状态机配置。
    所有状态转换必须通过触发器方法执行，确保转换合法性。

    状态流程：
    CREATED → DECOMPOSING → CHAINING → READY → EXECUTING → COMPLETED

    回退路径：
    - CHAINING/READY → DECOMPOSING (reset)
    - EXECUTING → READY (rollback)
    """

    states = [s.value for s in ProjectStatus]

    transitions = [
        # 正向流程
        {
            "trigger": "start_decompose",
            "source": "CREATED",
            "dest": "DECOMPOSING",
            "before": "_log_transition",
        },
        {
            "trigger": "start_chaining",
            "source": "DECOMPOSING",
            "dest": "CHAINING",
            "before": "_log_transition",
        },
        {
            "trigger": "chaining_done",
            "source": "CHAINING",
            "dest": "READY",
            "before": "_log_transition",
        },
        {
            "trigger": "start_execute",
            "source": "READY",
            "dest": "EXECUTING",
            "before": "_log_transition",
        },
        {
            "trigger": "complete",
            "source": "EXECUTING",
            "dest": "COMPLETED",
            "before": "_log_transition",
        },
        # 回退路径
        {
            "trigger": "reset",
            "source": ["CHAINING", "READY"],
            "dest": "DECOMPOSING",
            "before": "_log_transition",
        },
        {
            "trigger": "rollback",
            "source": "EXECUTING",
            "dest": "READY",
            "before": "_log_transition",
        },
    ]

    def __init__(self, initial_state: str = "CREATED"):
        """初始化状态机

        Args:
            initial_state: 初始状态，默认为 CREATED
        """
        self._transition_log: List[str] = []
        self.machine = Machine(
            model=self,
            states=self.states,
            transitions=self.transitions,
            initial=initial_state,
            auto_transitions=False,  # 禁止自动生成过渡
            send_event=True,  # 传递事件对象到回调
        )

    def _log_transition(self, event_data):
        """记录状态转换日志"""
        src = event_data.transition.source
        dst = event_data.transition.dest
        trigger = event_data.event.name
        self._transition_log.append(f"{trigger}: {src} → {dst}")

    def get_allowed_transitions(self) -> List[str]:
        """获取当前状态允许的触发器列表

        Returns:
            可执行的触发器名称列表
        """
        return self.machine.get_triggers(self.state)

    def can_transition_to(self, target: str) -> bool:
        """检查是否可以转换到目标状态

        Args:
            target: 目标状态

        Returns:
            是否存在合法的转换路径
        """
        for trigger in self.machine.get_triggers(self.state):
            # 检查触发器是否能到达目标状态
            for transition in self.machine.events[trigger].transitions:
                if transition.dest == target:
                    return True
        return False

    def get_transition_history(self) -> List[str]:
        """获取状态转换历史

        Returns:
            转换日志列表
        """
        return self._transition_log.copy()

    def is_final_state(self) -> bool:
        """检查是否处于最终状态

        Returns:
            当前状态是否为 COMPLETED
        """
        return self.state == "COMPLETED"

    def validate_transition(self, trigger: str) -> bool:
        """验证触发器是否可执行

        Args:
            trigger: 触发器名称

        Returns:
            触发器是否合法且可执行
        """
        return trigger in self.machine.get_triggers(self.state)


class RequirementStateMachine:
    """需求状态机 - 定义需求节点的状态转换规则

    状态流程：
    DRAFT → DECOMPOSING → LEAF → VALIDATED → CHAINED

    回退路径：
    - LEAF → DECOMPOSING (添加子需求时)
    - VALIDATED → LEAF (取消验证时)
    """

    states = [s.value for s in RequirementStatus]

    transitions = [
        # 正向流程
        {
            "trigger": "decompose",
            "source": "DRAFT",
            "dest": "DECOMPOSING",
            "before": "_log_transition",
        },
        {
            "trigger": "mark_leaf",
            "source": ["DRAFT", "DECOMPOSING"],
            "dest": "LEAF",
            "before": "_log_transition",
        },
        {
            "trigger": "validate",
            "source": "LEAF",
            "dest": "VALIDATED",
            "before": "_log_transition",
        },
        {
            "trigger": "chain",
            "source": "VALIDATED",
            "dest": "CHAINED",
            "before": "_log_transition",
        },
        # 回退路径
        {
            "trigger": "add_child",
            "source": "LEAF",
            "dest": "DECOMPOSING",
            "before": "_log_transition",
        },
        {
            "trigger": "unvalidate",
            "source": "VALIDATED",
            "dest": "LEAF",
            "before": "_log_transition",
        },
    ]

    def __init__(self, initial_state: str = "DRAFT"):
        """初始化需求状态机

        Args:
            initial_state: 初始状态，默认为 DRAFT
        """
        self._transition_log: List[str] = []
        self.machine = Machine(
            model=self,
            states=self.states,
            transitions=self.transitions,
            initial=initial_state,
            auto_transitions=False,
            send_event=True,
        )

    def _log_transition(self, event_data):
        """记录状态转换日志"""
        src = event_data.transition.source
        dst = event_data.transition.dest
        trigger = event_data.event.name
        self._transition_log.append(f"{trigger}: {src} → {dst}")

    def get_allowed_transitions(self) -> List[str]:
        """获取当前状态允许的触发器列表"""
        return self.machine.get_triggers(self.state)

    def can_transition_to(self, target: str) -> bool:
        """检查是否可以转换到目标状态"""
        for trigger in self.machine.get_triggers(self.state):
            for transition in self.machine.events[trigger].transitions:
                if transition.dest == target:
                    return True
        return False

    def is_leaf_eligible(self) -> bool:
        """检查是否可以标记为叶子节点

        Returns:
            当前状态是否允许转换到 LEAF
        """
        return self.can_transition_to("LEAF")

    def is_chainable(self) -> bool:
        """检查是否可以链化

        Returns:
            当前状态是否为 VALIDATED 或 CHAINED
        """
        return self.state in ["VALIDATED", "CHAINED"]

    def get_transition_history(self) -> List[str]:
        """获取状态转换历史"""
        return self._transition_log.copy()


class ChainStateMachine:
    """链化状态机 - 定义链化过程的状态转换

    状态流程：
    IDLE → BUILDING → COMPLETED

    回退：
    - BUILDING → IDLE (链化失败时)
    """

    states = [s.value for s in ChainStatus]

    transitions = [
        {
            "trigger": "start_building",
            "source": "IDLE",
            "dest": "BUILDING",
            "before": "_log_transition",
        },
        {
            "trigger": "complete",
            "source": "BUILDING",
            "dest": "COMPLETED",
            "before": "_log_transition",
        },
        {
            "trigger": "fail",
            "source": "BUILDING",
            "dest": "IDLE",
            "before": "_log_transition",
        },
        {
            "trigger": "reset",
            "source": "COMPLETED",
            "dest": "IDLE",
            "before": "_log_transition",
        },
    ]

    def __init__(self, initial_state: str = "IDLE"):
        """初始化链化状态机

        Args:
            initial_state: 初始状态，默认为 IDLE
        """
        self._transition_log: List[str] = []
        self.machine = Machine(
            model=self,
            states=self.states,
            transitions=self.transitions,
            initial=initial_state,
            auto_transitions=False,
            send_event=True,
        )

    def _log_transition(self, event_data):
        """记录状态转换日志"""
        src = event_data.transition.source
        dst = event_data.transition.dest
        trigger = event_data.event.name
        self._transition_log.append(f"{trigger}: {src} → {dst}")

    def is_building(self) -> bool:
        """检查是否正在构建"""
        return self.state == "BUILDING"

    def is_completed(self) -> bool:
        """检查是否已完成"""
        return self.state == "COMPLETED"


def validate_project_transition(current: str, target: str) -> bool:
    """验证项目状态转换合法性（静态方法）

    Args:
        current: 当前状态
        target: 目标状态

    Returns:
        转换是否合法
    """
    machine = ProjectStateMachine(initial_state=current)
    return machine.can_transition_to(target)


def validate_requirement_transition(current: str, target: str) -> bool:
    """验证需求状态转换合法性（静态方法）

    Args:
        current: 当前状态
        target: 目标状态

    Returns:
        转换是否合法
    """
    machine = RequirementStateMachine(initial_state=current)
    return machine.can_transition_to(target)


def get_project_allowed_transitions(current: str) -> List[str]:
    """获取项目当前状态允许的转换目标（静态方法）

    Args:
        current: 当前状态

    Returns:
        允许的目标状态列表
    """
    machine = ProjectStateMachine(initial_state=current)
    targets = []
    for trigger in machine.get_allowed_transitions():
        for transition in machine.machine.events[trigger].transitions:
            targets.append(transition.dest)
    return targets
