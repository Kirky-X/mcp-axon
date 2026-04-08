# Copyright (c) 2026 Kirky.X. All rights reserved.
# Licensed under the MIT License.
# See LICENSE file in the project root for full license information.

"""错误处理器测试"""

import os
import pytest

from src.exceptions import MCPAxonError
from src.utils.error_handler import get_safe_error_message, handle_errors, safe_execute


# ========== get_safe_error_message ==========


def test_get_safe_error_message_production_mode():
    """测试: 生产环境返回通用消息"""
    # Arrange
    os.environ["ENVIRONMENT"] = "production"
    detailed_message = (
        "数据库连接失败: host=db.example.com port=5432 user=admin password=secret"
    )

    # Act
    result = get_safe_error_message(detailed_message)

    # Assert
    assert result == "操作失败，请稍后重试"
    assert "db.example.com" not in result
    assert "password" not in result


def test_get_safe_error_message_development_mode():
    """测试: 开发环境返回详细消息"""
    # Arrange
    os.environ["ENVIRONMENT"] = "development"
    detailed_message = "数据库连接失败: host=db.example.com"

    # Act
    result = get_safe_error_message(detailed_message)

    # Assert
    assert result == detailed_message
    assert "db.example.com" in result


def test_get_safe_error_message_no_env_variable():
    """测试: 无环境变量时默认为开发模式"""
    # Arrange
    if "ENVIRONMENT" in os.environ:
        del os.environ["ENVIRONMENT"]
    detailed_message = "详细错误信息"

    # Act
    result = get_safe_error_message(detailed_message)

    # Assert
    assert result == detailed_message


def test_get_safe_error_message_development_case_insensitive():
    """测试: 环境变量大小写不敏感"""
    # Arrange
    os.environ["ENVIRONMENT"] = "Production"
    detailed_message = "错误信息"

    # Act
    result = get_safe_error_message(detailed_message)

    # Assert
    assert result == "操作失败，请稍后重试"


def test_get_safe_error_message_filters_stack_traces():
    """测试: 生产环境过滤堆栈跟踪"""
    # Arrange
    os.environ["ENVIRONMENT"] = "production"
    detailed_message = (
        "错误在 file.py:42\n堆栈跟踪:\n  at function1()\n  at function2()"
    )

    # Act
    result = get_safe_error_message(detailed_message)

    # Assert
    assert "堆栈跟踪" not in result
    assert "file.py" not in result


def test_get_safe_error_message_filters_file_paths():
    """测试: 生产环境过滤文件路径"""
    # Arrange
    os.environ["ENVIRONMENT"] = "production"
    detailed_message = "错误在 /home/user/project/src/module.py:123"

    # Act
    result = get_safe_error_message(detailed_message)

    # Assert
    assert "/home/user/" not in result
    assert ".py" not in result


def test_get_safe_error_message_filters_passwords():
    """测试: 生产环境过滤密码"""
    # Arrange
    os.environ["ENVIRONMENT"] = "production"
    detailed_message = "认证失败: password='secret123', api_key='key456'"

    # Act
    result = get_safe_error_message(detailed_message)

    # Assert
    assert "secret123" not in result
    assert "key456" not in result


# ========== handle_errors decorator ==========


def test_handle_errors_successful_execution():
    """测试: 成功执行正常返回"""

    # Arrange
    @handle_errors
    def successful_function():
        return "success"

    # Act
    result = successful_function()

    # Assert
    assert result == "success"


def test_handle_errors_catches_mcpxon_error():
    """测试: 捕获 MCPAxonError 并记录日志"""

    # Arrange
    @handle_errors
    def function_raises_mcpxon_error():
        raise MCPAxonError("业务错误", error_code="BUSINESS_ERROR")

    # Act & Assert
    with pytest.raises(MCPAxonError) as exc_info:
        function_raises_mcpxon_error()

    assert exc_info.value.message == "业务错误"
    assert exc_info.value.error_code == "BUSINESS_ERROR"


def test_handle_errors_catches_generic_exception():
    """测试: 捕获通用异常并转换为 MCPAxonError"""

    # Arrange
    @handle_errors
    def function_raises_value_error():
        raise ValueError("原始错误")

    # Act & Assert
    with pytest.raises(MCPAxonError) as exc_info:
        function_raises_value_error()

    assert exc_info.value.message == "内部服务器错误"
    assert exc_info.value.error_code == "INTERNAL_ERROR"


def test_handle_errors_preserves_function_signature():
    """测试: 保持被装饰函数的签名"""

    # Arrange
    @handle_errors
    def function_with_args(a, b, c=None):
        return a + b

    # Act
    result = function_with_args(1, 2)

    # Assert
    assert result == 3


def test_handle_errors_logs_business_warning():
    """测试: 业务异常记录 WARNING 级别日志"""

    # Arrange
    @handle_errors
    def function_raises_error():
        raise MCPAxonError("错误", error_code="ERROR_CODE")

    # Act & Assert
    with pytest.raises(MCPAxonError):
        function_raises_error()
    # 日志应该包含 "业务异常: ERROR_CODE - 错误"


def test_handle_errors_logs_unexpected_error():
    """测试: 未预期异常记录 ERROR 级别日志和堆栈跟踪"""

    # Arrange
    @handle_errors
    def function_raises_unexpected():
        raise KeyError("unexpected")

    # Act & Assert
    with pytest.raises(MCPAxonError):
        function_raises_unexpected()
    # 日志应该包含 "未预期的错误" 和堆栈跟踪


