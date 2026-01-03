# Copyright (c) 2026 Kirky.X. All rights reserved.
# Licensed under the MIT License.
# See LICENSE file in the project root for full license information.

"""性能指标和监控工具（增强版）"""

import logging
import time
from collections import defaultdict
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class PerformanceMetrics:
    """性能指标数据类"""

    operation: str
    duration: float
    start_time: datetime
    end_time: datetime
    success: bool
    error_message: Optional[str] = None
    additional_data: Optional[Dict[str, Any]] = None
    trace_id: Optional[str] = None


@dataclass
class DatabaseMetrics:
    """数据库性能指标"""

    query_type: str
    table_name: str
    duration: float
    rows_affected: int
    timestamp: datetime
    success: bool


@dataclass
class APIMetrics:
    """API 性能指标"""

    endpoint: str
    method: str
    status_code: int
    duration: float
    timestamp: datetime
    success: bool


class MetricsCollector:
    """性能指标收集器（增强版）"""

    def __init__(self):
        self.metrics: List[PerformanceMetrics] = []
        self.operation_counts: Dict[str, int] = defaultdict(int)
        self.total_operations = 0

        # 数据库指标
        self.db_metrics: List[DatabaseMetrics] = []
        self.db_query_counts: Dict[str, int] = defaultdict(int)

        # API 指标
        self.api_metrics: List[APIMetrics] = []
        self.api_call_counts: Dict[str, int] = defaultdict(int)

        # 错误统计
        self.error_counts: Dict[str, int] = defaultdict(int)

        # 性能阈值（用于告警）
        self.performance_thresholds = {
            "slow_operation": 1.0,  # 秒
            "slow_db_query": 0.5,  # 秒
            "slow_api_call": 0.5,  # 秒
        }

    def record_metric(self, metric: PerformanceMetrics) -> None:
        """记录性能指标"""
        self.metrics.append(metric)
        self.total_operations += 1

        # 统计操作类型
        op_type = metric.operation
        self.operation_counts[op_type] += 1

        # 统计错误
        if not metric.success:
            error_type = metric.error_message or "UnknownError"
            self.error_counts[error_type] += 1

        # 记录日志
        if metric.success:
            logger.info(
                f"操作完成: {op_type}, 耗时: {metric.duration:.3f}s, "
                f"操作ID: {metric.additional_data.get('id', 'N/A') if metric.additional_data else 'N/A'}"
            )

            # 性能告警
            if metric.duration > self.performance_thresholds["slow_operation"]:
                logger.warning(
                    f"慢操作告警: {op_type}, 耗时: {metric.duration:.3f}s "
                    f"超过阈值 {self.performance_thresholds['slow_operation']}s"
                )
        else:
            logger.warning(
                f"操作失败: {op_type}, 耗时: {metric.duration:.3f}s, "
                f"错误: {metric.error_message}"
            )

    def record_db_metric(self, metric: DatabaseMetrics) -> None:
        """记录数据库指标"""
        self.db_metrics.append(metric)
        self.db_query_counts[f"{metric.query_type}:{metric.table_name}"] += 1

        # 记录日志
        if metric.success:
            logger.debug(
                f"数据库查询: {metric.query_type} {metric.table_name}, "
                f"耗时: {metric.duration:.3f}s, 影响行数: {metric.rows_affected}"
            )

            # 性能告警
            if metric.duration > self.performance_thresholds["slow_db_query"]:
                logger.warning(
                    f"慢查询告警: {metric.query_type} {metric.table_name}, "
                    f"耗时: {metric.duration:.3f}s "
                    f"超过阈值 {self.performance_thresholds['slow_db_query']}s"
                )
        else:
            logger.error(
                f"数据库查询失败: {metric.query_type} {metric.table_name}, "
                f"耗时: {metric.duration:.3f}s"
            )

    def record_api_metric(self, metric: APIMetrics) -> None:
        """记录 API 指标"""
        self.api_metrics.append(metric)
        self.api_call_counts[f"{metric.method}:{metric.endpoint}"] += 1

        # 记录日志
        if metric.success:
            logger.info(
                f"API 调用: {metric.method} {metric.endpoint}, "
                f"状态: {metric.status_code}, 耗时: {metric.duration:.3f}s"
            )

            # 性能告警
            if metric.duration > self.performance_thresholds["slow_api_call"]:
                logger.warning(
                    f"慢 API 告警: {metric.method} {metric.endpoint}, "
                    f"耗时: {metric.duration:.3f}s "
                    f"超过阈值 {self.performance_thresholds['slow_api_call']}s"
                )
        else:
            logger.error(
                f"API 调用失败: {metric.method} {metric.endpoint}, "
                f"状态: {metric.status_code}, 耗时: {metric.duration:.3f}s"
            )

    def get_summary(self) -> Dict[str, Any]:
        """获取指标摘要（保持向后兼容）"""
        summary: Dict[str, Any] = {"timestamp": datetime.now(timezone.utc).isoformat()}

        # 通用指标
        if self.metrics:
            total_duration = sum(m.duration for m in self.metrics)
            avg_duration = total_duration / len(self.metrics)

            successful_ops = [m for m in self.metrics if m.success]
            failed_ops = [m for m in self.metrics if not m.success]

            # 向后兼容：直接在顶层返回这些字段
            summary["total_operations"] = self.total_operations
            summary["successful_operations"] = len(successful_ops)
            summary["failed_operations"] = len(failed_ops)
            summary["average_duration"] = avg_duration
            summary["total_duration"] = total_duration
            summary["operation_counts"] = dict(self.operation_counts)
            summary["fastest_operation"] = min(
                (m.duration for m in self.metrics), default=0
            )
            summary["slowest_operation"] = max(
                (m.duration for m in self.metrics), default=0
            )

            # 新增：嵌套结构
            summary["general"] = {
                "total_operations": self.total_operations,
                "successful_operations": len(successful_ops),
                "failed_operations": len(failed_ops),
                "success_rate": len(successful_ops) / len(self.metrics) * 100,
                "average_duration": avg_duration,
                "total_duration": total_duration,
                "operation_counts": dict(self.operation_counts),
                "fastest_operation": min((m.duration for m in self.metrics), default=0),
                "slowest_operation": max((m.duration for m in self.metrics), default=0),
            }
        else:
            # 向后兼容：当没有指标时，返回 message
            summary["message"] = "暂无性能指标数据"
            summary["total_operations"] = 0
            summary["successful_operations"] = 0
            summary["failed_operations"] = 0
            summary["average_duration"] = 0
            summary["total_duration"] = 0
            summary["operation_counts"] = {}
            summary["fastest_operation"] = 0
            summary["slowest_operation"] = 0
            summary["general"] = {"message": "暂无性能指标数据"}

        # 数据库指标
        if self.db_metrics:
            avg_db_duration = sum(m.duration for m in self.db_metrics) / len(
                self.db_metrics
            )
            summary["database"] = {
                "total_queries": len(self.db_metrics),
                "average_duration": avg_db_duration,
                "query_counts": dict(self.db_query_counts),
            }

        # API 指标
        if self.api_metrics:
            avg_api_duration = sum(m.duration for m in self.api_metrics) / len(
                self.api_metrics
            )
            successful_apis = [m for m in self.api_metrics if m.success]
            summary["api"] = {
                "total_calls": len(self.api_metrics),
                "successful_calls": len(successful_apis),
                "average_duration": avg_api_duration,
                "call_counts": dict(self.api_call_counts),
            }

        # 错误统计
        if self.error_counts:
            summary["errors"] = dict(self.error_counts)

        return summary

    def get_slow_operations(self, limit: int = 10) -> List[Dict[str, Any]]:
        """获取最慢的操作"""
        sorted_metrics = sorted(self.metrics, key=lambda m: m.duration, reverse=True)
        return [
            {
                "operation": m.operation,
                "duration": m.duration,
                "timestamp": m.start_time.isoformat(),
                "success": m.success,
                "error": m.error_message,
            }
            for m in sorted_metrics[:limit]
        ]

    def get_slow_db_queries(self, limit: int = 10) -> List[Dict[str, Any]]:
        """获取最慢的数据库查询"""
        sorted_metrics = sorted(self.db_metrics, key=lambda m: m.duration, reverse=True)
        return [
            {
                "query_type": m.query_type,
                "table_name": m.table_name,
                "duration": m.duration,
                "rows_affected": m.rows_affected,
                "timestamp": m.timestamp.isoformat(),
            }
            for m in sorted_metrics[:limit]
        ]

    def clear_metrics(self) -> None:
        """清空指标数据"""
        self.metrics.clear()
        self.operation_counts.clear()
        self.total_operations = 0
        self.db_metrics.clear()
        self.db_query_counts.clear()
        self.api_metrics.clear()
        self.api_call_counts.clear()
        self.error_counts.clear()


