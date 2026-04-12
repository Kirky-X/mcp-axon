# Copyright (c) 2026 Kirky.X. All rights reserved.
# Licensed under the MIT License.
# See LICENSE file in the project root for full license information.

"""请求限流器，防止 DoS 攻击"""

import logging
import threading
import time
from collections import deque
from typing import Dict, Optional

logger = logging.getLogger(__name__)

# 最大独立标识符数量，防止恶意枚举耗尽内存
_MAX_IDENTIFIERS = 5000


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
        self.requests: Dict[str, deque] = {}
        self._lock = threading.Lock()

    def is_allowed(self, identifier: str) -> bool:
        """
        检查请求是否允许

        Args:
            identifier: 唯一标识符（如会话 ID、IP 地址）

        Returns:
            是否允许请求
        """
        current_time = time.time()
        cutoff_time = current_time - self.window_seconds

        with self._lock:
            # 防御性限制：标识符数量上限
            if (
                identifier not in self.requests
                and len(self.requests) >= _MAX_IDENTIFIERS
            ):
                self._evict_expired_identifiers(current_time)
                if len(self.requests) >= _MAX_IDENTIFIERS:
                    # 强制移除最早的标识符
                    oldest = next(iter(self.requests))
                    del self.requests[oldest]

            if identifier not in self.requests:
                self.requests[identifier] = deque()

            request_history = self.requests[identifier]

            # 移除时间窗口外的请求
            while request_history and request_history[0] <= cutoff_time:
                request_history.popleft()

            # 检查是否超过限制
            if len(request_history) >= self.max_requests:
                logger.warning(
                    f"请求限流: {identifier} 在 {self.window_seconds}s 内已超过 {self.max_requests} 次请求"
                )
                return False

            # 记录当前请求
            request_history.append(current_time)
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
        cutoff_time = current_time - self.window_seconds

        with self._lock:
            request_history = self.requests.get(identifier)
            if not request_history:
                return self.max_requests

            # 移除时间窗口外的请求
            while request_history and request_history[0] <= cutoff_time:
                request_history.popleft()

            return max(0, self.max_requests - len(request_history))

    def reset(self, identifier: Optional[str] = None) -> None:
        """
        重置限流计数

        Args:
            identifier: 唯一标识符，如果为 None 则重置所有
        """
        with self._lock:
            if identifier:
                self.requests.pop(identifier, None)
            else:
                self.requests.clear()

    def cleanup(self, max_age_seconds: int = 3600) -> None:
        """
        清理过期的请求记录

        Args:
            max_age_seconds: 最大保留时间（秒）
        """
        with self._lock:
            self._evict_expired_identifiers(time.time(), max_age_seconds)

    def _evict_expired_identifiers(
        self, current_time: float, max_age: float | None = None
    ) -> None:
        """在持有锁时调用，移除所有过期的标识符"""
        threshold = max_age if max_age is not None else self.window_seconds
        expired = [
            ident
            for ident, history in self.requests.items()
            if not history or (current_time - history[-1] > threshold)
        ]
        for ident in expired:
            del self.requests[ident]
        if expired:
            logger.debug(f"清理了 {len(expired)} 个过期的限流记录")


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
