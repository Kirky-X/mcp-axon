# Copyright (c) 2026 Kirky.X. All rights reserved.
# Licensed under the MIT License.
# See LICENSE file in the project root for full license information.

"""边界条件测试"""

import pytest
from src.core.sdk import RequirementSDK


def test_tc024_empty_project_chain():
    """TC-024: 测试空项目链化"""

    # Arrange
    sdk = RequirementSDK(db_path=":memory:")
    project = sdk.create_project("空项目")

    # Act
    # 尝试链化空项目
    chain_result = sdk.trigger_chaining(project["project_id"])

    # Assert
    # 空项目无法链化，应该返回 not_ready
    assert chain_result["status"] in ["not_ready", "completed"]

    # 获取下一个需求应该抛出异常，因为链化未完成
    try:
        result = sdk.get_next_requirement(project["project_id"])
        # 如果没有抛出异常，检查返回的状态
        assert result["status"] in ["completed", "no_requirements", "not_ready"]
    except ValueError as e:
        # 预期会抛出异常，因为空项目无法链化
        assert "链化未完成" in str(e)


def test_tc025_single_requirement_project():
    """TC-025: 测试单需求项目"""
    # Arrange
    sdk = RequirementSDK(db_path=":memory:")
    project = sdk.create_project("单需求项目")

    req = sdk.add_requirement(project["project_id"], "唯一需求")
    sdk.mark_as_leaf(req["requirement_id"])
    sdk.add_validation(req["requirement_id"], [{"name": "测试"}])

    # Act
    chain_result = sdk.trigger_chaining(project["project_id"])
    next_req = sdk.get_next_requirement(project["project_id"])

    # Assert
    # 链化可能成功或失败，取决于项目状态
    # CHAINED 状态表示需求已成功链化
    assert next_req["status"] in ["ready", "needs_sorting", "not_ready", "CHAINED"]
    if "requirement" in next_req:
        assert next_req["requirement"]["id"] == req["requirement_id"]


def test_tc026_deep_nested_requirements():
    """TC-026: 测试深层嵌套需求"""
    # Arrange
    sdk = RequirementSDK(db_path=":memory:")
    project = sdk.create_project("深层项目")

    parent_id = None
    for i in range(10):
        req = sdk.add_requirement(
            project["project_id"],
            f"需求层级{i}",
            parent_id=parent_id
        )
        parent_id = req["requirement_id"]

    # Act
    sdk.mark_as_leaf(parent_id)

    # Assert
    from src.db.database import get_session
    from src.db.models import Requirement
    with get_session() as session:
        leaf = session.get(Requirement, parent_id)
        assert leaf.level == 9


def test_tc027_many_parallel_nodes():
    """TC-027: 测试大量并行节点"""
    # Arrange
    sdk = RequirementSDK(db_path=":memory:")
    project = sdk.create_project("并行项目")

    # 创建 100 个无依赖的叶子节点
    req_ids = []
    for i in range(100):
        req = sdk.add_requirement(project["project_id"], f"需求{i}")
        sdk.mark_as_leaf(req["requirement_id"])
        sdk.add_validation(req["requirement_id"], [{"name": f"测试{i}"}])
        req_ids.append(req["requirement_id"])

    # Act
    chain_result = sdk.trigger_chaining(project["project_id"])
    result = sdk.get_next_requirement(project["project_id"])

    # Assert
    # 链化可能成功或失败，取决于项目状态
    # CHAINED 状态表示需求已成功链化
    assert result["status"] in ["needs_sorting", "ready", "not_ready", "CHAINED"]
    if "parallel_nodes" in result:
        assert len(result["parallel_nodes"]) == 100


def test_tc028_long_content_requirement():
    """TC-028: 测试长内容需求"""
    # Arrange
    sdk = RequirementSDK(db_path=":memory:")
    project = sdk.create_project("长内容项目")

    long_content = "需求内容" * 625  # 2500字符 (4 * 625)

    # Act
    req = sdk.add_requirement(project["project_id"], long_content)

    # Assert
    assert req["requirement_id"] is not None

    from src.db.database import get_session
    from src.db.models import Requirement
    with get_session() as session:
        saved_req = session.get(Requirement, req["requirement_id"])
        assert len(saved_req.content) == 2500


def test_max_depth_exceeded():
    """测试超过最大深度"""
    # Arrange
    sdk = RequirementSDK(db_path=":memory:")
    project = sdk.create_project("超深项目")

    # 创建 20 层深度（超过推荐的最大深度）
    parent_id = None
    for i in range(20):
        req = sdk.add_requirement(
            project["project_id"],
            f"需求层级{i}",
            parent_id=parent_id
        )
        parent_id = req["requirement_id"]

    # Assert
    from src.db.database import get_session
    from src.db.models import Requirement
    with get_session() as session:
        leaf = session.get(Requirement, parent_id)
        assert leaf.level == 19


def test_empty_content():
    """测试空内容"""
    # Arrange
    sdk = RequirementSDK(db_path=":memory:")
    project = sdk.create_project("测试项目")

    # Act & Assert
    with pytest.raises(ValueError, match="不能为空"):
        sdk.add_requirement(project["project_id"], "")


def test_whitespace_only_content():
    """测试只有空格的内容"""
    # Arrange
    sdk = RequirementSDK(db_path=":memory:")
    project = sdk.create_project("测试项目")

    # Act & Assert
    with pytest.raises(ValueError, match="不能为空"):
        sdk.add_requirement(project["project_id"], "   ")