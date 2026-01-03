# Copyright (c) 2026 Kirky.X. All rights reserved.
# Licensed under the MIT License.
# See LICENSE file in the project root for full license information.

"""HTTP API 服务器 - 提供性能检测接口"""

import asyncio
import json
import logging
import os
import re
import sys
import threading
import time
import uuid
from datetime import datetime
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any, Dict, Optional

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

from src.api.tools import TOOL_DEFINITIONS
from src.constants import APIVersion
from src.core.sdk import RequirementSDK
from src.utils.error_handler import get_safe_error_message
from src.utils.rate_limiter import get_rate_limiter

# 配置日志
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# 创建 MCP 服务器
server = Server("requirement-chain")

# 检测是否在 pytest 测试环境中
IS_TESTING = (
    os.getenv("PYTEST_CURRENT_TEST") is not None
    or "pytest" in sys.modules
    or any("pytest" in arg for arg in sys.argv)
)
db_path = ":memory:" if IS_TESTING else "requirements.db"

# 延迟初始化 SDK（避免在模块加载时创建全局实例）
_sdk = None


def get_sdk() -> RequirementSDK:
    """获取或创建 SDK 实例（延迟初始化）"""
    global _sdk
    if _sdk is None:
        # 每次调用时重新检查环境变量
        is_testing = (
            os.getenv("PYTEST_CURRENT_TEST") is not None
            or "pytest" in sys.modules
            or any("pytest" in arg for arg in sys.argv)
        )
        db_path = ":memory:" if is_testing else "requirements.db"
        _sdk = RequirementSDK(db_path=db_path)
    return _sdk


# 获取限流器
rate_limiter = get_rate_limiter()


class PerformanceMetrics:
    """性能指标收集器"""

    def __init__(self):
        self._requests: list[Dict[str, Any]] = []
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
                    "timestamp": datetime.utcnow().isoformat(),
                    "endpoint": endpoint,
                    "method": method,
                    "status_code": status_code,
                    "duration_ms": duration_ms,
                    "session_id": session_id,
                }
            )

    def get_summary(self) -> Dict[str, Any]:
        """获取指标摘要"""
        with self._lock:
            total_requests = len(self._requests)
            uptime_seconds = time.time() - self._start_time

            if total_requests > 0:
                durations = [r["duration_ms"] for r in self._requests]
                avg_duration = sum(durations) / total_requests
                max_duration = max(durations)
                min_duration = min(durations)

                # 按状态码分组统计
                status_counts: Dict[str, int] = {}
                for r in self._requests:
                    status_counts[str(r["status_code"])] = (
                        status_counts.get(str(r["status_code"]), 0) + 1
                    )

                # 按端点分组统计
                endpoint_counts: Dict[str, int] = {}
                for r in self._requests:
                    endpoint_counts[r["endpoint"]] = (
                        endpoint_counts.get(r["endpoint"], 0) + 1
                    )

                return {
                    "total_requests": total_requests,
                    "uptime_seconds": round(uptime_seconds, 2),
                    "requests_per_second": round(total_requests / uptime_seconds, 2)
                    if uptime_seconds > 0
                    else 0,
                    "average_duration_ms": round(avg_duration, 2),
                    "max_duration_ms": round(max_duration, 2),
                    "min_duration_ms": round(min_duration, 2),
                    "status_counts": status_counts,
                    "endpoint_counts": endpoint_counts,
                }
            else:
                return {
                    "total_requests": 0,
                    "uptime_seconds": round(uptime_seconds, 2),
                    "requests_per_second": 0,
                    "average_duration_ms": 0,
                    "max_duration_ms": 0,
                    "min_duration_ms": 0,
                    "status_counts": {},
                    "endpoint_counts": {},
                }


# 全局性能指标实例
metrics = PerformanceMetrics()


class SessionContext:
    """
    会话上下文管理器

    避免使用全局变量，提供线程安全的会话管理
    """

    def __init__(self):
        """初始化会话上下文"""
        self._session_id = str(uuid.uuid4())
        logger.info(f"创建新会话: {self._session_id}")

    @property
    def session_id(self) -> str:
        """
        获取会话 ID

        Returns:
            会话 ID
        """
        return self._session_id


