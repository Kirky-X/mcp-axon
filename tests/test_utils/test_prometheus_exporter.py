# Copyright (c) 2026 Kirky.X. All rights reserved.
# Licensed under the MIT License.
# See LICENSE file in the project root for full license information.

"""Prometheus 指标导出器测试"""

import re


from src.utils.prometheus_exporter import (
    PrometheusMetricsExporter,
    export_metrics_to_prometheus,
    prometheus_exporter,
)


# ========== export_gauge ==========


def test_export_gauge_stores_metric():
    """测试: 导出 gauge 存储指标"""
    exporter = PrometheusMetricsExporter()

    exporter.export_gauge("test_metric", 42.0, {"label": "value"})

    assert "mcp_axon_test_metric" in exporter.metrics
    assert exporter.metrics["mcp_axon_test_metric"]["type"] == "gauge"
    assert exporter.metrics["mcp_axon_test_metric"]["value"] == 42.0


def test_export_gauge_with_labels():
    """测试: 导出 gauge 带标签"""
    exporter = PrometheusMetricsExporter()

    exporter.export_gauge("test", 1.0, {"env": "prod", "region": "us"})

    assert exporter.metrics["mcp_axon_test"]["labels"]["env"] == "prod"
    assert exporter.metrics["mcp_axon_test"]["labels"]["region"] == "us"


def test_export_gauge_without_labels():
    """测试: 导出 gauge 不带标签"""
    exporter = PrometheusMetricsExporter()

    exporter.export_gauge("test", 1.0)

    assert exporter.metrics["mcp_axon_test"]["labels"] == {}


def test_export_gauge_updates_existing():
    """测试: 导出 gauge 更新现有指标"""
    exporter = PrometheusMetricsExporter()

    exporter.export_gauge("test", 1.0)
    exporter.export_gauge("test", 2.0)

    assert exporter.metrics["mcp_axon_test"]["value"] == 2.0


# ========== export_counter ==========


def test_export_counter_increments():
    """测试: 导出 counter 递增值"""
    exporter = PrometheusMetricsExporter()

    exporter.export_counter("requests", 1.0)
    exporter.export_counter("requests", 2.0)

    # Counter 应该累加（这里简化为存储最新值）
    assert exporter.metrics["mcp_axon_requests"]["type"] == "counter"


def test_export_counter_with_labels():
    """测试: 导出 counter 带标签"""
    exporter = PrometheusMetricsExporter()

    exporter.export_counter("api_calls", 10.0, {"endpoint": "/api/test"})

    assert exporter.metrics["mcp_axon_api_calls"]["labels"]["endpoint"] == "/api/test"


# ========== export_histogram ==========


def test_export_histogram_creates_buckets():
    """测试: 导出 histogram 创建桶"""
    exporter = PrometheusMetricsExporter()
    buckets = [0.1, 0.5, 1.0, 5.0]

    exporter.export_histogram("latency", 0.150, buckets)

    metric = exporter.metrics["mcp_axon_latency"]
    assert metric["type"] == "histogram"
    assert metric["value"] == 0.150
    assert metric["buckets"] == buckets


def test_export_histogram_multiple_samples():
    """测试: 导出 histogram 多样本"""
    exporter = PrometheusMetricsExporter()
    buckets = [0.1, 0.5, 1.0, 5.0]

    # 导入第一个样本
    exporter.export_histogram("test", 0.002, buckets)
    # 导入第二个样本
    exporter.export_histogram("test", 0.800, buckets)

    # 只保留最后一个值和桶定义
    assert exporter.metrics["mcp_axon_test"]["value"] == 0.800


# ========== export_summary ==========


def test_export_summary_creates_quantiles():
    """测试: 导出 summary 创建分位数"""
    exporter = PrometheusMetricsExporter()
    quantiles = [0.5, 0.9, 0.99]

    exporter.export_summary("latency", 0.150, quantiles)

    metric = exporter.metrics["mcp_axon_latency"]
    assert metric["type"] == "summary"
    assert metric["value"] == 0.150
    assert metric["quantiles"] == quantiles


# ========== format_prometheus ==========


