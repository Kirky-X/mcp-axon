# Copyright (c) 2026 Kirky.X. All rights reserved.
# Licensed under the MIT License.
# See LICENSE file in the project root for full license information.

"""优先级调度器 - 使用 heapq 实现高效的优先级队列调度"""

import heapq
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


@dataclass(order=True)
class PriorityItem:
    """优先级队列元素

    heapq 是最小堆，通过负数实现最大堆效果。
    比较顺序：priority_score -> deadline_penalty -> item（不参与比较）
    """

    priority_score: float  # 负数（使高优先级在前）
    deadline_penalty: float = field(compare=True)  # 截止时间惩罚
    item: Dict[str, Any] = field(compare=False)  # 需求数据（不参与比较）


class PriorityScheduler:
    """优先级调度器

    使用 Python 标准库 heapq 实现优先级队列，支持：
    - 显式优先级（0-9）
    - 截止时间紧急度
    - 同层节点重排序
    """

    def __init__(self):
        """初始化调度器"""
        self._queue: List[PriorityItem] = []

    def calculate_score(self, requirement: Dict[str, Any]) -> float:
        """计算综合优先级分数

        考虑因素：
        - 显式优先级（0-9，值越高越优先）
        - 截止时间紧急度（越近越紧急）

        Args:
            requirement: 需求数据字典

        Returns:
            优先级分数（负数，用于最小堆）
        """
        # 基础分数：优先级 * 10
        priority = requirement.get("priority", 0)
        base_score = priority * 10

        # 截止时间因子
        deadline = requirement.get("deadline")
        if deadline:
            try:
                hours_until = self._hours_until_deadline(deadline)
                if hours_until < 0:
                    # 已过期，最高优先级
                    base_score += 100
                elif hours_until < 24:
                    # 24小时内紧急
                    base_score += 50
                elif hours_until < 72:
                    # 3天内
                    base_score += 20
                elif hours_until < 168:
                    # 一周内
                    base_score += 10
            except (ValueError, TypeError):
                pass

        # 返回负数（heapq 是最小堆）
        return -base_score

    def calculate_deadline_penalty(self, requirement: Dict[str, Any]) -> float:
        """计算截止时间惩罚分数

        用于同优先级节点的排序。

        Args:
            requirement: 需求数据字典

        Returns:
            惩罚分数（越紧急越低）
        """
        deadline = requirement.get("deadline")
        if not deadline:
            return 0.0

        try:
            hours_until = self._hours_until_deadline(deadline)
            # 越紧急惩罚越低
            return min(hours_until, 1000)
        except (ValueError, TypeError):
            return 1000.0

    def _hours_until_deadline(self, deadline: str) -> float:
        """计算距离截止时间的小时数

        Args:
            deadline: ISO 格式截止时间

        Returns:
            小时数（负数表示已过期）
        """
        try:
            # 解析 ISO 格式时间
            if deadline.endswith("Z"):
                deadline_dt = datetime.fromisoformat(deadline.replace("Z", "+00:00"))
            else:
                deadline_dt = datetime.fromisoformat(deadline)

            now = datetime.now(timezone.utc)

            # 确保时区一致
            if deadline_dt.tzinfo is None:
                deadline_dt = deadline_dt.replace(tzinfo=timezone.utc)

            delta = deadline_dt - now
            return delta.total_seconds() / 3600
        except (ValueError, TypeError):
            return 0.0

    def push(self, requirement: Dict[str, Any]) -> None:
        """将需求加入优先级队列

        Args:
            requirement: 需求数据字典
        """
        score = self.calculate_score(requirement)
        penalty = self.calculate_deadline_penalty(requirement)
        item = PriorityItem(score, penalty, requirement)
        heapq.heappush(self._queue, item)

    def pop(self) -> Optional[Dict[str, Any]]:
        """弹出最高优先级需求

        Returns:
            需求数据字典，队列为空时返回 None
        """
        if not self._queue:
            return None
        return heapq.heappop(self._queue).item

    def peek(self) -> Optional[Dict[str, Any]]:
        """查看最高优先级需求（不移除）

        Returns:
            需求数据字典，队列为空时返回 None
        """
        if not self._queue:
            return None
        return self._queue[0].item

    def reorder_layer(self, layer_nodes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """对同层节点按优先级重排序

        用于拓扑排序后的同层节点排序。

        Args:
            layer_nodes: 同层节点列表

        Returns:
            按优先级排序后的节点列表
        """
        # 清空队列并重新填充
        self._queue.clear()
        for req in layer_nodes:
            self.push(req)

        # 按优先级弹出
        result: List[Dict[str, Any]] = []
        while self._queue:
            item = self.pop()
            if item is not None:
                result.append(item)
        return result

    def size(self) -> int:
        """获取队列大小

        Returns:
            队列中元素数量
        """
        return len(self._queue)

    def clear(self) -> None:
        """清空队列"""
        self._queue.clear()

    def is_empty(self) -> bool:
        """检查队列是否为空

        Returns:
            是否为空
        """
        return len(self._queue) == 0

    def get_top_n(self, n: int) -> List[Dict[str, Any]]:
        """获取前 N 个最高优先级需求

        Args:
            n: 数量

        Returns:
            需求列表
        """
        result = []
        for _ in range(min(n, len(self._queue))):
            item = self.pop()
            if item:
                result.append(item)
        return result

    def batch_push(self, requirements: List[Dict[str, Any]]) -> int:
        """批量添加需求

        Args:
            requirements: 需求列表

        Returns:
            添加的数量
        """
        for req in requirements:
            self.push(req)
        return len(requirements)


def sort_by_priority(requirements: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """便捷函数：按优先级排序需求列表

    Args:
        requirements: 需求列表

    Returns:
        排序后的需求列表
    """
    scheduler = PriorityScheduler()
    return scheduler.reorder_layer(requirements)
