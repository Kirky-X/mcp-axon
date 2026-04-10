# Copyright (c) 2026 Kirky.X. All rights reserved.
# Licensed under the MIT License.
# See LICENSE file in the project root for full license information.

"""快照测试"""

from src.core.sdk import RequirementSDK


def test_tc023_snapshot_restore():
    """TC-023: 测试快照恢复"""
    sdk = RequirementSDK(db_path=":memory:")
    project = sdk.manage_project(name="测试项目")
    project_id = project["project_id"]

    req1 = sdk.manage_requirement(project_id=project_id, content="需求1")
    sdk.add_validation(req1["requirement_id"], [{"name": "测试1"}])

    snapshot_id = sdk.create_snapshot(project_id, "test-session-123456789")

    sdk.manage_requirement(project_id=project_id, content="需求2")

    result = sdk.restore_snapshot(snapshot_id, "test-session-123456789")
    assert result["restored_count"] >= 0

    state = sdk.get_project_state(project_id)
    assert state["total_requirements"] == 1


def test_list_snapshots():
    """测试列出快照"""
    sdk = RequirementSDK(db_path=":memory:")
    project = sdk.manage_project(name="测试项目")
    project_id = project["project_id"]

    snapshot1 = sdk.create_snapshot(project_id, "test-session-1")
    snapshot2 = sdk.create_snapshot(project_id, "test-session-2")
    snapshot3 = sdk.create_snapshot(project_id, "test-session-3")

    snapshots = sdk.list_snapshots(project_id, limit=10)

    assert len(snapshots) == 3
    assert any(s["snapshot_id"] == snapshot1 for s in snapshots)
    assert any(s["snapshot_id"] == snapshot2 for s in snapshots)
    assert any(s["snapshot_id"] == snapshot3 for s in snapshots)


def test_list_snapshots_limit():
    """测试列出快照（带限制）"""
    sdk = RequirementSDK(db_path=":memory:")
    project = sdk.manage_project(name="测试项目")
    project_id = project["project_id"]

    for _ in range(5):
        sdk.create_snapshot(project_id, "test-session")

    snapshots = sdk.list_snapshots(project_id, limit=3)

    assert len(snapshots) == 3
