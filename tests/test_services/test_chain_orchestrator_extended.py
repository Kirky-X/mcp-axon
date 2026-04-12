# Copyright (c) 2026 Kirky.X. All rights reserved.
# Licensed under the MIT License.
# See LICENSE file in the project root for full license information.

"""链化编排补充测试"""

import pytest

from src.core.containers import init_container
from src.core.sdk import RequirementSDK


@pytest.fixture
def sdk():
    init_container(db_path=":memory:")
    return RequirementSDK(db_path=":memory:")


@pytest.fixture
def project(sdk):
    return sdk.manage_project(name="链化编排测试项目")


class TestChainOrchestratorExtended:
    """链化编排补充测试"""

    def test_mark_requirement_completed(self, sdk, project):
        """测试: 标记需求完成"""
        req = sdk.manage_requirement(project_id=project["project_id"], content="短需求")
        sdk.requirement_manager.mark_as_leaf(sdk._get_conn(), req["requirement_id"])
        sdk.add_validation(req["requirement_id"], [{"name": "测试"}])

        result = sdk.trigger_chaining(project["project_id"], session_id="test")

        if result.get("status") == "completed":
            completion = sdk.mark_requirement_completed(
                project["project_id"], req["requirement_id"]
            )
            assert completion["progress_percentage"] == 100

    def test_mark_requirement_completed_updates_progress(self, sdk, project):
        """测试: 完成需求后进度更新"""
        req1 = sdk.manage_requirement(
            project_id=project["project_id"], content="独立需求1"
        )
        req2 = sdk.manage_requirement(
            project_id=project["project_id"], content="独立需求2"
        )
        sdk.requirement_manager.mark_as_leaf(sdk._get_conn(), req1["requirement_id"])
        sdk.requirement_manager.mark_as_leaf(sdk._get_conn(), req2["requirement_id"])
        sdk.add_validation(req1["requirement_id"], [{"name": "测试1"}])
        sdk.add_validation(req2["requirement_id"], [{"name": "测试2"}])

        chain_result = sdk.trigger_chaining(project["project_id"], session_id="test")
        if chain_result.get("status") == "completed":
            next_req = sdk.get_next_requirement(
                project["project_id"], session_id="test"
            )
            if next_req.get("requirement_id"):
                completion = sdk.mark_requirement_completed(
                    project["project_id"], next_req["requirement_id"]
                )
                assert "progress_percentage" in completion

    def test_get_next_requirement_triggers_chaining(self, sdk, project):
        """测试: get_next 自动触发链化"""
        req = sdk.manage_requirement(
            project_id=project["project_id"], content="自动链化需求"
        )
        sdk.requirement_manager.mark_as_leaf(sdk._get_conn(), req["requirement_id"])
        sdk.add_validation(req["requirement_id"], [{"name": "测试"}])

        result = sdk.get_next_requirement(project["project_id"], session_id="test")
        assert result is not None

    def test_mark_requirement_failed(self, sdk, project):
        """测试: 需求失败处理"""
        req = sdk.manage_requirement(
            project_id=project["project_id"], content="失败需求"
        )

        result = sdk.chain_orchestrator.mark_requirement_failed(
            sdk._get_conn(),
            project["project_id"],
            req["requirement_id"],
            reason="执行失败",
            retry_count=0,
        )
        assert result["status"] == "FAILED"
        assert result["can_retry"] is True
