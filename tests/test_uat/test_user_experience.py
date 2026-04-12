# Copyright (c) 2026 Kirky.X. All rights reserved.
# Licensed under the MIT License.
# See LICENSE file in the project root for full license information.

"""用户体验验收测试 (UAT-020 ~ UAT-021)"""

from src.core.sdk import RequirementSDK


def test_uat020_ai_interaction_experience():
    """UAT-020: AI 交互体验验收"""

    sdk = RequirementSDK(db_path=":memory:")

    # 模拟 AI 完成完整流程
    # 1. 创建项目
    project = sdk.manage_project(name="AI测试项目")
    assert "next_action" in project

    # 2. 添加需求
    req = sdk.manage_requirement(
        project_id=project["project_id"], content="实现用户登录"
    )
    assert "next_action" in req

    # 3. 标记叶子
    # 需求默认是叶子节点，next_action 已在 add_requirement 返回

    # 4. 添加验证
    validation = sdk.add_validation(req["requirement_id"], [{"name": "测试"}])
    assert "next_action" in validation

    # 5. 查询状态
    state = sdk.get_project_state(project["project_id"])
    assert "project_id" in state

    # 验证所有操作都有清晰的 next_action
    # 验证所有操作都有清晰的 next_action
    assert all("next_action" in r for r in [project, req, validation])


def test_uat021_response_message_quality():
    """UAT-021: 响应消息质量验收"""
    sdk = RequirementSDK(db_path=":memory:")

    # 测试成功消息
    project = sdk.manage_project(name="测试项目")
    assert project["project_id"] is not None
    assert project["status"] == "CREATED"
    assert "next_action" in project

    # 测试错误消息
    try:
        sdk.manage_requirement(project_id="nonexistent-id", content="需求")
        assert False, "应该抛出异常"
    except ValueError as e:
        assert "项目不存在" in str(e)

    # 测试引导消息
    req = sdk.manage_requirement(project_id=project["project_id"], content="复杂需求")
    if req["needs_decomposition"]:
        assert "decompose_hints" in req
        assert len(req["decompose_hints"]) > 0

    # 测试叶子节点引导
    simple_req = sdk.manage_requirement(
        project_id=project["project_id"], content="简单需求"
    )
    # 需求默认是叶子节点(simple_req["requirement_id"])
    assert "next_action" in simple_req
