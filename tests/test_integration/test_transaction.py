# Copyright (c) 2026 Kirky.X. All rights reserved.
# Licensed under the MIT License.
# See LICENSE file in the project root for full license information.

"""事务测试"""

import pytest
from src.core.sdk import RequirementSDK


def test_tc022_transaction_rollback():
    """TC-022: 测试事务回滚"""

    # Arrange
    sdk = RequirementSDK(db_path=":memory:")
    project = sdk.create_project("测试项目")

    # Act: 尝试为非叶子节点添加验证（应失败）
    req = sdk.add_requirement(project["project_id"], "非叶子需求")

    with pytest.raises(ValueError, match="只能为叶子节点添加验证"):
        sdk.add_validation(
            req["requirement_id"],
            [{"name": "测试"}]
        )

    # Assert: 验证节点未创建
    from src.db.database import get_session
    with get_session() as session:
        from src.db.models import ValidationNode
        validation = session.query(ValidationNode).filter_by(
            requirement_id=req["requirement_id"]
        ).first()
        assert validation is None


def test_transaction_success():
    """测试成功的事务"""
    # Arrange
    sdk = RequirementSDK(db_path=":memory:")
    project = sdk.create_project("测试项目")

    # Act
    req = sdk.add_requirement(project["project_id"], "需求")
    sdk.mark_as_leaf(req["requirement_id"])
    validation = sdk.add_validation(
        req["requirement_id"],
        [{"name": "测试"}]
    )

    # Assert: 所有操作都成功
    assert validation["validation_id"] is not None

    with sdk._get_session() as session:
        from src.db.models import Requirement, ValidationNode
        saved_req = session.get(Requirement, req["requirement_id"])
        saved_validation = session.query(ValidationNode).filter_by(
            requirement_id=req["requirement_id"]
        ).first()

        assert saved_req is not None
        assert saved_validation is not None


def test_transaction_partial_failure():
    """测试部分失败的事务"""
    # Arrange
    sdk = RequirementSDK(db_path=":memory:")
    project = sdk.create_project("测试项目")

    # Act: 创建需求后尝试删除不存在的需求
    req = sdk.add_requirement(project["project_id"], "需求")

    with pytest.raises(ValueError, match="需求不存在"):
        sdk.delete_requirement("nonexistent-id")

    # Assert: 原始需求应该仍然存在
    with sdk._get_session() as session:
        from src.db.models import Requirement
        saved_req = session.get(Requirement, req["requirement_id"])
        assert saved_req is not None