# 创建会话上下文实例
session_context = SessionContext()


# ============ HTTP 请求处理器 ============


class HTTPRequestHandler(BaseHTTPRequestHandler):
    """HTTP 请求处理器"""

    def log_message(self, format: str, *args) -> None:
        """自定义日志格式"""
        logger.info(f"[HTTP] {args[0]}")

    def send_json_response(self, status_code: int, data: Dict[str, Any]) -> None:
        """发送 JSON 响应"""
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False, indent=2).encode())

    def do_GET(self) -> None:
        """处理 GET 请求"""
        start_time = time.time()

        # 解析路径
        path = self.path.split("?")[0]  # 移除查询字符串

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
            # 尝试获取 SDK 以验证数据库连接
            sdk = get_sdk()

            data = {
                "status": "healthy",
                "timestamp": datetime.utcnow().isoformat(),
                "uptime_seconds": round(time.time() - start_time, 2),
                "response_time_ms": round(duration_ms, 2),
                "database": "connected",
                "sdk_initialized": sdk is not None,
            }
            self.send_json_response(200, data)
        except Exception as e:
            logger.error(f"健康检查失败: {e}")
            data = {
                "status": "unhealthy",
                "timestamp": datetime.utcnow().isoformat(),
                "error": str(e),
                "response_time_ms": round(duration_ms, 2),
            }
            self.send_json_response(503, data)

        metrics.record_request(
            "/health", "GET", 200 if "healthy" else 503, duration_ms, "http"
        )

    def _handle_metrics(self, start_time: float) -> None:
        """性能指标"""
        duration_ms = (time.time() - start_time) * 1000
        summary = metrics.get_summary()

        data = {
            "timestamp": datetime.utcnow().isoformat(),
            "metrics": summary,
            "sdk_status": {
                "initialized": _sdk is not None,
                "db_path": db_path,
            },
            "response_time_ms": round(duration_ms, 2),
        }
        self.send_json_response(200, data)

        metrics.record_request("/metrics", "GET", 200, duration_ms, "http")

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

        metrics.record_request("/api_version", "GET", 200, duration_ms, "http")

    def _handle_root(self, start_time: float) -> None:
        """根路径"""
        duration_ms = (time.time() - start_time) * 1000

        data = {
            "name": "MCP-Axon HTTP API",
            "version": APIVersion.CURRENT_VERSION,
            "description": "基于 MCP 协议的需求链化管理系统 - HTTP API",
            "endpoints": {
                "health": "/health",
                "metrics": "/metrics",
                "api_version": "/api_version",
            },
            "mcp_server": "运行 MCP 服务器模式请使用: python -m src.api.mcp_server",
            "response_time_ms": round(duration_ms, 2),
        }
        self.send_json_response(200, data)

        metrics.record_request("/", "GET", 200, duration_ms, "http")

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

        metrics.record_request(self.path, "GET", 404, duration_ms, "http")

    def do_OPTIONS(self) -> None:
        """处理 CORS 预检请求"""
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()


# ============ HTTP 服务器 ============


class HTTPServerThread(threading.Thread):
    """HTTP 服务器线程"""

    def __init__(self, host: str = "0.0.0.0", port: int = 8080):  # noqa: B104
        super().__init__(daemon=True)
        self.host = host
        self.port = port
        self.server: Optional[HTTPServer] = None
        self.running = False

    def run(self) -> None:
        """运行服务器"""
        try:
            self.server = HTTPServer((self.host, self.port), HTTPRequestHandler)
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
http_server: Optional[HTTPServerThread] = None


def start_http_server(host: str = "0.0.0.0", port: int = 8080) -> HTTPServerThread:  # noqa: B104
    """启动 HTTP 服务器"""
    global http_server
    http_server = HTTPServerThread(host=host, port=port)
    http_server.start()
    return http_server


def stop_http_server() -> None:
    """停止 HTTP 服务器"""
    global http_server
    if http_server:
        http_server.stop()
        http_server = None


# ============ MCP 服务器部分 ============


