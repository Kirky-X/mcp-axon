# Copyright (c) 2026 Kirky.X. All rights reserved.
# Licensed under the MIT License.
# See LICENSE file in the project root for full license information.

"""缓存管理工具"""

import time
from collections import OrderedDict
from threading import Lock, RLock
from typing import Any, Dict, Optional, Set, Tuple


class LRUCache:
    """线程安全的 LRU 缓存实现，支持 TTL 过期"""

    def __init__(self, capacity: int = 100, ttl_seconds: int = 300):
        """
        初始化 LRU 缓存

        Args:
            capacity: 缓存容量
            ttl_seconds: 缓存条目过期时间（秒），0 表示不过期
        """
        self.capacity = max(1, capacity)  # 确保容量至少为1
        self.ttl_seconds = ttl_seconds  # 过期时间
        self.cache: OrderedDict[str, Tuple[Any, float]] = (
            OrderedDict()
        )  # {key: (value, timestamp)}
        self.lock = RLock()  # 使用可重入锁

    def get(self, key: str) -> Optional[Any]:
        """
        获取缓存值

        Args:
            key: 缓存键

        Returns:
            缓存值，如果不存在或已过期则返回 None
        """
        with self.lock:
            if key in self.cache:
                value, timestamp = self.cache[key]

                # 检查是否过期
                if self.ttl_seconds > 0 and time.time() - timestamp > self.ttl_seconds:
                    # 过期，删除并返回 None
                    del self.cache[key]
                    return None

                # 移动到末尾（最近使用）并更新时间戳
                self.cache.pop(key)
                self.cache[key] = (value, time.time())
                return value
            return None

    def put(self, key: str, value: Any) -> None:
        """
        设置缓存值

        Args:
            key: 缓存键
            value: 缓存值
        """
        with self.lock:
            current_time = time.time()
            if key in self.cache:
                # 更新现有键值
                self.cache.pop(key)
            elif len(self.cache) >= self.capacity:
                # 移除最久未使用的条目
                self.cache.popitem(last=False)

            self.cache[key] = (value, current_time)

    def invalidate(self, key: str) -> None:
        """
        使特定键的缓存失效

        Args:
            key: 缓存键
        """
        with self.lock:
            self.cache.pop(key, None)

    def clear(self) -> None:
        """清空缓存"""
        with self.lock:
            self.cache.clear()

    def size(self) -> int:
        """获取缓存大小"""
        with self.lock:
            return len(self.cache)

    def cleanup_expired(self) -> int:
        """
        清理过期的缓存条目

        Returns:
            清理的条目数量
        """
        if self.ttl_seconds <= 0:
            return 0

        with self.lock:
            current_time = time.time()
            expired_keys = [
                key
                for key, (_, timestamp) in self.cache.items()
                if current_time - timestamp > self.ttl_seconds
            ]

            for key in expired_keys:
                del self.cache[key]

            return len(expired_keys)


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
        )  # 项目缓存
        self.requirement_cache = LRUCache(
            capacity=requirement_cache_size, ttl_seconds=ttl_seconds
        )  # 需求缓存
        self.chain_cache = LRUCache(
            capacity=chain_cache_size, ttl_seconds=ttl_seconds
        )  # 链化结果缓存
        self.project_requirements: Dict[str, Set[str]] = {}  # 项目ID -> 需求ID集合
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

    def set_requirement(
        self, req_id: str, requirement: Any, project_id: Optional[str] = None
    ) -> None:
        """设置需求缓存"""
        self.requirement_cache.put(f"req_{req_id}", requirement)

        # 记录项目与需求的关系
        if project_id:
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

        # 清除该项目的所有需求缓存
        with self.project_requirements_lock:
            if project_id in self.project_requirements:
                for req_id in self.project_requirements[project_id]:
                    self.requirement_cache.invalidate(f"req_{req_id}")
                del self.project_requirements[project_id]

    def invalidate_requirement(
        self, req_id: str, project_id: Optional[str] = None
    ) -> None:
        """
        使单个需求缓存失效，并使相关的链化结果缓存失效

        Args:
            req_id: 需求 ID
            project_id: 项目 ID（可选，用于清理项目需求关系）
        """
        self.requirement_cache.invalidate(f"req_{req_id}")

        # 清理项目需求关系
        if project_id:
            with self.project_requirements_lock:
                if project_id in self.project_requirements:
                    self.project_requirements[project_id].discard(req_id)

        # 使链化结果缓存失效（因为需求变更会影响链化结果）
        if project_id:
            self.chain_cache.invalidate(f"chain_{project_id}")

    def cleanup_expired(self) -> Dict[str, int]:
        """
        清理所有缓存中的过期条目

        Returns:
            清理统计 {cache_name: cleaned_count}
        """
        return {
            "project": self.project_cache.cleanup_expired(),
            "requirement": self.requirement_cache.cleanup_expired(),
            "chain": self.chain_cache.cleanup_expired(),
        }


# 全局缓存实例（延迟初始化）
_cache_manager: Optional[CacheManager] = None
_cache_manager_lock = Lock()


def get_cache_manager() -> CacheManager:
    """获取全局缓存管理器实例"""
    global _cache_manager

    if _cache_manager is None:
        with _cache_manager_lock:
            if _cache_manager is None:
                # 尝试从性能配置中读取缓存大小
                try:
                    from src.utils.performance_config import get_performance_config

                    config = get_performance_config()
                    _cache_manager = CacheManager(
                        project_cache_size=config.cache_project_size,
                        requirement_cache_size=config.cache_requirement_size,
                        chain_cache_size=config.cache_chain_size,
                        ttl_seconds=config.cache_ttl_seconds,
                    )
                except Exception:
                    # 如果配置不可用，使用默认值
                    _cache_manager = CacheManager()

    return _cache_manager


# 向后兼容的全局实例
cache_manager = get_cache_manager()
