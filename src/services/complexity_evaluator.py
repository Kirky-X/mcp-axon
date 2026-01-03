# Copyright (c) 2026 Kirky.X. All rights reserved.
# Licensed under the MIT License.
# See LICENSE file in the project root for full license information.

"""复杂度评估服务"""

import logging

from src.constants import ComplexityScoring

logger = logging.getLogger(__name__)


class ComplexityEvaluator:
    """复杂度评估服务"""

    def evaluate(self, content: str, level: int) -> float:
        """
        评估需求复杂度

        Args:
            content: 需求内容
            level: 需求层级

        Returns:
            复杂度分数 (0.0 - 1.0)
        """
        score = 0.0

        # 内容长度评分
        if len(content) > ComplexityScoring.CONTENT_LENGTH_THRESHOLD:
            score += ComplexityScoring.CONTENT_LENGTH_SCORE

        # 关键词评分
        keywords = ["模块", "系统", "平台", "管理", "集成", "框架", "服务"]
        for keyword in keywords:
            if keyword in content:
                score += ComplexityScoring.KEYWORD_SCORE

        # 根节点评分
        if level == 0:
            score += ComplexityScoring.ROOT_LEVEL_SCORE

        return min(score, 1.0)

    def should_decompose(self, score: float) -> bool:
        """
        判断是否应该分解

        Args:
            score: 复杂度分数

        Returns:
            是否应该分解
        """
        return score > ComplexityScoring.DECOMPOSE_THRESHOLD
