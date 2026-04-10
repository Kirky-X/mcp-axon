# Copyright (c) 2026 Kirky.X. All rights reserved.
# Licensed under the MIT License.
# See LICENSE file in the project root for full license information.

"""需求管理补充测试"""

import pytest

from src.core.containers import init_container
from src.core.sdk import RequirementSDK
from src.schemas import RequirementUpdate


@pytest.fixture
def sdk():
    init_container(db_path=":memory:")
    return RequirementSDK(db_path=":memory:")


@pytest.fixture
def project(sdk):
    return sdk.manage_project(name="需求管理测试项目")


class TestRequirementManagerBatch:
    """批量需求操作测试"""

    def test_batch_add_requirements(self, sdk, project):
        """测试: 批量添加需求"""
        result = sdk.requirement_manager.batch_add_requirements(
            sdk._get_conn(),
            project["project_id"],
            [
                {"content": "批量需求1"},
                {"content": "批量需求2"},
                {"content": "批量需求3"},
            ],
        )
        assert result["success"] == 3
        assert result["failed"] == 0

    def test_batch_add_with_parent(self, sdk, project):
        """测试: 批量添加子需求"""
        parent = sdk.manage_requirement(
            project_id=project["project_id"], content="父需求"
        )
        result = sdk.requirement_manager.batch_add_requirements(
            sdk._get_conn(),
            project["project_id"],
            [{"content": "子需求1"}, {"content": "子需求2"}],
            parent_uuid=parent["requirement_id"],
        )
        assert result["success"] == 2

    def test_batch_add_empty_content_fails(self, sdk, project):
        """测试: 批量添加空内容失败"""
        result = sdk.requirement_manager.batch_add_requirements(
            sdk._get_conn(),
            project["project_id"],
            [{"content": "有效需求"}, {"content": ""}, {"content": "  "}],
        )
        assert result["success"] == 1
        assert result["failed"] == 2

    def test_batch_update_requirements(self, sdk, project):
        """测试: 批量更新需求"""
        req1 = sdk.manage_requirement(project_id=project["project_id"], content="需求1")
        req2 = sdk.manage_requirement(project_id=project["project_id"], content="需求2")

        updates = [
            {"requirement_id": req1["requirement_id"], "content": "更新1"},
            {"requirement_id": req2["requirement_id"], "content": "更新2"},
        ]
        result = sdk.requirement_manager.batch_update_requirements(
            sdk._get_conn(), updates
        )
        assert result["success"] == 2
        assert result["failed"] == 0

    def test_batch_update_with_invalid_id(self, sdk, project):
        """测试: 批量更新包含无效 ID"""
        req = sdk.manage_requirement(project_id=project["project_id"], content="需求")
        updates = [
            {"requirement_id": req["requirement_id"], "content": "更新"},
            {
                "requirement_id": "00000000-0000-0000-0000-000000000000",
                "content": "无效",
            },
        ]
        result = sdk.requirement_manager.batch_update_requirements(
            sdk._get_conn(), updates
        )
        assert result["success"] == 1
        assert result["failed"] == 1


class TestRequirementManagerBoundary:
    """需求管理边界测试"""

    def test_max_depth_exceeded(self, sdk, project):
        """测试: 超过最大深度"""
        from src.constants import Limits

        current = None
        for i in range(Limits.MAX_DEPTH + 2):
            parent_id = current["requirement_id"] if current else None
            try:
                current = sdk.manage_requirement(
                    project_id=project["project_id"],
                    content=f"层级{i}",
                    parent_id=parent_id,
                )
            except ValueError as e:
                assert "层级超过限制" in str(e) or "需求不存在" in str(e)
                return
        pytest.fail("应该抛出层级超过限制异常")

    def test_parent_not_found(self, sdk, project):
        """测试: 父需求不存在"""
        with pytest.raises(ValueError, match="父需求不存在|需求不存在"):
            sdk.manage_requirement(
                project["project_id"],
                "孤儿需求",
                parent_id="00000000-0000-0000-0000-000000000000",
            )

    def test_update_chained_requirement_rejected(self, sdk, project):
        """测试: 已链化的需求不允许更新"""
        from src.db.graph_models import RequirementStatus

        req = sdk.manage_requirement(project_id=project["project_id"], content="短需求")
        # 直接设置 CHAINED 状态
        sdk.requirement_manager.update_requirement(
            sdk._get_conn(),
            req["requirement_id"],
            RequirementUpdate(content=None, status=RequirementStatus.CHAINED.value),
        )
        # 再次更新应该被拒绝
        with pytest.raises(ValueError, match="已链化"):
            sdk.requirement_manager.update_requirement(
                sdk._get_conn(),
                req["requirement_id"],
                RequirementUpdate(content="新内容"),
            )

    def test_delete_with_incoming_dependencies(self, sdk, project):
        """测试: 被依赖的需求无法删除"""
        req1 = sdk.manage_requirement(project_id=project["project_id"], content="需求1")
        req2 = sdk.manage_requirement(project_id=project["project_id"], content="需求2")
        # req2 依赖 req1
        sdk.dependency_service.add_dependency(
            sdk._get_conn(), req2["requirement_id"], req1["requirement_id"]
        )
        # 删除 req1 应该失败
        with pytest.raises(ValueError, match="被以下需求依赖"):
            sdk.delete_requirement(req1["requirement_id"])

    def test_mark_as_leaf_with_children(self, sdk, project):
        """测试: 有子需求时无法标记为叶子"""
        parent = sdk.manage_requirement(
            project_id=project["project_id"], content="父需求"
        )
        sdk.manage_requirement(
            project_id=project["project_id"],
            content="子需求",
            parent_id=parent["requirement_id"],
        )
        with pytest.raises(ValueError, match="存在子需求"):
            sdk.requirement_manager.mark_as_leaf(
                sdk._get_conn(), parent["requirement_id"]
            )
