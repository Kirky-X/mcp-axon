# Copyright (c) 2026 Kirky.X. All rights reserved.
# Licensed under the MIT License.
# See LICENSE file in the project root for full license information.

"""数据一致性验收测试 (UAT-022 ~ UAT-023)"""

from src.core.sdk import RequirementSDK
from src.utils.cache import CacheManager


def test_uat022_transaction_integrity():
    """UAT-022: 事务完整性验收"""

    sdk = RequirementSDK(db_path=":memory:")
    project = sdk.create_project("测试项目")
    project_id = project["project_id"]

    # 测试成功的事务
    req = sdk.add_requirement(project_id, "需求")
    sdk.add_validation(req["requirement_id"], [{"name": "测试"}])

    # 验证所有数据都正确保存 - 通过 SDK API
    saved_req = sdk.get_requirement(req["requirement_id"])
    assert saved_req is not None
    assert saved_req["status"] == "VALIDATED"

    # 验证验证节点存在
    from src.services.validation_service import ValidationService

    cache = CacheManager()
    validation_service = ValidationService(cache=cache)
    saved_validation = validation_service.get_validation_by_requirement(
        sdk._get_conn(), req["requirement_id"]
    )
    assert saved_validation is not None

    # 验证事件记录
    from src.utils.event_logger import get_event_history

    events = get_event_history(sdk._get_conn(), project_id)
    assert (
        len(events) >= 3
    )  # RequirementAdded, RequirementMarkedAsLeaf, ValidationAdded

    # 测试失败的事务
    try:
        sdk.add_requirement(project_id, "")  # 空内容
        assert False, "应该抛出异常"
    except ValueError:
        pass

    # 验证没有创建需求
    state = sdk.get_project_state(project_id)
    # 应该只有之前创建的一个需求
    assert state["total_requirements"] == 1


def test_uat023_event_sourcing():
    """UAT-023: 事件溯源验收"""
    sdk = RequirementSDK(db_path=":memory:")
    project = sdk.create_project("测试项目")
    project_id = project["project_id"]

    # 执行一系列操作
    req = sdk.add_requirement(project_id, "需求")
    sdk.add_validation(req["requirement_id"], [{"name": "测试"}])

    # 查询事件表
    from src.utils.event_logger import get_event_history

    events = get_event_history(sdk._get_conn(), project_id)

    # 验证事件序列
    assert len(events) >= 3

    # 验证事件类型
    event_types = [e["event_type"] for e in events]
    assert "ProjectCreated" in event_types
    assert "RequirementAdded" in event_types
    # 需求默认是叶子节点，不再有 RequirementMarkedAsLeaf 事件
    assert "ValidationAdded" in event_types

    # 验证序列号连续
    sequences = [e["sequence"] for e in events]
    assert sequences == list(range(1, len(sequences) + 1))

    # 验证每个事件都有完整的上下文
    for event in events:
        assert event["event_type"] is not None
        assert event["aggregate_uuid"] is not None
        assert event["payload"] is not None
        assert event["created_at"] is not None

    # 测试根据事件重建状态
    # 简单验证：根据事件计算应该有多少需求
    requirement_added_count = sum(
        1 for e in events if e["event_type"] == "RequirementAdded"
    )
    requirement_deleted_count = sum(
        1 for e in events if e["event_type"] == "RequirementDeleted"
    )

    expected_count = requirement_added_count - requirement_deleted_count

    # 验证实际需求数量
    state = sdk.get_project_state(project_id)
    actual_count = state["total_requirements"]

    assert actual_count == expected_count
