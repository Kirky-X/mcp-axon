# Copyright (c) 2026 Kirky.X. All rights reserved.
# Licensed under the MIT License.
# See LICENSE file in the project root for full license information.

"""MCP 服务器核心测试"""

import os

os.environ["MCP_AXON_DB_PATH"] = ":memory:"

from src.api.mcp_server import (
    SessionContext,
    get_sdk,
    get_tool_router,
)


class TestSessionContext:
    """会话上下文测试"""

    def test_session_id_generation(self):
        """测试: 生成唯一会话 ID"""
        session = SessionContext()
        assert session.session_id is not None
        assert len(session.session_id) > 0

    def test_session_ids_are_unique(self):
        """测试: 每个会话 ID 唯一"""
        s1 = SessionContext()
        s2 = SessionContext()
        assert s1.session_id != s2.session_id


class TestSDK:
    """SDK 测试"""

    def test_get_sdk_returns_instance(self):
        """测试: get_sdk 返回 SDK 实例"""
        sdk = get_sdk()
        assert sdk is not None
        assert sdk.project_manager is not None

    def test_get_sdk_is_singleton(self):
        """测试: get_sdk 返回单例"""
        sdk1 = get_sdk()
        sdk2 = get_sdk()
        assert sdk1 is sdk2


class TestMCPToolIntegration:
    """MCP 工具集成测试"""

    def test_full_requirement_lifecycle(self):
        """测试: 完整需求生命周期"""
        router = get_tool_router()

        # 1. 创建项目
        project = router.route("manage_project", {"name": "生命周期项目"})
        project_id = project["project_id"]

        # 2. 添加根需求
        root = router.route(
            "manage_requirement",
            {"project_id": project_id, "content": "根需求"},
        )
        root_id = root["requirement_id"]

        # 3. 添加子需求
        child = router.route(
            "manage_requirement",
            {
                "project_id": project_id,
                "content": "子需求",
                "parent_id": root_id,
            },
        )
        child_id = child["requirement_id"]

        # 4. 添加依赖
        router.route(
            "add_dependency",
            {"requirement_id": child_id, "dependency_id": root_id},
        )

        # 5. 查询项目状态
        state = router.route("get_project_state", {"project_id": project_id})
        assert state["total_requirements"] == 2

        # 6. 更新需求
        updated = router.route(
            "manage_requirement",
            {"requirement_id": child_id, "content": "更新后的子需求"},
        )
        assert updated["content"] == "更新后的子需求"

        # 7. 列出需求
        listing = router.route("list_requirements", {"project_id": project_id})
        assert listing["total"] == 2

    def test_validation_workflow(self):
        """测试: 验证节点工作流"""
        router = get_tool_router()

        project = router.route("manage_project", {"name": "验证工作流项目"})
        project_id = project["project_id"]

        req = router.route(
            "manage_requirement",
            {"project_id": project_id, "content": "短需求"},
        )
        req_id = req["requirement_id"]

        # 标记为叶子
        router.route("mark_as_leaf", {"requirement_id": req_id})

        # 添加验证
        validation = router.route(
            "add_validation",
            {
                "requirement_id": req_id,
                "test_cases": [
                    {
                        "name": "测试用例",
                        "steps": ["步骤1", "步骤2"],
                        "expected_result": "成功",
                    }
                ],
                "acceptance_criteria": "验收标准",
            },
        )
        assert validation["validation_id"] is not None

    def test_snapshot_workflow(self):
        """测试: 快照工作流"""
        router = get_tool_router()

        project = router.route("manage_project", {"name": "快照工作流项目"})
        project_id = project["project_id"]

        # 创建快照
        snapshot = router.route(
            "create_snapshot",
            {"project_id": project_id, "_session_id": "test"},
        )
        snapshot_id = snapshot["snapshot_id"]
        assert snapshot_id is not None

        # 列出快照
        snapshots = router.route("list_snapshots", {"project_id": project_id})
        assert len(snapshots["snapshots"]) >= 1

    def test_lock_workflow(self):
        """测试: 锁工作流"""
        router = get_tool_router()

        project = router.route("manage_project", {"name": "锁工作流项目"})
        project_id = project["project_id"]

        # 获取锁
        acquire = router.route(
            "acquire_lock",
            {"project_id": project_id, "session_id": "session1"},
        )
        assert acquire["success"] is True

        # 检查锁定
        locked = router.route("is_locked", {"project_id": project_id})
        assert locked["locked"] is True

        # 释放锁
        release = router.route(
            "release_lock",
            {"project_id": project_id, "session_id": "session1"},
        )
        assert release["success"] is True

        # 检查未锁定
        unlocked = router.route("is_locked", {"project_id": project_id})
        assert unlocked["locked"] is False