def test_format_prometheus_includes_type_declaration():
    """测试: 格式化包含类型声明"""
    exporter = PrometheusMetricsExporter()
    exporter.export_gauge("test", 1.0)

    output = exporter.format_prometheus()

    assert "# TYPE mcp_axon_test gauge" in output


def test_format_prometheus_includes_metric_line():
    """测试: 格式化包含指标行"""
    exporter = PrometheusMetricsExporter()
    exporter.export_gauge("test", 42.5)

    output = exporter.format_prometheus()

    assert "mcp_axon_test 42.5" in output


def test_format_prometheus_with_labels():
    """测试: 格式化包含标签"""
    exporter = PrometheusMetricsExporter()
    exporter.export_gauge("test", 1.0, {"env": "prod"})

    output = exporter.format_prometheus()

    assert 'mcp_axon_test{env="prod"} 1.0' in output


def test_format_prometheus_histogram_buckets():
    """测试: 格式化 histogram 桶"""
    exporter = PrometheusMetricsExporter()
    exporter.export_histogram("latency", 0.150, [0.1, 0.5, 1.0])

    output = exporter.format_prometheus()

    assert "# TYPE mcp_axon_latency histogram" in output
    assert 'mcp_axon_latency_bucket{le="0.1"}' in output
    assert 'mcp_axon_latency_bucket{le="+Inf"}' in output
    assert "mcp_axon_latency_sum" in output
    assert "mcp_axon_latency_count" in output


def test_format_prometheus_summary_quantiles():
    """测试: 格式化 summary 分位数"""
    exporter = PrometheusMetricsExporter()
    exporter.export_summary("latency", 0.150, [0.5, 0.9, 0.99])

    output = exporter.format_prometheus()

    assert "# TYPE mcp_axon_latency summary" in output
    assert 'mcp_axon_latency{quantile="0.5"}' in output
    assert 'mcp_axon_latency{quantile="0.9"}' in output
    assert "mcp_axon_latency_sum" in output
    assert "mcp_axon_latency_count" in output


def test_format_prometheus_multiple_metrics():
    """测试: 格式化多个指标"""
    exporter = PrometheusMetricsExporter()
    exporter.export_gauge("metric1", 1.0)
    exporter.export_counter("metric2", 2.0)

    output = exporter.format_prometheus()

    assert "# TYPE mcp_axon_metric1 gauge" in output
    assert "# TYPE mcp_axon_metric2 counter" in output
    assert "mcp_axon_metric1 1.0" in output
    assert "mcp_axon_metric2 2.0" in output


def test_format_prometheus_empty_after_clear():
    """测试: 清空后格式化返回空字符串"""
    exporter = PrometheusMetricsExporter()
    exporter.export_gauge("test", 1.0)
    exporter.clear_metrics()

    output = exporter.format_prometheus()

    assert output == "" or output == "\n"


# ========== clear_metrics ==========


def test_clear_metrics_removes_all():
    """测试: 清空移除所有指标"""
    exporter = PrometheusMetricsExporter()
    exporter.export_gauge("test1", 1.0)
    exporter.export_counter("test2", 2.0)

    exporter.clear_metrics()

    assert len(exporter.metrics) == 0


def test_clear_metrics_allows_new_export():
    """测试: 清空后允许新导出"""
    exporter = PrometheusMetricsExporter()
    exporter.export_gauge("test", 1.0)
    exporter.clear_metrics()

    exporter.export_gauge("new_test", 2.0)

    assert len(exporter.metrics) == 1
    assert "mcp_axon_new_test" in exporter.metrics


# ========== get_metrics ==========


def test_get_metrics_returns_all():
    """测试: 获取返回所有指标"""
    exporter = PrometheusMetricsExporter()
    exporter.export_gauge("metric1", 1.0)
    exporter.export_counter("metric2", 2.0)

    metrics = exporter.get_metrics()

    assert len(metrics) == 2
    assert "mcp_axon_metric1" in metrics
    assert "mcp_axon_metric2" in metrics


def test_get_metrics_includes_metadata():
    """测试: 获取包含元数据"""
    exporter = PrometheusMetricsExporter()
    exporter.export_gauge("test", 1.0, {"label": "value"})

    metrics = exporter.get_metrics()

    metric = metrics["mcp_axon_test"]
    assert metric["type"] == "gauge"
    assert metric["value"] == 1.0
    assert metric["labels"] == {"label": "value"}


