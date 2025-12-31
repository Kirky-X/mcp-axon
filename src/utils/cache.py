# Copyright (c) 2026 Kirky.X. All rights reserved.
# Licensed under the MIT License.
# See LICENSE file in the project root for full license information.

"""缓存管理工具"""

import time
from typing import Any, Optional, Dict, Set
from threading import Lock


class LRUCache:
    """简单的 LRU 缓存实现"""
    
    def __init__(self, capacity: int = 100):
        self.capacity = capacity
        self.cache: Dict[str, Any] = {}
        self.access_times: Dict[str, float] = {}
        self.lock = Lock()
        
    def get(self, key: str) -> Optional[Any]:
        """获取缓存值"""
        with self.lock:
            if key in self.cache:
                # 更新访问时间
                self.access_times[key] = time.time()
                return self.cache[key]
            return None
    
    def put(self, key: str, value: Any) -> None:
        """设置缓存值"""
        with self.lock:
            # 检查是否需要清理旧条目
            if len(self.cache) >= self.capacity and key not in self.cache:
                self._evict_oldest()
            
            self.cache[key] = value
            self.access_times[key] = time.time()
    
    def _evict_oldest(self) -> None:
        """移除最久未使用的条目"""
        if not self.access_times:
            return
            
        oldest_key = min(self.access_times, key=self.access_times.get)
        del self.cache[oldest_key]
        del self.access_times[oldest_key]
    
    def invalidate(self, key: str) -> None:
        """使特定键的缓存失效"""
        with self.lock:
            if key in self.cache:
                del self.cache[key]
                if key in self.access_times:
                    del self.access_times[key]
    
    def clear(self) -> None:
        """清空缓存"""
        with self.lock:
            self.cache.clear()
            self.access_times.clear()


class CacheManager:
    """缓存管理器"""

    def __init__(self):
        self.project_cache = LRUCache(capacity=50)  # 项目缓存
        self.requirement_cache = LRUCache(capacity=200)  # 需求缓存
        self.chain_cache = LRUCache(capacity=50)  # 链化结果缓存
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
    
    def set_requirement(self, req_id: str, requirement: Any, project_id: Optional[str] = None) -> None:
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


# 全局缓存实例
cache_manager = CacheManager()