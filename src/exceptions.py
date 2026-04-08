# Copyright (c) 2026 Kirky.X. All rights reserved.
# Licensed under the MIT License.
# See LICENSE file in the project root for full license information.

"""统一异常类定义"""

from enum import Enum
from typing import Any, Dict, Optional


class ErrorCode(str, Enum):
    """统一错误码枚举"""

    # 通用错误
    UNKNOWN = "E000"

    # 资源相关
    PROJECT_NOT_FOUND = "E001"
    REQUIREMENT_NOT_FOUND = "E002"
    VALIDATION_NOT_FOUND = "E003"
    SNAPSHOT_NOT_FOUND = "E004"

    # 状态转换
    INVALID_STATUS_TRANSITION = "E010"

    # 依赖相关
    CYCLE_DEPENDENCY = "E020"
    HAS_DEPENDENCIES = "E021"
    DEPENDENCY_NOT_FOUND = "E022"

    # 链化相关
    ALREADY_CHAINED = "E030"
    NOT_CHAINED = "E031"
    CHAIN_BUILD_FAILED = "E032"

    # 验证相关
    NOT_LEAF_NODE = "E040"
    VALIDATION_EXISTS = "E041"

    # 批量操作
    BATCH_SIZE_EXCEEDED = "E050"
    BATCH_PARTIAL_FAILURE = "E051"

    # 并发控制
    PROJECT_LOCKED = "E060"
    LOCK_TIMEOUT = "E061"

    # 权限
    PERMISSION_DENIED = "E070"

    # 验证错误
    VALIDATION_ERROR = "E100"
    INVALID_INPUT = "E101"


class MCPAxonError(Exception):
    """基础异常类"""

    def __init__(
        self,
        message: str,
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        self.message = message
        self.error_code = error_code or ErrorCode.UNKNOWN.value
        self.details = details or {}
        super().__init__(f"[{self.error_code}] {self.message}")

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "error": True,
            "error_code": self.error_code,
            "message": self.message,
            "details": self.details,
        }


class ValidationError(MCPAxonError):
    """验证错误"""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message, error_code=ErrorCode.VALIDATION_ERROR.value, details=details
        )


class NotFoundError(MCPAxonError):
    """资源未找到错误"""

    def __init__(self, resource_type: str, resource_id: str):
        code_map = {
            "project": ErrorCode.PROJECT_NOT_FOUND,
            "requirement": ErrorCode.REQUIREMENT_NOT_FOUND,
            "validation": ErrorCode.VALIDATION_NOT_FOUND,
            "snapshot": ErrorCode.SNAPSHOT_NOT_FOUND,
        }
        error_code = code_map.get(resource_type.lower(), ErrorCode.UNKNOWN)
        message = f"{resource_type} 不存在: {resource_id}"
        super().__init__(
            message,
            error_code=error_code.value,
            details={"resource_type": resource_type, "resource_id": resource_id},
        )


class BusinessRuleError(MCPAxonError):
    """业务规则错误"""

    def __init__(self, message: str, error_code: Optional[str] = None):
        super().__init__(
            message, error_code=error_code or ErrorCode.VALIDATION_ERROR.value
        )


class PermissionError(MCPAxonError):
    """权限错误"""

    def __init__(self, message: str):
        super().__init__(message, error_code=ErrorCode.PERMISSION_DENIED.value)


class LockError(MCPAxonError):
    """锁错误"""

    def __init__(self, message: str, project_id: Optional[str] = None):
        details = {"project_id": project_id} if project_id else None
        super().__init__(
            message, error_code=ErrorCode.PROJECT_LOCKED.value, details=details
        )


class ChainError(MCPAxonError):
    """链化错误"""

    def __init__(self, message: str, error_code: Optional[str] = None):
        super().__init__(
            message, error_code=error_code or ErrorCode.CHAIN_BUILD_FAILED.value
        )


class SnapshotError(MCPAxonError):
    """快照错误"""

    def __init__(self, message: str):
        super().__init__(message, error_code=ErrorCode.SNAPSHOT_NOT_FOUND.value)


class GraphError(MCPAxonError):
    """图算法错误"""

    def __init__(self, message: str, cycle_nodes: Optional[list] = None):
        details = {"cycle_nodes": cycle_nodes} if cycle_nodes else None
        super().__init__(
            message, error_code=ErrorCode.CYCLE_DEPENDENCY.value, details=details
        )


class DependencyError(MCPAxonError):
    """依赖关系错误"""

    def __init__(
        self,
        message: str,
        error_code: Optional[str] = None,
        dependencies: Optional[list] = None,
    ):
        details = {"dependencies": dependencies} if dependencies else None
        super().__init__(
            message,
            error_code=error_code or ErrorCode.HAS_DEPENDENCIES.value,
            details=details,
        )