# 全局指标收集器
metrics_collector = MetricsCollector()


@contextmanager
def performance_monitor(
    operation_name: str, additional_data: Optional[Dict[str, Any]] = None
):
    """性能监控上下文管理器"""
    start_time = time.time()
    start_dt = datetime.now(timezone.utc)
    trace_id = additional_data.get("trace_id") if additional_data else None

    try:
        yield
        # 操作成功完成
        end_time = time.time()
        end_dt = datetime.now(timezone.utc)

        duration = end_time - start_time

        metric = PerformanceMetrics(
            operation=operation_name,
            duration=duration,
            start_time=start_dt,
            end_time=end_dt,
            success=True,
            additional_data=additional_data,
            trace_id=trace_id,
        )

        metrics_collector.record_metric(metric)

    except Exception as e:
        # 操作失败
        end_time = time.time()
        end_dt = datetime.now(timezone.utc)

        duration = end_time - start_time

        metric = PerformanceMetrics(
            operation=operation_name,
            duration=duration,
            start_time=start_dt,
            end_time=end_dt,
            success=False,
            error_message=str(e),
            additional_data=additional_data,
            trace_id=trace_id,
        )

        metrics_collector.record_metric(metric)
        raise


def monitored_function(operation_name: str):
    """装饰器：监控函数性能"""

    def decorator(func: Callable) -> Callable:
        def wrapper(*args, **kwargs):
            # 尝试从参数中提取ID信息用于监控
            additional_data = {}
            if args and hasattr(args[0], "__class__"):
                # 如果是类方法，可能包含ID信息
                pass
            # 可以根据具体需要从参数中提取更多数据

            with performance_monitor(operation_name, additional_data):
                return func(*args, **kwargs)

        return wrapper

    return decorator


@contextmanager
def db_query_monitor(query_type: str, table_name: str):
    """数据库查询监控上下文管理器"""
    start_time = time.time()
    start_dt = datetime.now(timezone.utc)
    rows_affected = 0

    try:
        yield
        rows_affected = 1  # 默认值，实际应该从查询结果中获取
    except Exception:
        rows_affected = 0
        raise
    finally:
        end_time = time.time()
        duration = end_time - start_time

        metric = DatabaseMetrics(
            query_type=query_type,
            table_name=table_name,
            duration=duration,
            rows_affected=rows_affected,
            timestamp=start_dt,
            success=True,
        )

        metrics_collector.record_db_metric(metric)


# 使用示例
if __name__ == "__main__":
    # 示例：监控操作
    with performance_monitor("test_operation", {"id": "test123"}):
        time.sleep(0.1)  # 模拟耗时操作

    print("指标摘要:", metrics_collector.get_summary())
