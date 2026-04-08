# Copyright (c) 2026 Kirky.X. All rights reserved.
# Licensed under the MIT License.
# See LICENSE file in the project root for full license information.

"""错误处理工具"""

import functools
import logging
import os
import traceback

from src.exceptions import MCPAxonError

logger = logging.getLogger(__name__)


def get_safe_error_message(error_message: str) -> str:
    """获取安全的错误消息（生产环境过滤敏感信息）"""
    is_production = os.getenv("ENVIRONMENT", "development").lower() == "production"

    if is_production:
        # 生产环境返回通用错误消息
        return "操作失败，请稍后重试"
    else:
        # 开发环境返回详细错误信息
        return error_message


def handle_errors(func):
    """统一错误处理装饰器"""

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except MCPAxonError as e:
            # 已知业务异常，直接抛出
            logger.warning(f"业务异常: {e.error_code} - {e.message}")
            raise
        except Exception as e:
            # 未预期的错误
            logger.error(
                f"未预期的错误: {type(e).__name__} - {str(e)}\n"
                f"堆栈跟踪: {traceback.format_exc()}"
            )
            # 可以选择包装为 MCPAxonError 或直接抛出
            raise MCPAxonError(
                "内部服务器错误",
                error_code="INTERNAL_ERROR",
            )

    return wrapper