def test_handle_errors_with_function_args():
    """测试: 装饰器保持函数参数正确传递"""

    # Arrange
    @handle_errors
    def function_with_args(x, y):
        return x + y

    # Act
    result = function_with_args(10, 20)

    # Assert
    assert result == 30


def test_handle_errors_with_kwargs():
    """测试: 装饰器保持关键字参数正确传递"""

    # Arrange
    @handle_errors
    def function_with_kwargs(a, b=None, c=None):
        return a

    # Act
    result = function_with_kwargs(1, b=2, c=3)

    # Assert
    assert result == 1


# ========== safe_execute decorator ==========


def test_safe_execute_successful_returns_result_dict():
    """测试: 成功执行返回结果字典"""

    # Arrange
    @safe_execute
    def successful_function():
        return "success"

    # Act
    result = successful_function()

    # Assert
    assert result == {"success": True, "data": "success"}


def test_safe_execute_mcpxon_error_returns_error_dict():
    """测试: MCPAxonError 返回错误字典"""

    # Arrange
    @safe_execute
    def function_raises_mcpxon_error():
        raise MCPAxonError("业务错误", error_code="BUSINESS_ERROR")

    # Act
    result = function_raises_mcpxon_error()

    # Assert
    assert result["success"] is False
    assert result["error"] == "业务错误"
    assert result["error_code"] == "BUSINESS_ERROR"


def test_safe_execute_generic_error_returns_generic_dict():
    """测试: 通用异常返回通用错误字典"""

    # Arrange
    @safe_execute
    def function_raises_value_error():
        raise ValueError("原始错误")

    # Act
    result = function_raises_value_error()

    # Assert
    assert result["success"] is False
    assert result["error"] == "内部服务器错误"
    assert result["error_code"] == "INTERNAL_ERROR"


def test_safe_execute_preserves_function_signature():
    """测试: 保持被装饰函数的签名"""

    # Arrange
    @safe_execute
    def function_with_args(a, b):
        return a + b

    # Act
    result = function_with_args(5, 10)

    # Assert
    assert result == {"success": True, "data": 15}


def test_safe_execute_with_function_args():
    """测试: 装饰器正确传递函数参数"""

    # Arrange
    @safe_execute
    def function_with_args(x, y, z=None):
        return x + y + (z or 0)

    # Act
    result = function_with_args(1, 2, 3)

    # Assert
    assert result == {"success": True, "data": 6}


def test_safe_execute_logs_business_warning():
    """测试: 业务异常记录 WARNING 日志"""

    # Arrange
    @safe_execute
    def function_raises_error():
        raise MCPAxonError("错误", error_code="ERROR_CODE")

    # Act
    result = function_raises_error()

    # Assert
    assert result["success"] is False
    # 日志应该包含 "业务异常: ERROR_CODE - 错误"


def test_safe_execute_logs_unexpected_error():
    """测试: 未预期异常记录 ERROR 日志和堆栈跟踪"""

    # Arrange
    @safe_execute
    def function_raises_unexpected():
        raise RuntimeError("unexpected")

    # Act
    result = function_raises_unexpected()

    # Assert
    assert result["success"] is False
    # 日志应该包含 "未预期的错误" 和堆栈跟踪


def test_safe_execute_returns_dict_with_exact_keys():
    """测试: 返回的字典具有正确的键"""

    # Arrange
    @safe_execute
    def successful_func():
        return {"key": "value"}

    # Act
    result = successful_func()

    # Assert
    assert "success" in result
    assert "data" in result
    assert result["success"] is True


def test_safe_execute_error_dict_has_correct_structure():
    """测试: 错误字典具有正确的结构"""

    # Arrange
    @safe_execute
    def error_func():
        raise MCPAxonError("错误", error_code="TEST_ERROR")

    # Act
    result = error_func()

    # Assert
    assert "success" in result
    assert "error" in result
    assert "error_code" in result
    assert result["success"] is False


# ========== Integration tests ==========


def test_handle_errors_and_safe_execute_both_work():
    """测试: handle_errors 和 safe_execute 装饰器都能正常工作"""

    # Arrange
    @handle_errors
    @safe_execute
    def double_decorated_function():
        return "result"

    # Act
    # 由于 safe_execute 先执行，handle_errors 只会看到 {"success": True, "data": "result"}
    # 不会抛出异常
    result = double_decorated_function()

    # Assert
    assert result["success"] is True
    assert result["data"] == "result"


def test_handle_errors_reraises_mcpxon_error():
    """测试: handle_errors 重新抛出原始 MCPAxonError"""
    # Arrange
    original_error = MCPAxonError("原始错误", error_code="ORIGINAL")

    @handle_errors
    def function_raises_error():
        raise original_error

    # Act & Assert
    with pytest.raises(MCPAxonError) as exc_info:
        function_raises_error()

    # 应该是同一个异常对象
    assert exc_info.value is original_error
    assert exc_info.value.error_code == "ORIGINAL"


def test_safe_execute_never_raises():
    """测试: safe_execute 永不抛出异常"""

    # Arrange
    @safe_execute
    def function_raises_error():
        raise Exception("任何错误")

    # Act
    result = function_raises_error()

    # Assert - 不应该抛出异常
    assert result["success"] is False
    assert "error" in result
