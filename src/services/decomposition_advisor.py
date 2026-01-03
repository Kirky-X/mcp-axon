# Copyright (c) 2026 Kirky.X. All rights reserved.
# Licensed under the MIT License.
# See LICENSE file in the project root for full license information.

"""分解建议服务"""

import logging
from typing import List

logger = logging.getLogger(__name__)


class DecompositionAdvisor:
    """分解建议服务"""

    def generate_hints(self, content: str, level: int) -> List[str]:
        """
        生成分解建议

        Args:
            content: 需求内容
            level: 需求层级

        Returns:
            建议列表
        """
        hints = []

        # 基于内容生成建议
        if "模块" in content:
            hints.append("建议按功能模块分解")
        if "系统" in content:
            hints.append("建议按子系统分解")
        if "平台" in content:
            hints.append("建议按平台层次分解")
        if "管理" in content:
            hints.append("建议按管理对象分解")
        if "集成" in content:
            hints.append("建议按集成接口分解")
        if "框架" in content:
            hints.append("建议按框架层次分解")
        if "服务" in content:
            hints.append("建议按服务功能分解")

        # 基于层级生成建议
        if level == 0:
            hints.append("根需求建议分解为 3-7 个主要子需求")
        elif level == 1:
            hints.append("子需求建议分解为具体可执行的任务")
        elif level == 2:
            hints.append("孙需求建议分解为具体的验收标准")

        # 如果没有匹配关键词，提供通用建议
        if not hints:
            hints.append("建议将复杂需求分解为多个简单的可执行任务")
            hints.append("每个子需求应该可以在 1-2 天内完成")

        return hints