@server.list_tools()
async def list_tools() -> list[Tool]:
    """
    列出所有可用的工具

    Returns:
        工具列表
    """
    logger.info("工具列表请求")
    return TOOL_DEFINITIONS


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    """
    调用工具

    Args:
        name: 工具名称
        arguments: 工具参数

    Returns:
        工具执行结果
    """
    # 限流检查
    if not rate_limiter.is_allowed(session_context.session_id):
        remaining = rate_limiter.get_remaining_requests(session_context.session_id)
        logger.warning(f"请求限流: 会话 {session_context.session_id} 请求过于频繁")
        error_response = {
            "success": False,
            "error": (
                f"请求过于频繁，请稍后再试。"
                f"当前限制: {rate_limiter.max_requests} 次/{rate_limiter.window_seconds}秒，"
                f"剩余次数: {remaining}"
            ),
            "error_type": "RateLimitExceeded",
            "timestamp": None,
        }
        return [
            TextContent(
                type="text",
                text=json.dumps(error_response, ensure_ascii=False, indent=2),
            )
        ]

    logger.info(f"工具调用: {name} 参数: {arguments}")

    try:
        result = await execute_tool(name, arguments)

        # 格式化响应
        response = {
            "success": True,
            "data": result,
            "timestamp": result.get("timestamp") if isinstance(result, dict) else None,
        }

        # 添加 next_action（如果有）
        if isinstance(result, dict) and "next_action" in result:
            response["next_action"] = result["next_action"]

        return [
            TextContent(
                type="text", text=json.dumps(response, ensure_ascii=False, indent=2)
            )
        ]

    except ValueError as e:
        logger.error(f"工具执行错误（验证错误）: {e}")

        # 使用统一的错误消息
        error_message = get_safe_error_message(str(e))

        error_response = {
            "success": False,
            "error": error_message,
            "error_type": "ValidationError",
            "timestamp": None,
        }
        return [
            TextContent(
                type="text",
                text=json.dumps(error_response, ensure_ascii=False, indent=2),
            )
        ]

    except Exception as e:
        logger.error(f"工具执行错误: {e}", exc_info=True)

        # 使用统一的错误消息
        error_message = get_safe_error_message("内部服务器错误")

        error_response = {
            "success": False,
            "error": error_message,
            "error_type": type(e).__name__,
            "timestamp": None,
        }
        return [
            TextContent(
                type="text",
                text=json.dumps(error_response, ensure_ascii=False, indent=2),
            )
        ]


