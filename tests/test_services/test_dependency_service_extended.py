# Copyright (c) 2026 Kirky.X. All rights reserved.
# Licensed under the MIT License.
# See LICENSE file in the project root for full license information.

"""依赖服务补充测试"""

import pytest

from src.core.containers import init_container
from src.core.sdk import RequirementSDK


@pytest.fixture
def sdk():
    """创建测试 SDK 实例"""
    init_container(db_path=":memory:")
    return RequirementSDK(db_path=":memory:")


@pytest.fixture
def project(sdk):
    """创建测试项目"""
    return sdk.manage_project(name="依赖测试项目")


class TestDependencyServiceExtended:
    """依赖服务补充测试"""

    def test_transfer_dependencies_single_child(self, sdk, project):
        """测试: 单子需求依赖传递"""
        parent = sdk.manage_requirement(
            project_id=project["project_id"], content="父需求"
        )
        child = sdk.manage_requirement(
            project_id=project["project_id"],
            content="子需求",
            parent_id=parent["requirement_id"],
        )
        # 先给父需求添加依赖
        ext_dep = sdk.manage_requirement(
            project_id=project["project_id"], content="外部依赖需求"
        )
        sdk.dependency_service.add_dependency(
            sdk._get_conn(), parent["requirement_id"], ext_dep["requirement_id"]
        )

        # 传递依赖
        result = sdk.dependency_service.transfer_dependencies(
            sdk._get_conn(),
            parent["requirement_id"],
            {child["requirement_id"]: [ext_dep["requirement_id"]]},
        )
        assert "parent_id" in result or "message" in result

    def test_transfer_dependencies_multiple_children(self, sdk, project):
        """测试: 多子需求依赖传递"""
        parent = sdk.manage_requirement(
            project_id=project["project_id"], content="父需求"
        )
        child1 = sdk.manage_requirement(
            project_id=project["project_id"],
            content="子需求1",
            parent_id=parent["requirement_id"],
        )
        child2 = sdk.manage_requirement(
            project_id=project["project_id"],
            content="子需求2",
            parent_id=parent["requirement_id"],
        )
        ext_dep = sdk.manage_requirement(
            project_id=project["project_id"], content="外部依赖"
        )

        result = sdk.dependency_service.transfer_dependencies(
            sdk._get_conn(),
            parent["requirement_id"],
            {
                child1["requirement_id"]: [ext_dep["requirement_id"]],
                child2["requirement_id"]: [ext_dep["requirement_id"]],
            },
        )
        assert "parent_id" in result or "message" in result

    def test_get_dependency_chain(self, sdk, project):
        """测试: 获取依赖链"""
        req1 = sdk.manage_requirement(project_id=project["project_id"], content="需求1")
        req2 = sdk.manage_requirement(project_id=project["project_id"], content="需求2")
        req3 = sdk.manage_requirement(project_id=project["project_id"], content="需求3")

        # req2 依赖 req1
        sdk.dependency_service.add_dependency(
            sdk._get_conn(), req2["requirement_id"], req1["requirement_id"]
        )
        # req3 依赖 req2
        sdk.dependency_service.add_dependency(
            sdk._get_conn(), req3["requirement_id"], req2["requirement_id"]
        )

        # 获取依赖链
        deps = sdk.dependency_service.get_dependency_chain(
            sdk._get_conn(), req3["requirement_id"]
        )
        assert len(deps) >= 1

    def test_remove_dependency(self, sdk, project):
        """测试: 移除依赖关系"""
        req1 = sdk.manage_requirement(project_id=project["project_id"], content="需求1")
        req2 = sdk.manage_requirement(project_id=project["project_id"], content="需求2")

        sdk.dependency_service.add_dependency(
            sdk._get_conn(), req2["requirement_id"], req1["requirement_id"]
        )
        # 移除依赖
        sdk.dependency_service.remove_dependency(
            sdk._get_conn(), req2["requirement_id"], req1["requirement_id"]
        )

        # 验证已移除
        deps = sdk.dependency_service.get_dependencies(
            sdk._get_conn(), req2["requirement_id"]
        )
        assert req1["requirement_id"] not in deps

    def test_get_dependents(self, sdk, project):
        """测试: 获取依赖者"""
        req1 = sdk.manage_requirement(project_id=project["project_id"], content="需求1")
        req2 = sdk.manage_requirement(project_id=project["project_id"], content="需求2")
        req3 = sdk.manage_requirement(project_id=project["project_id"], content="需求3")

        # req2 和 req3 都依赖 req1
        sdk.dependency_service.add_dependency(
            sdk._get_conn(), req2["requirement_id"], req1["requirement_id"]
        )
        sdk.dependency_service.add_dependency(
            sdk._get_conn(), req3["requirement_id"], req1["requirement_id"]
        )

        dependents = sdk.dependency_service.get_dependents(
            sdk._get_conn(), req1["requirement_id"]
        )
        assert len(dependents) == 2

    def test_duplicate_dependency_rejected(self, sdk, project):
        """测试: 重复依赖被拒绝"""
        req1 = sdk.manage_requirement(project_id=project["project_id"], content="需求1")
        req2 = sdk.manage_requirement(project_id=project["project_id"], content="需求2")

        sdk.dependency_service.add_dependency(
            sdk._get_conn(), req2["requirement_id"], req1["requirement_id"]
        )
        # 再次添加相同依赖应该抛出异常
        with pytest.raises(ValueError):
            sdk.dependency_service.add_dependency(
                sdk._get_conn(), req2["requirement_id"], req1["requirement_id"]
            )
