# Copyright (c) 2026 Kirky.X. All rights reserved.
# Licensed under the MIT License.
# See LICENSE file in the project root for full license information.

"""请求限流器，防止 DoS 攻击"""

import logging
import time
from collections import defaultdict
from typing import Dict, Optional

logger = logging.getLogger(__name__)


class RateLimiter:
    """
    请求限流器（滑动窗口算法）

    用于防止 API 滥用和 DoS 攻击
    """

    def __init__(self, max_requests: int = 100, window_seconds: int = 60):
        """
        初始化限流器

        Args:
            max_requests: 时间窗口内最大请求数
            window_seconds: 时间窗口（秒）
        """
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests: Dict[str, list] = defaultdict(list)

    def is_allowed(self, identifier: str) -> bool:
        """
        检查请求是否允许

        Args:
            identifier: 唯一标识符（如会话 ID、IP 地址）

        Returns:
            是否允许请求
        """
        current_time = time.time()

        # 获取该标识符的请求历史
        request_history = self.requests[identifier]

        # 移除时间窗口外的请求
        cutoff_time = current_time - self.window_seconds
        self.requests[identifier] = [
            req_time for req_time in request_history if req_time > cutoff_time
        ]

        # 检查是否超过限制
        if len(self.requests[identifier]) >= self.max_requests:
            logger.warning(
                f"请求限流: {identifier} 在 {self.window_seconds}s 内已超过 {self.max_requests} 次请求"
            )
            return False

        # 记录当前请求
        self.requests[identifier].append(current_time)
        return True

    def get_remaining_requests(self, identifier: str) -> int:
        """
        获取剩余请求数

        Args:
            identifier: 唯一标识符

        Returns:
            剩余请求数
        """
        current_time = time.time()
        request_history = self.requests[identifier]

        # 移除时间窗口外的请求
        cutoff_time = current_time - self.window_seconds
        self.requests[identifier] = [
            req_time for req_time in request_history if req_time > cutoff_time
        ]

        return max(0, self.max_requests - len(self.requests[identifier]))

    def reset(self, identifier: Optional[str] = None) -> None:
        """
        重置限流计数

        Args:
            identifier: 唯一标识符，如果为 None 则重置所有
        """
        if identifier:
            if identifier in self.requests:
                del self.requests[identifier]
        else:
            self.requests.clear()

    def cleanup(self, max_age_seconds: int = 3600) -> None:
        """
        清理过期的请求记录

        Args:
            max_age_seconds: 最大保留时间（秒）
        """
        current_time = time.time()
        expired_identifiers = []

        for identifier, request_history in self.requests.items():
            # 检查是否有最近的请求
            if not request_history or (
                current_time - max(request_history) > max_age_seconds
            ):
                expired_identifiers.append(identifier)

        for identifier in expired_identifiers:
            del self.requests[identifier]

        if expired_identifiers:
            logger.debug(f"清理了 {len(expired_identifiers)} 个过期的限流记录")


def get_rate_limiter(max_requests: int = 100, window_seconds: int = 60) -> RateLimiter:
    """获取限流器实例（从容器获取单例）

    Args:
        max_requests: 时间窗口内最大请求数
        window_seconds: 时间窗口（秒）

    Returns:
        RateLimiter 实例
    """
    try:
        from src.core.containers import get_container

        return get_container().rate_limiter()
    except RuntimeError:
        # 容器未初始化时返回全局单例
        global _standalone_rate_limiter
        if _standalone_rate_limiter is None:
            _standalone_rate_limiter = RateLimiter(
                max_requests=max_requests, window_seconds=window_seconds
            )
        return _standalone_rate_limiter


# 全局单例（用于容器未初始化时）
_standalone_rate_limiter: Optional["RateLimiter"] = None