async def execute_tool(name: str, arguments: dict) -> dict:
    """
    执行工具

    Args:
        name: 工具名称
        arguments: 工具参数

    Returns:
        执行结果

    Raises:
        ValueError: 参数错误
    """
    # 输入验证
    validate_tool_input(name, arguments)

    if name == "create_project":
        project_name = arguments.get("name")
        if project_name is None:
            raise ValueError("缺少必需参数: name")
        return get_sdk().create_project(
            name=project_name, description=arguments.get("description", "")
        )

    elif name == "update_project":
        return get_sdk().update_project(
            project_id=arguments["project_id"],
            name=arguments.get("name"),
            description=arguments.get("description"),
        )

    elif name == "get_project":
        return get_sdk().get_project(project_id=arguments["project_id"])

    elif name == "add_requirement":
        return get_sdk().add_requirement(
            project_id=arguments["project_id"],
            content=arguments["content"],
            parent_id=arguments.get("parent_id"),
            order_in_parent=arguments.get("order_in_parent", 0),
        )

    elif name == "update_requirement":
        return get_sdk().update_requirement(
            requirement_id=arguments["requirement_id"],
            content=arguments.get("content"),
            status=arguments.get("status"),
        )

    elif name == "mark_as_leaf":
        return get_sdk().mark_as_leaf(requirement_id=arguments["requirement_id"])

    elif name == "delete_requirement":
        return get_sdk().delete_requirement(requirement_id=arguments["requirement_id"])

    elif name == "add_validation":
        return get_sdk().add_validation(
            requirement_id=arguments["requirement_id"],
            test_cases=arguments.get("test_cases", []),
            acceptance_criteria=arguments.get("acceptance_criteria", ""),
        )

    elif name == "transfer_dependencies":
        return get_sdk().transfer_dependencies(
            parent_id=arguments["parent_id"],
            dependency_mapping=arguments["dependency_mapping"],
        )

    elif name == "add_dependency":
        return get_sdk().add_dependency(
            requirement_id=arguments["requirement_id"],
            dependency_id=arguments["dependency_id"],
        )

    elif name == "resolve_parallel_order":
        return get_sdk().resolve_parallel_order(
            project_id=arguments["project_id"],
            parallel_nodes=arguments["parallel_nodes"],
            sorted_order=arguments["sorted_order"],
        )

    elif name == "get_next_requirement":
        return get_sdk().get_next_requirement(
            project_id=arguments["project_id"],
            session_id=session_context.session_id,
        )

    elif name == "mark_requirement_completed":
        return get_sdk().mark_requirement_completed(
            project_id=arguments["project_id"],
            requirement_id=arguments["requirement_id"],
        )

    elif name == "get_project_state":
        return get_sdk().get_project_state(project_id=arguments["project_id"])

    elif name == "trigger_chaining":
        return get_sdk().trigger_chaining(
            project_id=arguments["project_id"],
            session_id=session_context.session_id,
        )

    elif name == "create_snapshot":
        snapshot_id = get_sdk().create_snapshot(
            project_id=arguments["project_id"], session_id=session_context.session_id
        )
        return {"snapshot_id": snapshot_id, "message": "快照创建成功"}

    elif name == "restore_snapshot":
        return get_sdk().restore_snapshot(
            snapshot_id=arguments["snapshot_id"], session_id=session_context.session_id
        )

    elif name == "list_snapshots":
        return {
            "snapshots": get_sdk().list_snapshots(
                project_id=arguments["project_id"], limit=arguments.get("limit", 10)
            )
        }

    elif name == "acquire_lock":
        success = get_sdk().acquire_lock(
            project_id=arguments["project_id"], session_id=arguments["session_id"]
        )
        return {
            "success": success,
            "message": "锁获取成功" if success else "锁已被占用",
        }

    elif name == "release_lock":
        success = get_sdk().release_lock(
            project_id=arguments["project_id"], session_id=arguments["session_id"]
        )
        return {
            "success": success,
            "message": "锁释放成功" if success else "锁不属于该会话",
        }

    elif name == "is_locked":
        locked = get_sdk().is_locked(project_id=arguments["project_id"])
        return {"locked": locked, "message": "项目已锁定" if locked else "项目未锁定"}

    elif name == "get_lock_info":
        lock_info = get_sdk().get_lock_info(project_id=arguments["project_id"])
        return {
            "lock_info": lock_info,
            "message": "项目已锁定" if lock_info else "项目未锁定",
        }

    elif name == "get_api_version":
        return {
            "current_version": APIVersion.CURRENT_VERSION,
            "supported_versions": APIVersion.SUPPORTED_VERSIONS,
            "min_supported_version": APIVersion.MIN_SUPPORTED_VERSION,
            "version_history": APIVersion.VERSION_HISTORY,
        }

    else:
        raise ValueError(f"未知工具: {name}")


