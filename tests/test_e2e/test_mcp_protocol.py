# Copyright (c) 2026 Kirky.X. All rights reserved.
# Licensed under the MIT License.
# See LICENSE file in the project root for full license information.

"""MCP 协议端到端测试"""

import os
import pytest

os.environ["MCP_AXON_DB_PATH"] = ":memory:"

from src.api.mcp_server import get_tool_router, list_tools
from src.core.containers import init_container


@pytest.fixture(autouse=True)
def reset_state():
    """Reset global SDK and router state between tests"""
    import src.api.mcp_server as mcp_server

    mcp_server._sdk = None
    mcp_server._tool_router = None
    init_container(db_path=":memory:")
    yield
    mcp_server._sdk = None
    mcp_server._tool_router = None


async def test_tc032_mcp_tool_registration():
    """TC-032: 测试 MCP 工具注册"""
    tools = await list_tools()
    tool_names = [tool.name for tool in tools]
    assert "manage_project" in tool_names
    assert "manage_requirement" in tool_names
    assert "get_next_requirement" in tool_names
    assert len(tool_names) >= 19


async def test_tc033_mcp_tool_call():
    """TC-033: 测试 MCP 工具调用"""
    router = get_tool_router()
    result = router.route("manage_project", {"name": "测试项目", "description": "描述"})
    assert result is not None
    assert "project_id" in result
    assert "next_action" in result


async def test_mcp_tool_call_add_requirement():
    """测试 MCP 工具调用 - 添加需求"""
    router = get_tool_router()
    project_result = router.route("manage_project", {"name": "测试项目"})
    project_id = project_result["project_id"]

    result = router.route(
        "manage_requirement", {"project_id": project_id, "content": "测试需求"}
    )

    assert result is not None
    assert "requirement_id" in result
