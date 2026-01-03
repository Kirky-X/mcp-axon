# Copyright (c) 2026 Kirky.X. All rights reserved.
# Licensed under the MIT License.
# See LICENSE file in the project root for full license information.

"""Prometheus 指标导出器

将性能监控指标导出为 Prometheus 格式
"""

import logging
import time
from collections import defaultdict
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class PrometheusMetricsExporter:
    """
    Prometheus 指标导出器

    将内部指标转换为 Prometheus 格式
    """

    def __init__(self, prefix: str = "mcp_axon"):
        """
        初始化导出器

        Args:
            prefix: 指标前缀
        """
        self.prefix = prefix
        self.metrics: Dict[str, Dict] = defaultdict(dict)

    def export_gauge(
        self, name: str, value: float, labels: Optional[Dict[str, str]] = None
    ):
        """
        导出 Gauge 指标

        Args:
            name: 指标名称
            value: 指标值
            labels: 标签
        """
        metric_name = f"{self.prefix}_{name}"
        self.metrics[metric_name]["type"] = "gauge"
        self.metrics[metric_name]["value"] = value
        self.metrics[metric_name]["labels"] = labels or {}

    def export_counter(
        self, name: str, value: float, labels: Optional[Dict[str, str]] = None
    ):
        """
        导出 Counter 指标

        Args:
            name: 指标名称
            value: 指标值
            labels: 标签
        """
        metric_name = f"{self.prefix}_{name}"
        self.metrics[metric_name]["type"] = "counter"
        self.metrics[metric_name]["value"] = value
        self.metrics[metric_name]["labels"] = labels or {}

    def export_histogram(
        self,
        name: str,
        value: float,
        buckets: List[float],
        labels: Optional[Dict[str, str]] = None,
    ):
        """
        导出 Histogram 指标

        Args:
            name: 指标名称
            value: 指标值
            buckets: 分桶边界
            labels: 标签
        """
        metric_name = f"{self.prefix}_{name}"
        self.metrics[metric_name]["type"] = "histogram"
        self.metrics[metric_name]["value"] = value
        self.metrics[metric_name]["buckets"] = buckets
        self.metrics[metric_name]["labels"] = labels or {}

    def export_summary(
        self,
        name: str,
        value: float,
        quantiles: List[float],
        labels: Optional[Dict[str, str]] = None,
    ):
        """
        导出 Summary 指标

        Args:
            name: 指标名称
            value: 指标值
            quantiles: 分位数
            labels: 标签
        """
        metric_name = f"{self.prefix}_{name}"
        self.metrics[metric_name]["type"] = "summary"
        self.metrics[metric_name]["value"] = value
        self.metrics[metric_name]["quantiles"] = quantiles
        self.metrics[metric_name]["labels"] = labels or {}

    def export_from_metrics_collector(self, metrics_summary: Dict):
        """
        从指标收集器导出数据

        Args:
            metrics_summary: 指标摘要
        """
        timestamp = int(time.time())

        # 导出通用指标
        if "general" in metrics_summary:
            general = metrics_summary["general"]
            if "total_operations" in general:
                self.export_counter(
                    "total_operations",
                    general["total_operations"],
                    {"timestamp": str(timestamp)},
                )
            if "successful_operations" in general:
                self.export_counter(
                    "successful_operations",
                    general["successful_operations"],
                    {"timestamp": str(timestamp)},
                )
            if "failed_operations" in general:
                self.export_counter(
                    "failed_operations",
                    general["failed_operations"],
                    {"timestamp": str(timestamp)},
                )
            if "average_duration" in general:
                self.export_gauge(
                    "average_duration_seconds",
                    general["average_duration"],
                    {"timestamp": str(timestamp)},
                )

        # 导出数据库指标
        if "database" in metrics_summary:
            db = metrics_summary["database"]
            if "total_queries" in db:
                self.export_counter(
                    "db_total_queries",
                    db["total_queries"],
                    {"timestamp": str(timestamp)},
                )
            if "average_duration" in db:
                self.export_gauge(
                    "db_average_duration_seconds",
                    db["average_duration"],
                    {"timestamp": str(timestamp)},
                )

        # 导出 API 指标
        if "api" in metrics_summary:
            api = metrics_summary["api"]
            if "total_calls" in api:
                self.export_counter(
                    "api_total_calls", api["total_calls"], {"timestamp": str(timestamp)}
                )
            if "average_duration" in api:
                self.export_gauge(
                    "api_average_duration_seconds",
                    api["average_duration"],
                    {"timestamp": str(timestamp)},
                )

    def format_prometheus(self) -> str:
        """
        格式化为 Prometheus 文本格式

        Returns:
            Prometheus 格式的文本
        """
        lines = []

        for metric_name, metric_data in self.metrics.items():
            metric_type = metric_data.get("type", "gauge")
            value = metric_data.get("value", 0)
            labels = metric_data.get("labels", {})

            # 添加类型注释
            lines.append(f"# TYPE {metric_name} {metric_type}")

            # 格式化标签
            label_str = ""
            if labels:
                label_pairs = [f'{k}="{v}"' for k, v in labels.items()]
                label_str = "{" + ", ".join(label_pairs) + "}"

            # 添加指标值
            lines.append(f"{metric_name}{label_str} {value}")

            # 如果是 histogram，添加桶
            if metric_type == "histogram" and "buckets" in metric_data:
                buckets = metric_data["buckets"]
                for bucket in buckets:
                    bucket_value = 1 if value <= bucket else 0
                    lines.append(
                        f'{metric_name}_bucket{{le="{bucket}"}}{label_str} {bucket_value}'
                    )
                lines.append(f'{metric_name}_bucket{{le="+Inf"}}{label_str} 1')
                lines.append(f"{metric_name}_sum{label_str} {value}")
                lines.append(f"{metric_name}_count{label_str} 1")

            # 如果是 summary，添加分位数
            if metric_type == "summary" and "quantiles" in metric_data:
                quantiles = metric_data["quantiles"]
                for quantile in quantiles:
                    lines.append(
                        f'{metric_name}{{quantile="{quantile}"}}{label_str} {value}'
                    )
                lines.append(f"{metric_name}_sum{label_str} {value}")
                lines.append(f"{metric_name}_count{label_str} 1")

            lines.append("")  # 空行分隔

        return "\n".join(lines)

    def clear_metrics(self):
        """清空所有指标"""
        self.metrics.clear()

    def get_metrics(self) -> Dict:
        """
        获取所有指标

        Returns:
            指标字典
        """
        return dict(self.metrics)


# 全局导出器实例
prometheus_exporter = PrometheusMetricsExporter()


def export_metrics_to_prometheus(metrics_summary: Dict) -> str:
    """
    导出指标到 Prometheus 格式

    Args:
        metrics_summary: 指标摘要

    Returns:
        Prometheus 格式的文本
    """
    prometheus_exporter.clear_metrics()
    prometheus_exporter.export_from_metrics_collector(metrics_summary)
    return prometheus_exporter.format_prometheus()


# 使用示例
if __name__ == "__main__":
    # 示例导出
    summary = {
        "general": {
            "total_operations": 100,
            "successful_operations": 95,
            "failed_operations": 5,
            "average_duration": 0.5,
        },
        "database": {
            "total_queries": 50,
            "average_duration": 0.1,
        },
        "api": {
            "total_calls": 30,
            "average_duration": 0.2,
        },
    }

    prometheus_text = export_metrics_to_prometheus(summary)
    print(prometheus_text)
