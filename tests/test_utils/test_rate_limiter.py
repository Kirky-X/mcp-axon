# Copyright (c) 2026 Kirky.X. All rights reserved.
# Licensed under the MIT License.
# See LICENSE file in the project root for full license information.

"""请求限流器测试"""

from unittest.mock import patch

import pytest

from src.utils.rate_limiter import RateLimiter, get_rate_limiter

# ========== RateLimiter.is_allowed ==========


@pytest.fixture
def frozen_time():
    """固定时间，避免测试不稳定"""
    with patch("src.utils.rate_limiter.time") as mock_time:
        mock_time.time.return_value = 1000.0
        yield mock_time


def test_rate_limiter_allows_within_limit(frozen_time):
    """测试: 限制内请求允许"""
    limiter = RateLimiter(max_requests=3, window_seconds=60)

    assert limiter.is_allowed("user1") is True
    assert limiter.is_allowed("user1") is True
    assert limiter.is_allowed("user1") is True


def test_rate_limiter_blocks_when_exceeded(frozen_time):
    """测试: 超过限制请求拒绝"""
    limiter = RateLimiter(max_requests=2, window_seconds=60)

    assert limiter.is_allowed("user1") is True
    assert limiter.is_allowed("user1") is True
    assert limiter.is_allowed("user1") is False


def test_rate_limiter_window_expiry(frozen_time):
    """测试: 时间窗口过期后允许新请求"""
    limiter = RateLimiter(max_requests=2, window_seconds=60)

    limiter.is_allowed("user1")  # t=1000
    limiter.is_allowed("user1")  # t=1000

    frozen_time.time.return_value = 1061.0  # 61秒后
    assert limiter.is_allowed("user1") is True  # 已过期


def test_rate_limiter_different_identifiers(frozen_time):
    """测试: 不同标识符独立计数"""
    limiter = RateLimiter(max_requests=2, window_seconds=60)

    assert limiter.is_allowed("user1") is True
    assert limiter.is_allowed("user1") is True
    assert limiter.is_allowed("user1") is False  # user1 超限

    assert limiter.is_allowed("user2") is True  # user2 不受影响


def test_rate_limiter_custom_config(frozen_time):
    """测试: 自定义配置生效"""
    limiter = RateLimiter(max_requests=5, window_seconds=30)

    assert limiter.max_requests == 5
    assert limiter.window_seconds == 30

    for _ in range(5):
        assert limiter.is_allowed("user1") is True

    assert limiter.is_allowed("user1") is False


def test_rate_limiter_removes_expired_requests(frozen_time):
    """测试: 移除窗口外的过期请求"""
    limiter = RateLimiter(max_requests=3, window_seconds=60)

    frozen_time.time.return_value = 1000.0
    limiter.is_allowed("user1")
    limiter.is_allowed("user1")

    frozen_time.time.return_value = 1020.0  # 20秒后
    limiter.is_allowed("user1")

    frozen_time.time.return_value = 1040.0  # 40秒后
    limiter.is_allowed("user1")

    # 最后一个请求在 1040，需要在 1040 + 60 = 1100 后才过期
    frozen_time.time.return_value = 1101.0
    # 触发一次 is_allowed 来清理过期请求
    limiter.is_allowed("user1")
    assert len(limiter.requests["user1"]) == 1  # 只有最新的请求保留


# ========== RateLimiter.get_remaining_requests ==========


def test_get_remaining_requests_full(frozen_time):
    """测试: 全部剩余请求"""
    limiter = RateLimiter(max_requests=10, window_seconds=60)

    assert limiter.get_remaining_requests("user1") == 10


def test_get_remaining_requests_partial(frozen_time):
    """测试: 部分剩余请求"""
    limiter = RateLimiter(max_requests=10, window_seconds=60)

    limiter.is_allowed("user1")
    limiter.is_allowed("user1")
    limiter.is_allowed("user1")

    assert limiter.get_remaining_requests("user1") == 7


def test_get_remaining_requests_zero(frozen_time):
    """测试: 零剩余请求"""
    limiter = RateLimiter(max_requests=5, window_seconds=60)

    for _ in range(5):
        limiter.is_allowed("user1")

    assert limiter.get_remaining_requests("user1") == 0


def test_get_remaining_requests_after_expiry(frozen_time):
    """测试: 过期后剩余恢复"""
    limiter = RateLimiter(max_requests=5, window_seconds=60)

    # 用完所有配额
    for _ in range(5):
        limiter.is_allowed("user1")

    assert limiter.get_remaining_requests("user1") == 0

    # 时间前进 61 秒，使所有请求过期
    frozen_time.time.return_value = 1061.0

    # 应该恢复
    assert limiter.get_remaining_requests("user1") == 5


# ========== RateLimiter.reset ==========


def test_reset_specific_identifier(frozen_time):
    """测试: 重置特定标识符"""
    limiter = RateLimiter(max_requests=2, window_seconds=60)

    limiter.is_allowed("user1")
    limiter.is_allowed("user1")

    limiter.reset("user1")

    # user1 应该被重置
    assert limiter.is_allowed("user1") is True
    assert limiter.is_allowed("user1") is True


