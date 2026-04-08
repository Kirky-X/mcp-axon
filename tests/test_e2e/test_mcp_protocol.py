# Copyright (c) 2026 Kirky.X. All rights reserved.
# Licensed under the MIT License.
# See LICENSE file in the project root for full license information.

"""MCP 协议端到端测试"""

from src.api.mcp_server import execute_tool, list_tools


async def test_tc032_mcp_tool_registration():
    """TC-032: 测试 MCP 工具注册"""

    # Arrange & Act
    tools = await list_tools()

    # Assert
    tool_names = [tool.name for tool in tools]
    assert "create_project" in tool_names
    assert "add_requirement" in tool_names
    assert "get_next_requirement" in tool_names
    assert len(tool_names) >= 22


async def test_tc033_mcp_tool_call():
    """TC-033: 测试 MCP 工具调用"""
    # Arrange & Act
    result = await execute_tool(
        "create_project", {"name": "测试项目", "description": "描述"}
    )

    # Assert
    assert result is not None
    assert "project_id" in result
    assert "next_action" in result


async def test_mcp_tool_call_add_requirement():
    """测试 MCP 工具调用 - 添加需求"""
    # Arrange: 先创建项目
    project_result = await execute_tool("create_project", {"name": "测试项目"})
    project_id = project_result["project_id"]

    # Act
    result = await execute_tool(
        "add_requirement", {"project_id": project_id, "content": "测试需求"}
    )

    # Assert
    assert result is not None
    assert "requirement_id" in result