def validate_tool_input(name: str, arguments: dict) -> None:
    """
    验证工具输入参数

    Args:
        name: 工具名称
        arguments: 工具参数

    Raises:
        ValueError: 参数验证失败
    """
    # 基本参数检查
    if not isinstance(arguments, dict):
        raise ValueError("参数必须是字典格式")

    # UUID 格式验证
    uuid_pattern = re.compile(
        r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", re.IGNORECASE
    )

    # 项目 ID 验证
    if name in [
        "update_project",
        "get_project",
        "add_requirement",
        "get_project_state",
        "trigger_chaining",
        "create_snapshot",
        "list_snapshots",
        "acquire_lock",
        "release_lock",
        "is_locked",
        "get_lock_info",
        "resolve_parallel_order",
        "get_next_requirement",
        "mark_requirement_completed",
    ]:
        project_id = arguments.get("project_id")
        if not project_id or not isinstance(project_id, str):
            raise ValueError("project_id 参数是必填的字符串")
        if not uuid_pattern.match(project_id):
            raise ValueError("project_id 格式不正确，必须是有效的 UUID")

    # 需求 ID 验证
    if name in [
        "update_requirement",
        "mark_as_leaf",
        "delete_requirement",
        "add_validation",
        "add_dependency",
    ]:
        requirement_id = arguments.get("requirement_id")
        if not requirement_id or not isinstance(requirement_id, str):
            raise ValueError("requirement_id 参数是必填的字符串")
        if not uuid_pattern.match(requirement_id):
            raise ValueError("requirement_id 格式不正确，必须是有效的 UUID")

    # transfer_dependencies 使用 parent_id
    if name == "transfer_dependencies":
        parent_id = arguments.get("parent_id")
        if not parent_id or not isinstance(parent_id, str):
            raise ValueError("parent_id 参数是必填的字符串")
        if not uuid_pattern.match(parent_id):
            raise ValueError("parent_id 格式不正确，必须是有效的 UUID")

        # 验证 dependency_mapping
        dependency_mapping = arguments.get("dependency_mapping")
        if not isinstance(dependency_mapping, dict):
            raise ValueError("dependency_mapping 必须是字典格式")

    # 字符串内容验证
    if name in ["create_project", "add_requirement"]:
        content_key = "name" if name == "create_project" else "content"
        content = arguments.get(content_key, "")
        if not isinstance(content, str) or not content.strip():
            raise ValueError(f"{content_key} 不能为空")
        if len(content) > 5000:
            raise ValueError(f"{content_key} 长度不能超过 5000 字符")

    # 数组参数验证
    if name == "add_validation":
        test_cases = arguments.get("test_cases", [])
        if not isinstance(test_cases, list):
            raise ValueError("test_cases 必须是数组格式")
        # 验证测试用例格式
        for i, test_case in enumerate(test_cases):
            if not isinstance(test_case, dict):
                raise ValueError(f"test_cases[{i}] 必须是字典格式")

    # 并行节点排序验证
    if name == "resolve_parallel_order":
        parallel_nodes = arguments.get("parallel_nodes", [])
        sorted_order = arguments.get("sorted_order", [])
        if not isinstance(parallel_nodes, list) or not isinstance(sorted_order, list):
            raise ValueError("parallel_nodes 和 sorted_order 必须是数组格式")
        if len(parallel_nodes) != len(sorted_order):
            raise ValueError("parallel_nodes 和 sorted_order 长度必须相同")
        if set(parallel_nodes) != set(sorted_order):
            raise ValueError("sorted_order 必须包含所有 parallel_nodes 中的节点")

        # 验证节点ID格式
        all_nodes = parallel_nodes + sorted_order
        for node in all_nodes:
            if not isinstance(node, str) or not uuid_pattern.match(node):
                raise ValueError(f"节点ID格式不正确: {node}")


async def main():
    """主函数 - 同时启动 MCP 和 HTTP 服务器"""
    import argparse

    parser = argparse.ArgumentParser(description="MCP-Axon 服务器")
    parser.add_argument(
        "--mode",
        choices=["mcp", "http", "both"],
        default="mcp",
        help="运行模式: mcp (默认), http, both",
    )
    parser.add_argument(  # noqa: B104
        "--http-host",
        default="0.0.0.0",
        help="HTTP 服务器绑定地址 (默认: 0.0.0.0)",
    )
    parser.add_argument(
        "--http-port",
        type=int,
        default=8080,
        help="HTTP 服务器端口 (默认: 8080)",
    )
    args = parser.parse_args()

    # 启动 HTTP 服务器（如果需要）
    if args.mode in ["http", "both"]:
        start_http_server(host=args.http_host, port=args.http_port)

    # 启动 MCP 服务器
    if args.mode in ["mcp", "both"]:
        logger.info("启动 MCP 服务器...")

        async with stdio_server() as (read_stream, write_stream):
            await server.run(
                read_stream, write_stream, server.create_initialization_options()
            )
    else:
        # 仅 HTTP 模式，保持运行
        logger.info(f"HTTP 服务器运行在 http://{args.http_host}:{args.http_port}")
        logger.info("按 Ctrl+C 停止服务器")

        # 保持主线程运行
        try:
            while True:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            logger.info("收到停止信号")
            stop_http_server()


if __name__ == "__main__":
    asyncio.run(main())