def test_reset_all_identifiers(frozen_time):
    """测试: 重置所有标识符"""
    limiter = RateLimiter(max_requests=1, window_seconds=60)

    limiter.is_allowed("user1")
    limiter.is_allowed("user2")

    limiter.reset()  # 重置所有

    # 所有用户都应该被重置
    assert limiter.is_allowed("user1") is True
    assert limiter.is_allowed("user2") is True


def test_reset_nonexistent_identifier(frozen_time):
    """测试: 重置不存在的标识符不报错"""
    limiter = RateLimiter(max_requests=5, window_seconds=60)

    limiter.reset("nonexistent")  # 不应抛出异常


# ========== RateLimiter.cleanup ==========


def test_cleanup_removes_old_records(frozen_time):
    """测试: 清理移除过期记录"""
    limiter = RateLimiter(max_requests=5, window_seconds=60)

    frozen_time.time.return_value = 1000.0
    limiter.is_allowed("user1")

    frozen_time.time.return_value = 2000.0  # 1000秒后
    limiter.is_allowed("user2")

    limiter.cleanup(max_age_seconds=500)  # 清理500秒前的

    # user1 应该被清理
    assert "user1" not in limiter.requests
    # user2 应该保留
    assert "user2" in limiter.requests


def test_cleanup_removes_empty_history(frozen_time):
    """测试: 清理移除空历史的记录"""
    limiter = RateLimiter(max_requests=5, window_seconds=60)

    frozen_time.time.return_value = 1000.0
    limiter.is_allowed("user1")

    frozen_time.time.return_value = 5000.0  # 4000秒后
    limiter.cleanup(max_age_seconds=3600)

    # user1 应该被清理（超过1小时）
    assert "user1" not in limiter.requests


def test_cleanup_preserves_recent_records(frozen_time):
    """测试: 清理保留最近记录"""
    limiter = RateLimiter(max_requests=5, window_seconds=60)

    frozen_time.time.return_value = 1000.0
    limiter.is_allowed("user1")

    frozen_time.time.return_value = 2000.0  # 1000秒后
    limiter.cleanup(max_age_seconds=3600)

    # user1 应该保留
    assert "user1" in limiter.requests
    assert len(limiter.requests["user1"]) == 1


# ========== Concurrent access ==========


def test_rate_limiter_concurrent_requests():
    """测试: 并发请求计数正确"""
    import threading

    limiter = RateLimiter(max_requests=10, window_seconds=60)
    results = []

    def make_request():
        result = limiter.is_allowed("shared")
        results.append(result)

    threads = [threading.Thread(target=make_request) for _ in range(20)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    # 不应超过限制
    assert sum(results) <= 10


def test_rate_limiter_thread_safety():
    """测试: 线程安全性"""
    import threading

    limiter = RateLimiter(max_requests=5, window_seconds=60)
    errors = []

    def make_requests(identifier):
        try:
            for _ in range(10):
                limiter.is_allowed(identifier)
        except Exception as e:
            errors.append(e)

    threads = [
        threading.Thread(target=make_requests, args=(f"user{i}",)) for i in range(5)
    ]

    for t in threads:
        t.start()
    for t in threads:
        t.join()

    # 不应该有错误
    assert len(errors) == 0


# ========== Global rate limiter ==========


def test_get_rate_limiter_returns_singleton():
    """测试: get_rate_limiter 返回单例"""
    limiter1 = get_rate_limiter()
    limiter2 = get_rate_limiter()

    assert limiter1 is limiter2


def test_get_rate_limiter_default_config():
    """测试: 全局限流器使用默认配置"""
    limiter = get_rate_limiter()

    assert limiter.max_requests == 100
    assert limiter.window_seconds == 60


# ========== Edge cases ==========


def test_rate_limiter_empty_string_identifier(frozen_time):
    """测试: 空字符串标识符"""
    limiter = RateLimiter(max_requests=5, window_seconds=60)

    assert limiter.is_allowed("") is True
    assert limiter.is_allowed("") is True


def test_rate_limiter_zero_max_requests(frozen_time):
    """测试: 零最大请求数"""
    limiter = RateLimiter(max_requests=0, window_seconds=60)

    assert limiter.is_allowed("user1") is False


def test_rate_limiter_zero_window(frozen_time):
    """测试: 零时间窗口"""
    limiter = RateLimiter(max_requests=5, window_seconds=0)

    assert limiter.is_allowed("user1") is True
    # 下一请求应该仍然允许，因为窗口立即过期
    assert limiter.is_allowed("user1") is True


def test_rate_limiter_large_max_requests(frozen_time):
    """测试: 大请求限制"""
    limiter = RateLimiter(max_requests=10000, window_seconds=60)

    for _ in range(100):
        assert limiter.is_allowed("user1") is True
