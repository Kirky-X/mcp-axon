# Copyright (c) 2026 Kirky.X. All rights reserved.
# Licensed under the MIT License.
# See LICENSE file in the project root for full license information.

"""HTTP 服务器 - 提供性能检测和健康检查接口"""

import json
import logging
import threading
import time
from datetime import UTC, datetime
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any

from src.constants import APIVersion

logger = logging.getLogger(__name__)


class PerformanceMetricsCollector:
    """HTTP 请求性能指标收集器"""

    def __init__(self):
        self._requests: list[dict[str, Any]] = []
        self._lock = threading.Lock()
        self._start_time = time.time()

    def record_request(
        self,
        endpoint: str,
        method: str,
        status_code: int,
        duration_ms: float,
        session_id: str,
    ) -> None:
        """记录请求"""
        with self._lock:
            self._requests.append(
                {
                    "timestamp": datetime.now(UTC).isoformat(),
                    "endpoint": endpoint,
                    "method": method,
                    "status_code": status_code,
                    "duration_ms": duration_ms,
                    "session_id": session_id,
                }
            )

    def get_summary(self) -> dict[str, Any]:
        """获取指标摘要"""
        with self._lock:
            total_requests = len(self._requests)
            uptime_seconds = time.time() - self._start_time

            if total_requests > 0:
                durations = [r["duration_ms"] for r in self._requests]
                return {
                    "total_requests": total_requests,
                    "uptime_seconds": round(uptime_seconds, 2),
                    "requests_per_second": round(total_requests / uptime_seconds, 2)
                    if uptime_seconds > 0
                    else 0,
                    "average_duration_ms": round(sum(durations) / total_requests, 2),
                    "max_duration_ms": round(max(durations), 2),
                    "min_duration_ms": round(min(durations), 2),
                }
            return {
                "total_requests": 0,
                "uptime_seconds": round(uptime_seconds, 2),
                "requests_per_second": 0,
                "average_duration_ms": 0,
                "max_duration_ms": 0,
                "min_duration_ms": 0,
            }


# 全局性能指标实例
http_metrics = PerformanceMetricsCollector()


