# Copyright (c) 2026 Kirky.X. All rights reserved.
# Licensed under the MIT License.
# See LICENSE file in the project root for full license information.

"""性能监控工具测试"""

import time

import pytest

from src.utils.metrics import (
    metrics_collector,
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
    with performance_monitor("test_operation", {"id": "test123"}):
        time.sleep(0.01)

    summary = metrics_collector.get_summary()
    assert summary["total_operations"] >= 1
    assert summary["successful_operations"] >= 1


def test_performance_monitor_context_manager_failure():
    """测试性能监控上下文管理器 - 失败场景"""
    with pytest.raises(ValueError, match="Test error"):
        with performance_monitor("test_operation"):
            time.sleep(0.01)
            raise ValueError("Test error")

    summary = metrics_collector.get_summary()
    assert summary["failed_operations"] >= 1


def test_performance_monitor_multiple_operations():
    """测试性能监控 - 多个操作"""
    operations = ["op1", "op2", "op3"]

    for op in operations:
        with performance_monitor(op):
            time.sleep(0.01)

    summary = metrics_collector.get_summary()
    assert summary["total_operations"] >= 3
    assert "op1" in summary["operation_counts"]
    assert "op2" in summary["operation_counts"]
    assert "op3" in summary["operation_counts"]


def test_performance_monitor_nested():
    """测试性能监控 - 嵌套调用"""
    with performance_monitor("outer"):
        time.sleep(0.01)
        with performance_monitor("inner"):
            time.sleep(0.01)

    summary = metrics_collector.get_summary()
    assert summary["total_operations"] >= 2


def test_performance_monitor_very_fast_operation():
    """测试性能监控 - 极快操作"""
    with performance_monitor("fast_operation"):
        result = "fast"

    assert result == "fast"
    summary = metrics_collector.get_summary()
    assert summary["total_operations"] >= 1


def test_performance_monitor_slow_operation():
    """测试性能监控 - 慢操作"""
    with performance_monitor("slow_operation"):
        time.sleep(0.1)

    summary = metrics_collector.get_summary()
    assert summary["total_operations"] >= 1
    assert summary["slowest_operation"] >= 0.1


def test_performance_monitor_context_manager_with_exception():
    """测试性能监控上下文管理器 - 异常场景"""
    with pytest.raises(RuntimeError, match="Test runtime error"):
        with performance_monitor("test_operation"):
            time.sleep(0.01)
            raise RuntimeError("Test runtime error")

    summary = metrics_collector.get_summary()
    assert summary["failed_operations"] >= 1


def test_metrics_collector_clear():
    """测试指标收集器清空"""
    with performance_monitor("test1"):
        time.sleep(0.01)

    metrics_collector.clear_metrics()

    summary = metrics_collector.get_summary()
    assert summary["message"] == "暂无性能指标数据"


def test_metrics_collector_summary():
    """测试指标收集器摘要"""
    metrics_collector.clear_metrics()

    with performance_monitor("op1"):
        time.sleep(0.01)

    with performance_monitor("op2"):
        time.sleep(0.02)

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
