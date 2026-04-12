# Copyright (c) 2026 Kirky.X. All rights reserved.
# Licensed under the MIT License.
# See LICENSE file in the project root for full license information.

"""错误处理器测试"""

from src.utils.error_handler import get_safe_error_message

# ========== get_safe_error_message ==========


def test_get_safe_error_message_known_business_exception():
    """测试: 已知业务异常返回原始消息"""
    message = "项目不存在: abc-123"
    result = get_safe_error_message(message)
    assert result == message


def test_get_safe_error_message_unknown_exception():
    """测试: 未知异常返回通用消息"""
    message = "数据库连接失败: host=db.example.com port=5432 user=admin password=secret"
    result = get_safe_error_message(message)
    assert result == "操作失败，请稍后重试"
    assert "db.example.com" not in result
    assert "password" not in result


def test_get_safe_error_message_empty_string():
    """测试: 空字符串返回通用消息"""
    result = get_safe_error_message("")
    assert result == "操作失败，请稍后重试"


def test_get_safe_error_message_stack_trace_blocked():
    """测试: 堆栈跟踪被过滤"""
    message = "File '/secret/path/app.py', line 42, in foo: KeyError('internal detail')"
    result = get_safe_error_message(message)
    assert result == "操作失败，请稍后重试"
    assert "/secret/path" not in result


def test_get_safe_error_message_chinese_known_prefix():
    """测试: 中文已知前缀的消息被放行"""
    for prefix in [
        "锁获取成功",
        "项目已锁定",
        "需求不存在",
        "参数必须是字典",
        "无法完成操作",
    ]:
        result = get_safe_error_message(f"{prefix}: 详细信息")
        assert result == f"{prefix}: 详细信息", f"Failed for: {prefix}"