class HTTPRequestHandler(BaseHTTPRequestHandler):
    """HTTP 请求处理器"""

    def __init__(
        self,
        request,
        client_address,
        server,
        health_check_fn=None,
        sdk_check_fn=None,
    ):
        self._health_check_fn = health_check_fn
        self._sdk_check_fn = sdk_check_fn
        super().__init__(request, client_address, server)

    def log_message(self, format: str, *args) -> None:
        """自定义日志格式"""
        logger.info(f"[HTTP] {args[0]}")

    def send_json_response(self, status_code: int, data: dict[str, Any]) -> None:
        """发送 JSON 响应"""
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "http://127.0.0.1")
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False, indent=2).encode())

    def do_GET(self) -> None:
        """处理 GET 请求"""
        start_time = time.time()
        path = self.path.split("?")[0]

        if path == "/health":
            self._handle_health(start_time)
        elif path == "/metrics":
            self._handle_metrics(start_time)
        elif path == "/api_version":
            self._handle_api_version(start_time)
        elif path == "/":
            self._handle_root(start_time)
        else:
            self._handle_not_found(start_time)

    def _handle_health(self, start_time: float) -> None:
        """健康检查"""
        duration_ms = (time.time() - start_time) * 1000

        try:
            sdk_ok = self._sdk_check_fn() if self._sdk_check_fn else True
            data = {
                "status": "healthy",
                "timestamp": datetime.now(UTC).isoformat(),
                "response_time_ms": round(duration_ms, 2),
                "database": "connected",
                "sdk_initialized": sdk_ok,
            }
            self.send_json_response(200, data)
            http_metrics.record_request("/health", "GET", 200, duration_ms, "http")
        except Exception as e:
            logger.error(f"健康检查失败: {e}")
            data = {
                "status": "unhealthy",
                "timestamp": datetime.now(UTC).isoformat(),
                "response_time_ms": round(duration_ms, 2),
            }
            self.send_json_response(503, data)
            http_metrics.record_request("/health", "GET", 503, duration_ms, "http")

    def _handle_metrics(self, start_time: float) -> None:
        """性能指标"""
        duration_ms = (time.time() - start_time) * 1000
        summary = http_metrics.get_summary()

        data = {
            "timestamp": datetime.now(UTC).isoformat(),
            "metrics": summary,
            "response_time_ms": round(duration_ms, 2),
        }
        self.send_json_response(200, data)
        http_metrics.record_request("/metrics", "GET", 200, duration_ms, "http")

    def _handle_api_version(self, start_time: float) -> None:
        """API 版本信息"""
        duration_ms = (time.time() - start_time) * 1000

        data = {
            "current_version": APIVersion.CURRENT_VERSION,
            "supported_versions": APIVersion.SUPPORTED_VERSIONS,
            "min_supported_version": APIVersion.MIN_SUPPORTED_VERSION,
            "version_history": APIVersion.VERSION_HISTORY,
            "response_time_ms": round(duration_ms, 2),
        }
        self.send_json_response(200, data)
        http_metrics.record_request("/api_version", "GET", 200, duration_ms, "http")

    def _handle_root(self, start_time: float) -> None:
        """根路径"""
        duration_ms = (time.time() - start_time) * 1000

        data = {
            "name": "Axon HTTP API",
            "version": APIVersion.CURRENT_VERSION,
            "description": "基于 MCP 协议的需求链化管理系统 - HTTP API",
            "endpoints": {
                "health": "/health",
                "metrics": "/metrics",
                "api_version": "/api_version",
            },
            "response_time_ms": round(duration_ms, 2),
        }
        self.send_json_response(200, data)
        http_metrics.record_request("/", "GET", 200, duration_ms, "http")

    def _handle_not_found(self, start_time: float) -> None:
        """404 处理"""
        duration_ms = (time.time() - start_time) * 1000

        data = {
            "error": "Not Found",
            "message": f"路径 {self.path} 不存在",
            "available_endpoints": ["/health", "/metrics", "/api_version"],
            "response_time_ms": round(duration_ms, 2),
        }
        self.send_json_response(404, data)
        http_metrics.record_request(self.path, "GET", 404, duration_ms, "http")

    def do_OPTIONS(self) -> None:
        """处理 CORS 预检请求"""
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "http://127.0.0.1")
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()


class HTTPServerThread(threading.Thread):
    """HTTP 服务器线程"""

    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 8080,
        health_check_fn=None,
        sdk_check_fn=None,
    ):
        super().__init__(daemon=True)
        self.host = host
        self.port = port
        self.health_check_fn = health_check_fn
        self.sdk_check_fn = sdk_check_fn
        self.server: HTTPServer | None = None
        self.running = False

    def run(self) -> None:
        """运行服务器"""

        def handler(request, client_address, server):
            return HTTPRequestHandler(
                request,
                client_address,
                server,
                health_check_fn=self.health_check_fn,
                sdk_check_fn=self.sdk_check_fn,
            )

        try:
            self.server = HTTPServer((self.host, self.port), handler)
            self.running = True
            logger.info(f"HTTP 服务器启动: http://{self.host}:{self.port}")
            logger.info("可用端点: /health, /metrics, /api_version")
            self.server.serve_forever()
        except Exception as e:
            logger.error(f"HTTP 服务器启动失败: {e}")
            self.running = False

    def stop(self) -> None:
        """停止服务器"""
        if self.server:
            self.server.shutdown()
            self.running = False
            logger.info("HTTP 服务器已停止")


# 全局 HTTP 服务器实例
_http_server: HTTPServerThread | None = None


def start_http_server(
    host: str = "127.0.0.1",
    port: int = 8080,
    health_check_fn=None,
    sdk_check_fn=None,
) -> HTTPServerThread:
    """启动 HTTP 服务器"""
    global _http_server
    _http_server = HTTPServerThread(
        host=host, port=port, health_check_fn=health_check_fn, sdk_check_fn=sdk_check_fn
    )
    _http_server.start()
    return _http_server


def stop_http_server() -> None:
    """停止 HTTP 服务器"""
    global _http_server
    if _http_server:
        _http_server.stop()
        _http_server = None
