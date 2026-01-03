# Copyright (c) 2026 Kirky.X. All rights reserved.
# Licensed under MIT License.
# See LICENSE file in project root for full license information.

"""CSRF 保护工具"""

import hashlib
import secrets
import time
from typing import Dict


class CSRFTokenManager:
    """CSRF Token 管理器"""

    def __init__(self, token_ttl_seconds: int = 3600):
        """
        初始化 CSRF Token 管理器

        Args:
            token_ttl_seconds: Token 有效期（默认 1 小时）
        """
        self.token_ttl_seconds = token_ttl_seconds
        self.tokens: Dict[str, tuple] = {}  # {token: (session_id, 创建时间戳)}

    def generate_token(self, session_id: str) -> str:
        """
        生成 CSRF Token

        Args:
            session_id: 会话 ID

        Returns:
            CSRF Token
        """
        # 使用会话 ID 和随机数生成 token
        raw_token = f"{session_id}:{secrets.token_hex(16)}"
        token = hashlib.sha256(raw_token.encode()).hexdigest()

        # 记录 token 和对应的 session_id 及创建时间
        self.tokens[token] = (session_id, time.time())

        return token

    def validate_token(self, token: str, session_id: str) -> bool:
        """
        验证 CSRF Token

        Args:
            token: CSRF Token
            session_id: 会话 ID

        Returns:
            是否有效
        """
        # 检查 token 是否存在
        if token not in self.tokens:
            return False

        stored_session_id, timestamp = self.tokens[token]

        # 检查 token 是否属于当前会话
        if stored_session_id != session_id:
            return False

        # 检查 token 是否过期
        token_age = time.time() - timestamp
        if token_age > self.token_ttl_seconds:
            # 删除过期的 token
            del self.tokens[token]
            return False

        return True

    def revoke_token(self, token: str) -> None:
        """
        撤销 CSRF Token

        Args:
            token: CSRF Token
        """
        if token in self.tokens:
            del self.tokens[token]

    def cleanup_expired_tokens(self) -> int:
        """
        清理过期的 Token

        Returns:
            清理的 token 数量
        """
        current_time = time.time()
        expired_tokens = [
            token
            for token, (_, timestamp) in self.tokens.items()
            if current_time - timestamp > self.token_ttl_seconds
        ]

        for token in expired_tokens:
            del self.tokens[token]

        return len(expired_tokens)


# 全局 CSRF Token 管理器实例
csrf_manager = CSRFTokenManager()
