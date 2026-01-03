# Copyright (c) 2026 Kirky.X. All rights reserved.
# Licensed under the MIT License.
# See LICENSE file in the project root for full license information.

"""统一异常类定义"""


class MCPAxonError(Exception):
    """基础异常类"""

    def __init__(self, message: str, error_code: str = None):
        self.message = message
        self.error_code = error_code
        super().__init__(self.message)


class ValidationError(MCPAxonError):
    """验证错误"""

    def __init__(self, message: str):
        super().__init__(message, error_code="VALIDATION_ERROR")


class NotFoundError(MCPAxonError):
    """资源未找到错误"""

    def __init__(self, resource_type: str, resource_id: str):
        message = f"{resource_type} 不存在: {resource_id}"
        super().__init__(message, error_code="NOT_FOUND")


class BusinessRuleError(MCPAxonError):
    """业务规则错误"""

    def __init__(self, message: str):
        super().__init__(message, error_code="BUSINESS_RULE_ERROR")


class PermissionError(MCPAxonError):
    """权限错误"""

    def __init__(self, message: str):
        super().__init__(message, error_code="PERMISSION_ERROR")


class LockError(MCPAxonError):
    """锁错误"""

    def __init__(self, message: str):
        super().__init__(message, error_code="LOCK_ERROR")


class ChainError(MCPAxonError):
    """链化错误"""

    def __init__(self, message: str):
        super().__init__(message, error_code="CHAIN_ERROR")


class SnapshotError(MCPAxonError):
    """快照错误"""

    def __init__(self, message: str):
        super().__init__(message, error_code="SNAPSHOT_ERROR")


class GraphError(MCPAxonError):
    """图算法错误"""

    def __init__(self, message: str):
        super().__init__(message, error_code="GRAPH_ERROR")