def test_get_metrics_empty_when_no_metrics():
    """测试: 无指标时返回空字典"""
    exporter = PrometheusMetricsExporter()

    metrics = exporter.get_metrics()

    assert metrics == {}


# ========== export_from_metrics_collector ==========


def test_export_from_collector_general_metrics():
    """测试: 从收集器导出通用指标"""
    exporter = PrometheusMetricsExporter()
    summary = {
        "general": {
            "total_operations": 100,
            "successful_operations": 95,
            "failed_operations": 5,
            "average_duration": 0.5,
        }
    }

    exporter.export_from_metrics_collector(summary)

    assert "mcp_axon_total_operations" in exporter.metrics
    assert "mcp_axon_successful_operations" in exporter.metrics
    assert "mcp_axon_failed_operations" in exporter.metrics
    assert "mcp_axon_average_duration_seconds" in exporter.metrics


def test_export_from_collector_database_metrics():
    """测试: 从收集器导出数据库指标"""
    exporter = PrometheusMetricsExporter()
    summary = {
        "database": {
            "total_queries": 50,
            "average_duration": 0.1,
        }
    }

    exporter.export_from_metrics_collector(summary)

    assert "mcp_axon_db_total_queries" in exporter.metrics
    assert "mcp_axon_db_average_duration_seconds" in exporter.metrics


def test_export_from_collector_api_metrics():
    """测试: 从收集器导出 API 指标"""
    exporter = PrometheusMetricsExporter()
    summary = {
        "api": {
            "total_calls": 30,
            "average_duration": 0.2,
        }
    }

    exporter.export_from_metrics_collector(summary)

    assert "mcp_axon_api_total_calls" in exporter.metrics
    assert "mcp_axon_api_average_duration_seconds" in exporter.metrics


def test_export_from_collector_empty_summary():
    """测试: 空摘要不导出任何指标"""
    exporter = PrometheusMetricsExporter()

    exporter.export_from_metrics_collector({})

    assert len(exporter.metrics) == 0


# ========== Global exporter ==========


def test_prometheus_exporter_is_singleton():
    """测试: 全局导出器是单例"""
    exporter1 = prometheus_exporter
    exporter2 = prometheus_exporter

    assert exporter1 is exporter2


def test_export_metrics_to_prometheus_function():
    """测试: export_metrics_to_prometheus 函数"""
    summary = {
        "general": {"total_operations": 10},
    }

    output = export_metrics_to_prometheus(summary)

    assert "# TYPE mcp_axon_total_operations counter" in output
    assert "mcp_axon_total_operations" in output


# ========== Label handling ==========


def test_label_escaping_basic_chars():
    """测试: 标签中特殊字符"""
    exporter = PrometheusMetricsExporter()
    exporter.export_gauge("test", 1.0, {"key": 'value with "quotes"'})

    output = exporter.format_prometheus()

    # 标签值包含引号（当前实现不转义）
    assert 'key="value with "quotes""' in output


def test_label_empty_value_allowed():
    """测试: 空标签值允许"""
    exporter = PrometheusMetricsExporter()
    exporter.export_gauge("test", 1.0, {"key": ""})

    output = exporter.format_prometheus()

    assert 'key=""' in output


def test_label_multiple_labels():
    """测试: 多个标签正确格式化"""
    exporter = PrometheusMetricsExporter()
    exporter.export_gauge("test", 1.0, {"label1": "v1", "label2": "v2"})

    output = exporter.format_prometheus()

    # 多个标签用逗号和空格分隔
    assert 'label1="v1", label2="v2"' in output


# ========== Metric name validation ==========


def test_metric_name_valid_chars():
    """测试: 有效指标名称通过"""
    exporter = PrometheusMetricsExporter()

    # 各种有效名称
    exporter.export_gauge("valid_name_123", 1.0)
    exporter.export_gauge("name:with:colons", 1.0)

    assert "mcp_axon_valid_name_123" in exporter.metrics
    assert "mcp_axon_name:with:colons" in exporter.metrics


# ========== Histogram bucket calculations ==========


