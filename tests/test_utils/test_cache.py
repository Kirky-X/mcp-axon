# Copyright (c) 2026 Kirky.X. All rights reserved.
# Licensed under the MIT License.
# See LICENSE file in the project root for full license information.

"""缓存管理工具测试"""

import pytest
import time
from src.utils.cache import LRUCache, CacheManager


def test_lru_cache_basic_operations():
    """测试 LRU 缓存基本操作"""

    # Arrange
    cache = LRUCache(capacity=3)

    # Act & Assert - 添加和获取
    cache.put("key1", "value1")
    assert cache.get("key1") == "value1"

    cache.put("key2", "value2")
    cache.put("key3", "value3")

    # 所有值都应该存在
    assert cache.get("key1") == "value1"
    assert cache.get("key2") == "value2"
    assert cache.get("key3") == "value3"


def test_lru_cache_eviction():
    """测试 LRU 缓存淘汰机制"""

    # Arrange
    cache = LRUCache(capacity=2)

    # Act - 添加超过容量的项目
    cache.put("key1", "value1")
    cache.put("key2", "value2")
    cache.put("key3", "value3")  # 应该淘汰 key1

    # Assert - key1 应该被淘汰
    assert cache.get("key1") is None
    assert cache.get("key2") == "value2"
    assert cache.get("key3") == "value3"


def test_lru_cache_access_order():
    """测试 LRU 缓存访问顺序更新"""

    # Arrange
    cache = LRUCache(capacity=2)

    # Act - 添加项目并访问
    cache.put("key1", "value1")
    cache.put("key2", "value2")
    cache.get("key1")  # 访问 key1，使其成为最近使用的
    cache.put("key3", "value3")  # 应该淘汰 key2

    # Assert - key2 应该被淘汰，key1 还在
    assert cache.get("key1") == "value1"
    assert cache.get("key2") is None
    assert cache.get("key3") == "value3"


def test_lru_cache_invalidate():
    """测试 LRU 缓存失效"""

    # Arrange
    cache = LRUCache(capacity=3)
    cache.put("key1", "value1")
    cache.put("key2", "value2")

    # Act - 使 key1 失效
    cache.invalidate("key1")

    # Assert - key1 应该不存在
    assert cache.get("key1") is None
    assert cache.get("key2") == "value2"


def test_lru_cache_clear():
    """测试 LRU 缓存清空"""

    # Arrange
    cache = LRUCache(capacity=3)
    cache.put("key1", "value1")
    cache.put("key2", "value2")
    cache.put("key3", "value3")

    # Act - 清空缓存
    cache.clear()

    # Assert - 所有值都应该不存在
    assert cache.get("key1") is None
    assert cache.get("key2") is None
    assert cache.get("key3") is None


def test_lru_cache_update_existing():
    """测试更新已存在的键"""

    # Arrange
    cache = LRUCache(capacity=2)
    cache.put("key1", "value1")

    # Act - 更新 key1
    cache.put("key1", "new_value1")

    # Assert - 应该返回新值
    assert cache.get("key1") == "new_value1"


def test_lru_cache_get_nonexistent():
    """测试获取不存在的键"""

    # Arrange
    cache = LRUCache(capacity=2)

    # Act & Assert - 获取不存在的键
    assert cache.get("nonexistent") is None


def test_cache_manager_project_operations():
    """测试缓存管理器的项目操作"""

    # Arrange
    manager = CacheManager()

    # Act & Assert - 设置和获取项目
    manager.set_project("proj1", {"name": "项目1"})
    result = manager.get_project("proj1")
    assert result is not None
    assert result["name"] == "项目1"


def test_cache_manager_requirement_operations():
    """测试缓存管理器的需求操作"""

    # Arrange
    manager = CacheManager()

    # Act & Assert - 设置和获取需求
    manager.set_requirement("req1", {"content": "需求1"}, "proj1")
    result = manager.get_requirement("req1")
    assert result is not None
    assert result["content"] == "需求1"


def test_cache_manager_chain_operations():
    """测试缓存管理器的链化操作"""

    # Arrange
    manager = CacheManager()

    # Act & Assert - 设置和获取链化结果
    manager.set_chain_result("proj1", {"status": "completed"})
    result = manager.get_chain_result("proj1")
    assert result is not None
    assert result["status"] == "completed"


def test_cache_manager_invalidate_project():
    """测试缓存管理器的项目失效"""

    # Arrange
    manager = CacheManager()
    manager.set_project("proj1", {"name": "项目1"})
    manager.set_requirement("req1", {"content": "需求1"}, "proj1")
    manager.set_chain_result("proj1", {"status": "completed"})

    # Act - 使项目失效
    manager.invalidate_project("proj1")

    # Assert - 所有相关缓存都应该失效
    assert manager.get_project("proj1") is None
    assert manager.get_chain_result("proj1") is None
    assert manager.get_requirement("req1") is None


def test_cache_manager_project_requirements_tracking():
    """测试缓存管理器的项目-需求关系跟踪"""

    # Arrange
    manager = CacheManager()

    # Act - 添加多个需求到同一个项目
    manager.set_requirement("req1", {"content": "需求1"}, "proj1")
    manager.set_requirement("req2", {"content": "需求2"}, "proj1")
    manager.set_requirement("req3", {"content": "需求3"}, "proj1")

    # 使项目失效
    manager.invalidate_project("proj1")

    # Assert - 所有需求缓存都应该失效
    assert manager.get_requirement("req1") is None
    assert manager.get_requirement("req2") is None
    assert manager.get_requirement("req3") is None


def test_lru_cache_thread_safety():
    """测试 LRU 缓存的线程安全性"""

    # Arrange
    cache = LRUCache(capacity=100)

    # Act - 并发写入
    def put_items(start, end):
        for i in range(start, end):
            cache.put(f"key{i}", f"value{i}")

    import threading
    threads = [
        threading.Thread(target=put_items, args=(0, 50)),
        threading.Thread(target=put_items, args=(50, 100))
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    # Assert - 所有值都应该存在
    for i in range(100):
        result = cache.get(f"key{i}")
        assert result is not None, f"key{i} 不存在"


def test_cache_manager_multiple_projects():
    """测试缓存管理器的多项目支持"""

    # Arrange
    manager = CacheManager()

    # Act - 添加多个项目的需求
    manager.set_requirement("req1", {"content": "需求1"}, "proj1")
    manager.set_requirement("req2", {"content": "需求2"}, "proj2")
    manager.set_requirement("req3", {"content": "需求3"}, "proj1")

    # 使 proj1 失效
    manager.invalidate_project("proj1")

    # Assert - 只有 proj1 的需求失效
    assert manager.get_requirement("req1") is None
    assert manager.get_requirement("req3") is None
    assert manager.get_requirement("req2") is not None  # proj2 的需求还在


def test_lru_cache_capacity_boundary():
    """测试 LRU 缓存容量边界"""

    # Arrange & Act - 创建容量为 1 的缓存
    cache = LRUCache(capacity=1)
    cache.put("key1", "value1")
    cache.put("key2", "value2")

    # Assert - 只有 key2 存在
    assert cache.get("key1") is None
    assert cache.get("key2") == "value2"