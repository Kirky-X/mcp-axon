# Copyright (c) 2026 Kirky.X. All rights reserved.
# Licensed under MIT License.
# See LICENSE file in project root for full license information.

"""CSRF 保护工具测试"""

import time

from src.utils.csrf import CSRFTokenManager


def test_csrf_token_generation():
    """测试 CSRF Token 生成"""
    manager = CSRFTokenManager()
    session_id = "test-session-123"

    token = manager.generate_token(session_id)

    assert token is not None
    assert isinstance(token, str)
    assert len(token) == 64  # SHA256 哈希长度


def test_csrf_token_validation():
    """测试 CSRF Token 验证"""
    manager = CSRFTokenManager(token_ttl_seconds=3600)
    session_id = "test-session-123"

    token = manager.generate_token(session_id)

    # 验证正确的 token
    assert manager.validate_token(token, session_id) is True

    # 验证错误的 token
    assert manager.validate_token("wrong-token", session_id) is False

    # 验证错误的会话
    assert manager.validate_token(token, "wrong-session") is False


def test_csrf_token_expiration():
    """测试 CSRF Token 过期"""
    manager = CSRFTokenManager(token_ttl_seconds=1)  # 1 秒过期
    session_id = "test-session-123"

    token = manager.generate_token(session_id)

    # 立即验证应该成功
    assert manager.validate_token(token, session_id) is True

    # 等待过期
    time.sleep(1.5)

    # 过期后验证应该失败
    assert manager.validate_token(token, session_id) is False


def test_csrf_token_revoke():
    """测试 CSRF Token 撤销"""
    manager = CSRFTokenManager()
    session_id = "test-session-123"

    token = manager.generate_token(session_id)

    # 验证 token 有效
    assert manager.validate_token(token, session_id) is True

    # 撤销 token
    manager.revoke_token(token)

    # 撤销后验证应该失败
    assert manager.validate_token(token, session_id) is False


def test_csrf_token_cleanup_expired():
    """测试清理过期 Token"""
    manager = CSRFTokenManager(token_ttl_seconds=1)
    _ = "test-session-123"

    # 生成多个 token
    _ = [manager.generate_token(f"session-{i}") for i in range(5)]

    # 等待过期
    time.sleep(1.5)

    # 清理过期 token
    cleaned_count = manager.cleanup_expired_tokens()

    assert cleaned_count == 5
    assert len(manager.tokens) == 0


def test_csrf_multiple_sessions():
    """测试多个会话的 Token"""
    manager = CSRFTokenManager()

    session1 = "session-1"
    session2 = "session-2"

    token1 = manager.generate_token(session1)
    token2 = manager.generate_token(session2)

    # 两个 token 应该不同
    assert token1 != token2

    # 每个 token 只能在对应的会话中验证
    assert manager.validate_token(token1, session1) is True
    assert manager.validate_token(token1, session2) is False
    assert manager.validate_token(token2, session2) is True
    assert manager.validate_token(token2, session1) is False