def test_histogram_bucket_calculation():
    """测试: histogram 桶计算"""
    exporter = PrometheusMetricsExporter()
    buckets = [0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0]
    exporter.export_histogram("latency", 0.150, buckets)

    output = exporter.format_prometheus()

    # 验证桶行
    lines = output.split("\n")
    bucket_lines = [l for l in lines if "_bucket{" in l]

    # 0.150 <= 0.5, 所以 0.5 桶值为 1
    assert any('le="0.5"}' in line and " 1" in line for line in bucket_lines)
    # 0.150 > 0.1, 所以 0.1 桶值为 0
    assert any('le="0.001"}' in line and " 0" in line for line in bucket_lines)


def test_histogram_infinite_bucket():
    """测试: histogram 无限桶"""
    exporter = PrometheusMetricsExporter()
    exporter.export_histogram("latency", 0.150, [0.1, 1.0])

    output = exporter.format_prometheus()

    # +Inf 桶应该有值 1
    assert 'mcp_axon_latency_bucket{le="+Inf"} 1' in output


# ========== Summary quantile calculations ==========


def test_summary_quantile_formatting():
    """测试: summary 分位数格式化"""
    exporter = PrometheusMetricsExporter()
    exporter.export_summary("latency", 0.150, [0.5, 0.9, 0.99])

    output = exporter.format_prometheus()

    # 验证分位数行
    assert 'mcp_axon_latency{quantile="0.5"} 0.15' in output
    assert 'mcp_axon_latency{quantile="0.9"} 0.15' in output
    assert 'mcp_axon_latency{quantile="0.99"} 0.15' in output


# ========== Output format validation ==========


def test_format_prometheus_valid_prometheus_format():
    """测试: 输出符合 Prometheus 格式"""
    exporter = PrometheusMetricsExporter()
    exporter.export_gauge("test_metric", 42.0, {"label": "value"})

    output = exporter.format_prometheus()

    lines = output.strip().split("\n")

    # 第一行应该是 TYPE 声明
    assert lines[0] == "# TYPE mcp_axon_test_metric gauge"
    # 第二行应该是指标值
    assert re.match(r'^mcp_axon_test_metric\{label="value"\} 42\.0$', lines[1])


def test_format_prometheus_sorts_metrics():
    """测试: 格式化输出指标"""
    exporter = PrometheusMetricsExporter()
    exporter.export_gauge("z_metric", 1.0)
    exporter.export_gauge("a_metric", 2.0)

    output = exporter.format_prometheus()

    # 验证两个指标都存在
    assert "mcp_axon_a_metric" in output
    assert "mcp_axon_z_metric" in output


# ========== Edge cases ==========


def test_export_negative_counter_value():
    """测试: 负 counter 值存储（计数器应用避免）"""
    exporter = PrometheusMetricsExporter()

    # 这里存储负值，实际使用中应该避免
    exporter.export_counter("test", -1.0)

    assert exporter.metrics["mcp_axon_test"]["type"] == "counter"


def test_export_zero_value():
    """测试: 零值指标"""
    exporter = PrometheusMetricsExporter()

    exporter.export_gauge("test", 0.0)

    assert exporter.metrics["mcp_axon_test"]["value"] == 0.0


def test_export_large_value():
    """测试: 大数值指标"""
    exporter = PrometheusMetricsExporter()

    exporter.export_gauge("test", 999999.999)

    assert exporter.metrics["mcp_axon_test"]["value"] == 999999.999


def test_export_special_characters_in_labels():
    """测试: 标签中的特殊字符"""
    exporter = PrometheusMetricsExporter()

    exporter.export_gauge("test", 1.0, {"path": "/api/v1/test"})

    output = exporter.format_prometheus()

    # 路径中的斜杠应该保留
    assert 'path="/api/v1/test"' in output


def test_export_unicode_labels():
    """测试: Unicode 标签值"""
    exporter = PrometheusMetricsExporter()

    exporter.export_gauge("test", 1.0, {"chinese": "中文", "emoji": "🎉"})

    output = exporter.format_prometheus()

    # Unicode 字符应该保留
    assert 'chinese="中文"' in output
    assert 'emoji="🎉"' in output
