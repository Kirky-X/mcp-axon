# Copyright (c) 2026 Kirky.X. All rights reserved.
# Licensed under the MIT License.
# See LICENSE file in the project root for full license information.

"""MCP 服务器入口"""

import asyncio
import json
import logging
import os
import sys

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

from src.api.http_server import start_http_server, stop_http_server
from src.api.tool_router import ToolRouter
from src.api.tools import TOOL_DEFINITIONS
from src.core.containers import init_container
from src.core.sdk import RequirementSDK
from src.utils.rate_limiter import get_rate_limiter

# 配置日志
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# 检测测试环境
IS_TESTING = (
    os.getenv("PYTEST_CURRENT_TEST") is not None
    or "pytest" in sys.modules
    or any("pytest" in arg for arg in sys.argv)
)
db_path = ":memory:" if IS_TESTING else os.getenv("MCP_AXON_DB_PATH", "requirements.db")

# 延迟初始化 SDK
_sdk: RequirementSDK | None = None


def get_sdk() -> RequirementSDK:
    """获取或创建 SDK 实例（延迟初始化）"""
    global _sdk
    if _sdk is None:
        _sdk = RequirementSDK(db_path=db_path)
    return _sdk


# 工具路由器（延迟初始化）
_tool_router: ToolRouter | None = None


def get_tool_router() -> ToolRouter:
    """获取工具路由器实例"""
    global _tool_router
    if _tool_router is None:
        _tool_router = ToolRouter(get_sdk)
    return _tool_router


# 会话管理
class SessionContext:
    """会话上下文管理器"""

    def __init__(self):
        import uuid

        self._session_id = str(uuid.uuid4())
        logger.info(f"创建新会话: {self._session_id}")

    @property
    def session_id(self) -> str:
        return self._session_id


session_context = SessionContext()


# MCP 服务器
server = Server("requirement-chain")


rate_limiter = None


@server.list_tools()
async def list_tools() -> list[Tool]:
    """列出所有可用的工具"""
    logger.info("工具列表请求")
    return TOOL_DEFINITIONS


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    """调用工具"""
    global rate_limiter
    if rate_limiter is None:
        rate_limiter = get_rate_limiter()

    # 限流检查
    if not rate_limiter.is_allowed(session_context.session_id):
        remaining = rate_limiter.get_remaining_requests(session_context.session_id)
        logger.warning(f"请求限流: 会话 {session_context.session_id} 请求过于频繁")
        return [
            TextContent(
                type="text",
                text=json.dumps(
                    {
                        "success": False,
                        "error": (
                            f"请求过于频繁，请稍后再试。"
                            f"当前限制: {rate_limiter.max_requests} 次/{rate_limiter.window_seconds}秒，"
                            f"剩余次数: {remaining}"
                        ),
                        "error_type": "RateLimitExceeded",
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
            )
        ]

    logger.info(f"工具调用: {name} 参数: {arguments}")

    try:
        router = get_tool_router()
        router.validate_input(name, arguments)
        # 注入 session_id 到参数中
        arguments["_session_id"] = session_context.session_id
        result = router.route(name, arguments)

        response = {
            "success": True,
            "data": result,
            "timestamp": result.get("timestamp") if isinstance(result, dict) else None,
        }
        if isinstance(result, dict) and "next_action" in result:
            response["next_action"] = result["next_action"]

        return [
            TextContent(
                type="text", text=json.dumps(response, ensure_ascii=False, indent=2)
            )
        ]

    except ValueError as e:
        logger.error(f"工具执行错误（验证错误）: {e}")
        from src.utils.error_handler import get_safe_error_message

        error_message = get_safe_error_message(str(e))
        return [
            TextContent(
                type="text",
                text=json.dumps(
                    {
                        "success": False,
                        "error": error_message,
                        "error_type": "ValidationError",
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
            )
        ]

    except Exception as e:
        logger.error(f"工具执行错误: {e}", exc_info=True)
        from src.utils.error_handler import get_safe_error_message

        error_message = get_safe_error_message("内部服务器错误")
        return [
            TextContent(
                type="text",
                text=json.dumps(
                    {
                        "success": False,
                        "error": error_message,
                        "error_type": type(e).__name__,
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
            )
        ]


async def main():
    """主函数 - 同时启动 MCP 和 HTTP 服务器"""
    import argparse

    parser = argparse.ArgumentParser(description="Axon 服务器")
    parser.add_argument(
        "--mode",
        choices=["mcp", "http", "both"],
        default="mcp",
        help="运行模式: mcp (默认), http, both",
    )
    parser.add_argument(
        "--db-path",
        default="requirements.db",
        help="数据库文件路径 (默认: requirements.db)",
    )
    parser.add_argument(
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

    os.environ["MCP_AXON_DB_PATH"] = args.db_path
    init_container(db_path=args.db_path)
    logger.info(f"数据库初始化完成: {args.db_path}")

    # 启动 HTTP 服务器（如果需要）
    if args.mode in ["http", "both"]:
        start_http_server(
            host=args.http_host,
            port=args.http_port,
            health_check_fn=lambda: True,
            sdk_check_fn=lambda: _sdk is not None,
        )

    # 启动 MCP 服务器
    if args.mode in ["mcp", "both"]:
        logger.info("启动 MCP 服务器...")
        async with stdio_server() as (read_stream, write_stream):
            await server.run(
                read_stream, write_stream, server.create_initialization_options()
            )
    else:
        logger.info(f"HTTP 服务器运行在 http://{args.http_host}:{args.http_port}")
        try:
            while True:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            logger.info("收到停止信号")
            stop_http_server()


if __name__ == "__main__":
    asyncio.run(main())
