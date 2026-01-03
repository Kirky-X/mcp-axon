# Copyright (c) 2026 Kirky.X. All rights reserved.
# Licensed under the MIT License.
# See LICENSE file in the project root for full license information.

"""MCP 服务器入口"""

import asyncio
import json
import logging
import re
import uuid

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

# 注册服务器信息

# 检查是否在测试环境中，使用内存数据库
import os
IS_TESTING = os.getenv("PYTEST_CURRENT_TEST") is not None
db_path = ":memory:" if IS_TESTING else "requirements.db"

# 初始化 SDK
sdk = RequirementSDK(db_path=db_path)

# 获取限流器
rate_limiter = get_rate_limiter()


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
        return sdk.create_project(
            name=project_name, description=arguments.get("description", "")
        )

    elif name == "update_project":
        return sdk.update_project(
            project_id=arguments["project_id"],
            name=arguments.get("name"),
            description=arguments.get("description"),
        )

    elif name == "get_project":
        return sdk.get_project(project_id=arguments["project_id"])

    elif name == "add_requirement":
        return sdk.add_requirement(
            project_id=arguments["project_id"],
            content=arguments["content"],
            parent_id=arguments.get("parent_id"),
            order_in_parent=arguments.get("order_in_parent", 0),
        )

    elif name == "update_requirement":
        return sdk.update_requirement(
            requirement_id=arguments["requirement_id"],
            content=arguments.get("content"),
            status=arguments.get("status"),
        )

    elif name == "mark_as_leaf":
        return sdk.mark_as_leaf(requirement_id=arguments["requirement_id"])

    elif name == "delete_requirement":
        return sdk.delete_requirement(requirement_id=arguments["requirement_id"])

    elif name == "add_validation":
        return sdk.add_validation(
            requirement_id=arguments["requirement_id"],
            test_cases=arguments.get("test_cases", []),
            acceptance_criteria=arguments.get("acceptance_criteria", ""),
        )

    elif name == "transfer_dependencies":
        return sdk.transfer_dependencies(
            parent_id=arguments["parent_id"],
            dependency_mapping=arguments["dependency_mapping"],
        )

    elif name == "add_dependency":
        return sdk.add_dependency(
            requirement_id=arguments["requirement_id"],
            dependency_id=arguments["dependency_id"],
        )

    elif name == "resolve_parallel_order":
        return sdk.resolve_parallel_order(
            project_id=arguments["project_id"],
            parallel_nodes=arguments["parallel_nodes"],
            sorted_order=arguments["sorted_order"],
        )

    elif name == "get_next_requirement":
        return sdk.get_next_requirement(
            project_id=arguments["project_id"],
            session_id=session_context.session_id,
        )

    elif name == "mark_requirement_completed":
        return sdk.mark_requirement_completed(
            project_id=arguments["project_id"],
            requirement_id=arguments["requirement_id"],
        )

    elif name == "get_project_state":
        return sdk.get_project_state(project_id=arguments["project_id"])

    elif name == "trigger_chaining":
        return sdk.trigger_chaining(
            project_id=arguments["project_id"],
            session_id=session_context.session_id,
        )

    elif name == "create_snapshot":
        snapshot_id = sdk.create_snapshot(
            project_id=arguments["project_id"], session_id=session_context.session_id
        )
        return {"snapshot_id": snapshot_id, "message": "快照创建成功"}

    elif name == "restore_snapshot":
        return sdk.restore_snapshot(
            snapshot_id=arguments["snapshot_id"], session_id=session_context.session_id
        )

    elif name == "list_snapshots":
        return {
            "snapshots": sdk.list_snapshots(
                project_id=arguments["project_id"], limit=arguments.get("limit", 10)
            )
        }

    elif name == "acquire_lock":
        success = sdk.acquire_lock(
            project_id=arguments["project_id"], session_id=arguments["session_id"]
        )
        return {
            "success": success,
            "message": "锁获取成功" if success else "锁已被占用",
        }

    elif name == "release_lock":
        success = sdk.release_lock(
            project_id=arguments["project_id"], session_id=arguments["session_id"]
        )
        return {
            "success": success,
            "message": "锁释放成功" if success else "锁不属于该会话",
        }

    elif name == "is_locked":
        locked = sdk.is_locked(project_id=arguments["project_id"])
        return {"locked": locked, "message": "项目已锁定" if locked else "项目未锁定"}

    elif name == "get_lock_info":
        lock_info = sdk.get_lock_info(project_id=arguments["project_id"])
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
    """主函数"""
    logger.info("启动 MCP 服务器...")

    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream, write_stream, server.create_initialization_options()
        )


if __name__ == "__main__":
    asyncio.run(main())
