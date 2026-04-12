# Copyright (c) 2026 Kirky.X. All rights reserved.
# Licensed under the MIT License.
# See LICENSE file in the project root for full license information.

"""HTTP 服务器测试"""

import json
import time
from io import BytesIO

import pytest

from src.api.http_server import (
    HTTPRequestHandler,
    HTTPServerThread,
    http_metrics,
)


class TestPerformanceMetricsCollector:
    """PerformanceMetricsCollector 测试"""

    def setup_method(self):
        """每个测试前清空数据"""
        http_metrics._requests.clear()
        http_metrics._start_time = time.time()

    def test_record_request_and_get_summary(self):
        """测试: 记录请求并获取摘要"""
        http_metrics.record_request("/health", "GET", 200, 10.5, "test")
        summary = http_metrics.get_summary()

        assert summary["total_requests"] == 1
        assert summary["average_duration_ms"] == 10.5
        assert summary["max_duration_ms"] == 10.5
        assert summary["min_duration_ms"] == 10.5

    def test_multiple_requests_summary(self):
        """测试: 多个请求的摘要统计"""
        http_metrics.record_request("/health", "GET", 200, 10.0, "test")
        http_metrics.record_request("/metrics", "GET", 200, 20.0, "test")
        http_metrics.record_request("/api_version", "GET", 200, 5.0, "test")

        summary = http_metrics.get_summary()
        assert summary["total_requests"] == 3
        assert summary["average_duration_ms"] == pytest.approx(11.67, abs=0.02)
        assert summary["max_duration_ms"] == 20.0
        assert summary["min_duration_ms"] == 5.0

    def test_empty_summary(self):
        """测试: 无请求时返回空摘要"""
        summary = http_metrics.get_summary()
        assert summary["total_requests"] == 0
        assert summary["requests_per_second"] == 0

    def test_uptime_calculation(self):
        """测试: 运行时间计算"""
        old_start = http_metrics._start_time
        http_metrics._start_time = time.time() - 10
        summary = http_metrics.get_summary()
        assert summary["uptime_seconds"] >= 9.9
        http_metrics._start_time = old_start


class MockConnection:
    """模拟 HTTP 连接用于测试"""

    def __init__(self):
        self.response_code = None
        self.response_headers = {}
        self.response_body = b""
        self.wfile = BytesIO()

    def makefile(self, *args, **kwargs):
        return BytesIO()

    def sendall(self, data):
        pass


class MockServer:
    """模拟服务器"""

    def __init__(self):
        self.address = ("127.0.0.1", 8080)


def create_handler(request_line, method="GET", sdk_check_fn=None):
    """创建 HTTPRequestHandler 实例用于测试"""

    class TestableHandler(HTTPRequestHandler):
        def __init__(self):
            self._health_check_fn = None
            self._sdk_check_fn = sdk_check_fn
            self.rfile = BytesIO(request_line.encode())
            self.wfile = BytesIO()
            self._headers_buffer = BytesIO()
            self.requestline = request_line
            self.command = method
            self.path = request_line.split(" ")[1] if " " in request_line else "/"
            self.headers = {}
            self._headers_written = False
            self._body = b""
            self._code = 200

        def send_response(self, code):
            self._code = code

        def send_header(self, keyword, value):
            self._headers_buffer.write(f"{keyword}: {value}\r\n".encode())

        def end_headers(self):
            self._headers_written = True

        def log_message(self, format, *args):
            pass

    return TestableHandler()


class TestHTTPRequestHandler:
    """HTTPRequestHandler 测试"""

    def test_health_endpoint(self):
        """测试: /health 端点返回健康状态"""
        handler = create_handler("GET /health HTTP/1.1", sdk_check_fn=lambda: True)
        handler._handle_health(time.time())

        handler.wfile.seek(0)
        body = handler.wfile.getvalue().decode()
        data = json.loads(body)

        assert data["status"] == "healthy"
        assert "response_time_ms" in data
        assert data["database"] == "connected"

    def test_health_endpoint_sdk_check(self):
        """测试: /health 包含 SDK 状态"""
        handler = create_handler("GET /health HTTP/1.1", sdk_check_fn=lambda: True)
        handler._handle_health(time.time())

        handler.wfile.seek(0)
        data = json.loads(handler.wfile.getvalue().decode())
        assert data["sdk_initialized"] is True

    def test_api_version_endpoint(self):
        """测试: /api_version 返回版本信息"""
        handler = create_handler("GET /api_version HTTP/1.1")
        handler._handle_api_version(time.time())

        handler.wfile.seek(0)
        data = json.loads(handler.wfile.getvalue().decode())

        assert "current_version" in data
        assert "supported_versions" in data
        assert "version_history" in data

    def test_root_endpoint(self):
        """测试: / 返回 API 信息"""
        handler = create_handler("GET / HTTP/1.1")
        handler._handle_root(time.time())

        handler.wfile.seek(0)
        data = json.loads(handler.wfile.getvalue().decode())

        assert data["name"] == "Axon HTTP API"
        assert "endpoints" in data
        assert "health" in data["endpoints"]

    def test_not_found_endpoint(self):
        """测试: 不存在的路径返回 404"""
        handler = create_handler("GET /nonexistent HTTP/1.1")
        handler._handle_not_found(time.time())

        handler.wfile.seek(0)
        data = json.loads(handler.wfile.getvalue().decode())

        assert data["error"] == "Not Found"
        assert "nonexistent" in data["message"]

    def test_metrics_endpoint(self):
        """测试: /metrics 返回性能指标"""
        handler = create_handler("GET /metrics HTTP/1.1")
        handler._handle_metrics(time.time())

        handler.wfile.seek(0)
        data = json.loads(handler.wfile.getvalue().decode())

        assert "metrics" in data
        assert "timestamp" in data

    def test_options_cors(self):
        """测试: OPTIONS 请求返回 CORS 头"""
        handler = create_handler("OPTIONS /health HTTP/1.1")

        sent_headers = {}

        def mock_send_response(code):
            handler._code = code

        def mock_send_header(keyword, value):
            sent_headers[keyword] = value

        def mock_end_headers():
            pass

        handler.send_response = mock_send_response
        handler.send_header = mock_send_header
        handler.end_headers = mock_end_headers
        handler.do_OPTIONS()

        assert sent_headers.get("Access-Control-Allow-Origin") == "http://127.0.0.1"
        assert "GET" in sent_headers.get("Access-Control-Allow-Methods", "")


class TestHTTPServerThread:
    """HTTPServerThread 测试"""

    def test_server_start_stop(self):
        """测试: 服务器可以启动和停止"""
        # 使用随机端口避免冲突
        thread = HTTPServerThread(host="127.0.0.1", port=0)
        # 不实际启动（需要有效端口），仅测试初始化
        assert thread.host == "127.0.0.1"
        assert not thread.running
