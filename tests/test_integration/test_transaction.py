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
    sdk.manage_project(name="测试项目")

    # 创建父需求和子需求
    parent = sdk.manage_requirement(project_id="父需求")
    sdk.manage_requirement(project_id="子需求", parent_id=parent["requirement_id"])

    # 尝试为非叶子节点（父需求）添加验证（应失败）
    with pytest.raises(ValueError, match="只能为叶子节点添加验证"):
        sdk.add_validation(parent["requirement_id"], [{"name": "测试"}])

    # Assert: 验证节点未创建（使用 SDK 内置的 validation_service）
    validation = sdk.validation_service.get_validation_by_requirement(
        sdk._get_conn(), parent["requirement_id"]
    )
    assert validation is None


def test_transaction_success():
    """测试成功的事务"""
    # Arrange
    sdk = RequirementSDK(db_path=":memory:")
    sdk.manage_project(name="测试项目")

    # Act
    req = sdk.manage_requirement(project_id="需求")
    validation = sdk.add_validation(req["requirement_id"], [{"name": "测试"}])

    # Assert: 所有操作都成功
    assert validation["validation_id"] is not None

    # 验证通过 SDK 内置的 validation_service
    saved_validation = sdk.validation_service.get_validation_by_requirement(
        sdk._get_conn(), req["requirement_id"]
    )

    assert saved_validation is not None


def test_transaction_partial_failure():
    """测试部分失败的事务"""
    # Arrange
    sdk = RequirementSDK(db_path=":memory:")
    sdk.manage_project(name="测试项目")

    # Act: 创建需求后尝试删除不存在的需求
    req = sdk.manage_requirement(project_id="需求")

    with pytest.raises(ValueError, match="需求不存在"):
        sdk.delete_requirement("nonexistent-id")

    # Assert: 原始需求应该仍然存在
    saved_req = sdk.get_requirement(req["requirement_id"])
    assert saved_req is not None
    assert saved_req["requirement_id"] == req["requirement_id"]
