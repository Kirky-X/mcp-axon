# Copyright (c) 2026 Kirky.X. All rights reserved.
# Licensed under the MIT License.
# See LICENSE file in the project root for full license information.

"""性能监控工具测试"""

import time

import pytest

from src.utils.metrics import (
    metrics_collector,
    monitored_function,
    performance_monitor,
)


@pytest.fixture(autouse=True)
def reset_metrics():
    """每个测试前清空指标"""
    metrics_collector.clear_metrics()
    yield
    metrics_collector.clear_metrics()


def test_performance_monitor_context_manager_success():
    """测试性能监控上下文管理器 - 成功场景"""

    # Arrange & Act
    with performance_monitor("test_operation", {"id": "test123"}):
        time.sleep(0.01)

    # Assert - 应该记录成功
    summary = metrics_collector.get_summary()
    assert summary["total_operations"] >= 1
    assert summary["successful_operations"] >= 1


def test_performance_monitor_context_manager_failure():
    """测试性能监控上下文管理器 - 失败场景"""

    # Arrange & Act & Assert
    with pytest.raises(ValueError, match="Test error"):
        with performance_monitor("test_operation"):
            time.sleep(0.01)
            raise ValueError("Test error")

    # 应该记录失败
    summary = metrics_collector.get_summary()
    assert summary["failed_operations"] >= 1


def test_monitored_function_decorator():
    """测试监控函数装饰器"""

    # Arrange
    @monitored_function("test_func")
    def test_func():
        time.sleep(0.01)
        return "success"

    # Act
    result = test_func()

    # Assert
    assert result == "success"
    summary = metrics_collector.get_summary()
    assert summary["total_operations"] >= 1


def test_monitored_function_with_exception():
    """测试监控函数装饰器 - 异常场景"""

    # Arrange
    @monitored_function("test_func_error")
    def test_func():
        time.sleep(0.01)
        raise ValueError("Test error")

    # Act & Assert
    with pytest.raises(ValueError, match="Test error"):
        test_func()

    summary = metrics_collector.get_summary()
    assert summary["failed_operations"] >= 1


def test_performance_monitor_multiple_operations():
    """测试性能监控 - 多个操作"""

    # Arrange
    operations = ["op1", "op2", "op3"]

    # Act
    for op in operations:
        with performance_monitor(op):
            time.sleep(0.01)

    # Assert
    summary = metrics_collector.get_summary()
    assert summary["total_operations"] >= 3
    assert "op1" in summary["operation_counts"]
    assert "op2" in summary["operation_counts"]
    assert "op3" in summary["operation_counts"]


def test_performance_monitor_nested():
    """测试性能监控 - 嵌套调用"""

    # Arrange & Act
    with performance_monitor("outer"):
        time.sleep(0.01)
        with performance_monitor("inner"):
            time.sleep(0.01)

    # Assert - 应该正确处理嵌套调用
    summary = metrics_collector.get_summary()
    assert summary["total_operations"] >= 2


def test_performance_monitor_very_fast_operation():
    """测试性能监控 - 极快操作"""

    # Arrange & Act
    with performance_monitor("fast_operation"):
        result = "fast"

    # Assert
    assert result == "fast"
    summary = metrics_collector.get_summary()
    assert summary["total_operations"] >= 1


def test_performance_monitor_slow_operation():
    """测试性能监控 - 慢操作"""

    # Arrange & Act
    with performance_monitor("slow_operation"):
        time.sleep(0.1)

    # Assert
    summary = metrics_collector.get_summary()
    assert summary["total_operations"] >= 1
    assert summary["slowest_operation"] >= 0.1


def test_performance_monitor_context_manager_with_exception():
    """测试性能监控上下文管理器 - 异常场景"""

    # Arrange & Act & Assert
    with pytest.raises(RuntimeError, match="Test runtime error"):
        with performance_monitor("test_operation"):
            time.sleep(0.01)
            raise RuntimeError("Test runtime error")

    summary = metrics_collector.get_summary()
    assert summary["failed_operations"] >= 1


def test_monitored_function_class_method():
    """测试监控函数装饰器 - 类方法"""

    # Arrange
    class TestClass:
        @monitored_function("method_operation")
        def test_method(self):
            time.sleep(0.01)
            return "method_result"

    # Act
    obj = TestClass()
    result = obj.test_method()

    # Assert
    assert result == "method_result"
    summary = metrics_collector.get_summary()
    assert summary["total_operations"] >= 1


def test_monitored_function_static_method():
    """测试监控函数装饰器 - 静态方法"""

    # Arrange
    class TestClass:
        @staticmethod
        @monitored_function("static_operation")
        def test_static():
            time.sleep(0.01)
            return "static_result"

    # Act
    result = TestClass.test_static()

    # Assert
    assert result == "static_result"


def test_monitored_function_with_args():
    """测试监控函数装饰器 - 带参数的函数"""

    # Arrange
    @monitored_function("test_func")
    def test_func(a, b, c=None):
        time.sleep(0.01)
        return a + b + (c or 0)

    # Act
    result = test_func(1, 2, c=3)

    # Assert
    assert result == 6


def test_metrics_collector_clear():
    """测试指标收集器清空"""

    # Arrange - 添加一些指标
    with performance_monitor("test1"):
        time.sleep(0.01)

    # Act - 清空
    metrics_collector.clear_metrics()

    # Assert
    summary = metrics_collector.get_summary()
    assert summary["message"] == "暂无性能指标数据"


def test_metrics_collector_summary():
    """测试指标收集器摘要"""

    # Arrange - 清空之前的指标
    metrics_collector.clear_metrics()

    # Act - 添加一些指标
    with performance_monitor("op1"):
        time.sleep(0.01)

    with performance_monitor("op2"):
        time.sleep(0.02)

    # Assert
    summary = metrics_collector.get_summary()
    assert summary["total_operations"] == 2
    assert summary["successful_operations"] == 2
    assert summary["failed_operations"] == 0
    assert summary["average_duration"] > 0
    assert summary["total_duration"] > 0
    assert summary["fastest_operation"] > 0
    assert summary["slowest_operation"] > 0
    assert "op1" in summary["operation_counts"]
    assert "op2" in summary["operation_counts"]
