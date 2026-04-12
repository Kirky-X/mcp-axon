# Copyright (c) 2026 Kirky.X. All rights reserved.
# Licensed under the MIT License.
# See LICENSE file in the project root for full license information.

"""缓存管理工具 - 基于 cachetools 的线程安全 TTL 缓存"""

from threading import Lock, RLock
from typing import Any, Dict, Optional, Set

from cachetools import TTLCache  # type: ignore[import-untyped]


class LRUCache:
    """线程安全的 LRU 缓存实现，基于 cachetools.TTLCache"""

    def __init__(self, capacity: int = 100, ttl_seconds: int = 300):
        """
        初始化 LRU 缓存

        Args:
            capacity: 缓存容量
            ttl_seconds: 缓存条目过期时间（秒），0 表示不过期（使用 LRUCache）
        """
        self.capacity = max(1, capacity)
        self.ttl_seconds = ttl_seconds
        self.lock = RLock()

        # ttl_seconds=0 表示不过期，使用无限 TTL
        effective_ttl = ttl_seconds if ttl_seconds > 0 else float("inf")
        self._cache = TTLCache(maxsize=capacity, ttl=effective_ttl)

    def get(self, key: str) -> Optional[Any]:
        """
        获取缓存值

        Args:
            key: 缓存键

        Returns:
            缓存值，如果不存在或已过期则返回 None
        """
        with self.lock:
            return self._cache.get(key, None)

    def put(self, key: str, value: Any) -> None:
        """
        设置缓存值

        Args:
            key: 缓存键
            value: 缓存值
        """
        with self.lock:
            self._cache[key] = value

    def invalidate(self, key: str) -> None:
        """
        使特定键的缓存失效

        Args:
            key: 缓存键
        """
        with self.lock:
            self._cache.pop(key, None)

    def clear(self) -> None:
        """清空缓存"""
        with self.lock:
            self._cache.clear()

    def cleanup_expired(self) -> int:
        """
        清理过期的缓存条目

        Returns:
            清理的条目数量
        """
        with self.lock:
            # TTLCache.expire() 返回清理的条目数量
            return self._cache.expire()


class CacheManager:
    """缓存管理器"""

    def __init__(
        self,
        project_cache_size: int = 50,
        requirement_cache_size: int = 200,
        chain_cache_size: int = 50,
        ttl_seconds: int = 300,
    ):
        """
        初始化缓存管理器

        Args:
            project_cache_size: 项目缓存大小
            requirement_cache_size: 需求缓存大小
            chain_cache_size: 链化结果缓存大小
            ttl_seconds: 缓存过期时间（秒）
        """
        self.project_cache = LRUCache(
            capacity=project_cache_size, ttl_seconds=ttl_seconds
        )
        self.requirement_cache = LRUCache(
            capacity=requirement_cache_size, ttl_seconds=ttl_seconds
        )
        self.chain_cache = LRUCache(capacity=chain_cache_size, ttl_seconds=ttl_seconds)
        self.project_requirements: Dict[str, Set[str]] = {}
        self.project_requirements_lock = Lock()

    def get_project(self, project_id: str) -> Optional[Any]:
        """获取项目缓存"""
        return self.project_cache.get(f"project_{project_id}")

    def set_project(self, project_id: str, project: Any) -> None:
        """设置项目缓存"""
        self.project_cache.put(f"project_{project_id}", project)

    def get_requirement(self, req_id: str) -> Optional[Any]:
        """获取需求缓存"""
        return self.requirement_cache.get(f"req_{req_id}")

    def set_requirement(self, req_id: str, requirement: Any, project_id: str) -> None:
        """
        设置需求缓存

        Args:
            req_id: 需求 ID
            requirement: 需求数据
            project_id: 项目 ID（必填，用于缓存失效）

        Raises:
            ValueError: 如果 project_id 为空
        """
        if not project_id:
            raise ValueError("project_id is required for requirement caching")

        self.requirement_cache.put(f"req_{req_id}", requirement)

        with self.project_requirements_lock:
            if project_id not in self.project_requirements:
                self.project_requirements[project_id] = set()
            self.project_requirements[project_id].add(req_id)

    def get_chain_result(self, project_id: str) -> Optional[Any]:
        """获取链化结果缓存"""
        return self.chain_cache.get(f"chain_{project_id}")

    def set_chain_result(self, project_id: str, result: Any) -> None:
        """设置链化结果缓存"""
        self.chain_cache.put(f"chain_{project_id}", result)

    def invalidate_project(self, project_id: str) -> None:
        """使项目相关缓存失效"""
        self.project_cache.invalidate(f"project_{project_id}")
        self.chain_cache.invalidate(f"chain_{project_id}")

        with self.project_requirements_lock:
            if project_id in self.project_requirements:
                for req_id in self.project_requirements[project_id]:
                    self.requirement_cache.invalidate(f"req_{req_id}")
                del self.project_requirements[project_id]

    def invalidate_requirement(
        self, req_id: str, project_id: Optional[str] = None
    ) -> None:
        """使单个需求缓存失效"""
        self.requirement_cache.invalidate(f"req_{req_id}")

        if project_id:
            with self.project_requirements_lock:
                if project_id in self.project_requirements:
                    self.project_requirements[project_id].discard(req_id)
            self.chain_cache.invalidate(f"chain_{project_id}")

    def cleanup_expired(self) -> Dict[str, int]:
        """清理所有缓存中的过期条目"""
        return {
            "project": self.project_cache.cleanup_expired(),
            "requirement": self.requirement_cache.cleanup_expired(),
            "chain": self.chain_cache.cleanup_expired(),
        }


# 全局缓存管理器实例
cache_manager = CacheManager()
