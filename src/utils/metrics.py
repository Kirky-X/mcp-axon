# Copyright (c) 2026 Kirky.X. All rights reserved.
# Licensed under the MIT License.
# See LICENSE file in the project root for full license information.

"""性能指标和监控工具"""

import time
import logging
from typing import Dict, Any, Callable, Optional
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone

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


class MetricsCollector:
    """性能指标收集器"""
    
    def __init__(self):
        self.metrics: list[PerformanceMetrics] = []
        self.operation_counts: Dict[str, int] = {}
        self.total_operations = 0
        
    def record_metric(self, metric: PerformanceMetrics) -> None:
        """记录性能指标"""
        self.metrics.append(metric)
        self.total_operations += 1
        
        # 统计操作类型
        op_type = metric.operation
        self.operation_counts[op_type] = self.operation_counts.get(op_type, 0) + 1
        
        # 记录日志
        if metric.success:
            logger.info(
                f"操作完成: {op_type}, 耗时: {metric.duration:.3f}s, "
                f"操作ID: {metric.additional_data.get('id', 'N/A') if metric.additional_data else 'N/A'}"
            )
        else:
            logger.warning(
                f"操作失败: {op_type}, 耗时: {metric.duration:.3f}s, "
                f"错误: {metric.error_message}"
            )
    
    def get_summary(self) -> Dict[str, Any]:
        """获取指标摘要"""
        if not self.metrics:
            return {"message": "暂无性能指标数据"}
        
        total_duration = sum(m.duration for m in self.metrics)
        avg_duration = total_duration / len(self.metrics)
        
        successful_ops = [m for m in self.metrics if m.success]
        failed_ops = [m for m in self.metrics if not m.success]
        
        return {
            "total_operations": self.total_operations,
            "successful_operations": len(successful_ops),
            "failed_operations": len(failed_ops),
            "average_duration": avg_duration,
            "total_duration": total_duration,
            "operation_counts": self.operation_counts.copy(),
            "fastest_operation": min((m.duration for m in self.metrics), default=0),
            "slowest_operation": max((m.duration for m in self.metrics), default=0)
        }
    
    def clear_metrics(self) -> None:
        """清空指标数据"""
        self.metrics.clear()
        self.operation_counts.clear()
        self.total_operations = 0


# 全局指标收集器
metrics_collector = MetricsCollector()


@contextmanager
def performance_monitor(operation_name: str, additional_data: Optional[Dict[str, Any]] = None):
    """性能监控上下文管理器"""
    start_time = time.time()
    start_dt = datetime.now(timezone.utc)
    
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
            additional_data=additional_data
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
            additional_data=additional_data
        )
        
        metrics_collector.record_metric(metric)
        raise

def monitored_function(operation_name: str):
    """装饰器：监控函数性能"""
    def decorator(func: Callable) -> Callable:
        def wrapper(*args, **kwargs):
            # 尝试从参数中提取ID信息用于监控
            additional_data = {}
            if args and hasattr(args[0], '__class__'):
                # 如果是类方法，可能包含ID信息
                pass
            # 可以根据具体需要从参数中提取更多数据
            
            with performance_monitor(operation_name, additional_data):
                return func(*args, **kwargs)
        return wrapper
    return decorator


# 使用示例
if __name__ == "__main__":
    # 示例：监控操作
    with performance_monitor("test_operation", {"id": "test123"}):
        time.sleep(0.1)  # 模拟耗时操作
    
    print("指标摘要:", metrics_collector.get_summary())