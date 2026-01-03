# Copyright (c) 2026 Kirky.X. All rights reserved.
# Licensed under the MIT License.
# See LICENSE file in the project root for full license information.

"""数据一致性验收测试 (UAT-022 ~ UAT-023)"""

from src.core.sdk import RequirementSDK


def test_uat022_transaction_integrity():
    """UAT-022: 事务完整性验收"""

    sdk = RequirementSDK(db_path=":memory:")
    project = sdk.create_project("测试项目")

    # 测试成功的事务
    req = sdk.add_requirement(project["project_id"], "需求")
    # 需求默认是叶子节点(req["requirement_id"])
    sdk.add_validation(req["requirement_id"], [{"name": "测试"}])

    # 验证所有数据都正确保存
    with sdk._get_session() as session:
        from src.db.models import Event, Requirement, ValidationNode

        # 验证需求存在
        saved_req = session.get(Requirement, req["requirement_id"])
        assert saved_req is not None
        assert saved_req.status == "VALIDATED"

        # 验证验证节点存在
        saved_validation = (
            session.query(ValidationNode)
            .filter_by(requirement_id=req["requirement_id"])
            .first()
        )
        assert saved_validation is not None

        # 验证事件记录
        events = session.query(Event).filter_by(project_id=project["project_id"]).all()
        assert (
            len(events) >= 3
        )  # RequirementAdded, RequirementMarkedAsLeaf, ValidationAdded

    # 测试失败的事务
    try:
        sdk.add_requirement(project["project_id"], "")  # 空内容
        assert False, "应该抛出异常"
    except ValueError:
        pass

    # 验证没有创建需求
    with sdk._get_session() as session:
        from src.db.models import Requirement

        reqs = (
            session.query(Requirement).filter_by(project_id=project["project_id"]).all()
        )
        # 应该只有之前创建的一个需求
        assert len(reqs) == 1


def test_uat023_event_sourcing():
    """UAT-023: 事件溯源验收"""
    sdk = RequirementSDK(db_path=":memory:")
    project = sdk.create_project("测试项目")

    # 执行一系列操作
    req = sdk.add_requirement(project["project_id"], "需求")
    # 需求默认是叶子节点(req["requirement_id"])
    sdk.add_validation(req["requirement_id"], [{"name": "测试"}])

    # 查询事件表
    with sdk._get_session() as session:
        from src.db.models import Event

        events = (
            session.query(Event)
            .filter_by(project_id=project["project_id"])
            .order_by(Event.sequence)
            .all()
        )

        # 验证事件序列
        assert len(events) >= 3

        # 验证事件类型
        event_types = [e.event_type for e in events]
        assert "ProjectCreated" in event_types
        assert "RequirementAdded" in event_types
        # 需求默认是叶子节点，不再有 RequirementMarkedAsLeaf 事件
        assert "ValidationAdded" in event_types

        # 验证序列号连续
        sequences = [e.sequence for e in events]
        assert sequences == list(range(1, len(sequences) + 1))

        # 验证每个事件都有完整的上下文
        for event in events:
            assert event.event_type is not None
            assert event.aggregate_id is not None
            assert event.payload is not None
            assert event.created_at is not None

    # 测试根据事件重建状态
    with sdk._get_session() as session:
        from src.db.models import Event, Requirement

        # 获取所有事件
        events = (
            session.query(Event)
            .filter_by(project_id=project["project_id"])
            .order_by(Event.sequence)
            .all()
        )

        # 简单验证：根据事件计算应该有多少需求
        requirement_added_count = sum(
            1 for e in events if e.event_type == "RequirementAdded"
        )
        requirement_deleted_count = sum(
            1 for e in events if e.event_type == "RequirementDeleted"
        )

        expected_count = requirement_added_count - requirement_deleted_count

        # 验证实际需求数量
        actual_count = (
            session.query(Requirement)
            .filter_by(project_id=project["project_id"])
            .count()
        )

        assert actual_count == expected_count
