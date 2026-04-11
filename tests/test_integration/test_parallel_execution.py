# Copyright (c) 2026 Kirky.X. All rights reserved.
# Licensed under the MIT License.
# See LICENSE file in the project root for full license information.

"""并行执行集成测试"""

from src.core.sdk import RequirementSDK


def test_parallel_group_integration():
    """测试 parallel_group 拓扑层级写入"""

    # Arrange: 创建多层级 DAG
    sdk = RequirementSDK(db_path=":memory:")
    project = sdk.manage_project(name="并行测试项目")
    project_id = project["project_id"]

    # 创建 3 层结构
    # Layer 0: A, B (并行)
    # Layer 1: C (依赖 A 和 B)
    # Layer 2: D (依赖 C)

    req_a = sdk.manage_requirement(project_id=project_id, content="任务A")
    req_b = sdk.manage_requirement(project_id=project_id, content="任务B")
    req_c = sdk.manage_requirement(project_id=project_id, content="任务C")
    req_d = sdk.manage_requirement(project_id=project_id, content="任务D")

    # 添加验证（标记为叶子节点）
    for req_id in [
        req_a["requirement_id"],
        req_b["requirement_id"],
        req_c["requirement_id"],
        req_d["requirement_id"],
    ]:
        sdk.add_validation(requirement_id=req_id, test_cases=[{"name": "测试"}])

    # 添加依赖: C 依赖 A 和 B, D 依赖 C
    sdk.add_dependency(req_c["requirement_id"], req_a["requirement_id"])
    sdk.add_dependency(req_c["requirement_id"], req_b["requirement_id"])
    sdk.add_dependency(req_d["requirement_id"], req_c["requirement_id"])

    # 触发链化
    sdk.trigger_chaining(project_id, "test-session-001")

    # Act: 获取需求验证 parallel_group
    result_a = sdk.get_requirement(requirement_id=req_a["requirement_id"])
    result_b = sdk.get_requirement(requirement_id=req_b["requirement_id"])
    result_c = sdk.get_requirement(requirement_id=req_c["requirement_id"])
    result_d = sdk.get_requirement(requirement_id=req_d["requirement_id"])

    # Assert: 验证拓扑层级
    assert result_a["parallel_group"] == 0  # Layer 0
    assert result_b["parallel_group"] == 0  # Layer 0 (与 A 并行)
    assert result_c["parallel_group"] == 1  # Layer 1 (依赖 Layer 0)
    assert result_d["parallel_group"] == 2  # Layer 2 (依赖 Layer 1)


def test_can_parallel_marker_integration():
    """测试 get_next_requirement 返回 can_parallel 标记"""

    # Arrange
    sdk = RequirementSDK(db_path=":memory:")
    project = sdk.manage_project(name="并行标记测试")
    project_id = project["project_id"]

    # 创建可并行的节点: A 和 B 无依赖
    req_a = sdk.manage_requirement(project_id=project_id, content="任务A")
    req_b = sdk.manage_requirement(project_id=project_id, content="任务B")
    req_c = sdk.manage_requirement(project_id=project_id, content="任务C")

    for req_id in [
        req_a["requirement_id"],
        req_b["requirement_id"],
        req_c["requirement_id"],
    ]:
        sdk.add_validation(requirement_id=req_id, test_cases=[{"name": "测试"}])

    # C 依赖 A 和 B
    sdk.add_dependency(req_c["requirement_id"], req_a["requirement_id"])
    sdk.add_dependency(req_c["requirement_id"], req_b["requirement_id"])

    sdk.trigger_chaining(project_id, "test-session-002")

    # Act: 获取第一个需求
    next_req = sdk.get_next_requirement(project_id, "test-session-002")

    # Assert: 第一个需求是 layer 0
    assert next_req["parallel_group"] == 0
    # 下一个也是 layer 0, 所以 can_parallel=True
    assert next_req["can_parallel"]

    # 标记当前需求完成
    current_id = next_req["requirement_id"]
    sdk.mark_requirement_completed(project_id, current_id)

    # 获取下一个需求
    next_req = sdk.get_next_requirement(project_id, "test-session-002")
    assert next_req["parallel_group"] == 0
    # 下一个 C 是 layer 1, 所以 can_parallel=False
    assert not next_req["can_parallel"]


def test_completed_status_integration():
    """测试 mark_requirement_completed 更新需求状态为 COMPLETED"""

    # Arrange
    sdk = RequirementSDK(db_path=":memory:")
    project = sdk.manage_project(name="完成状态测试")
    project_id = project["project_id"]

    req = sdk.manage_requirement(project_id=project_id, content="任务")
    sdk.add_validation(
        requirement_id=req["requirement_id"], test_cases=[{"name": "测试"}]
    )
    sdk.trigger_chaining(project_id, "test-session-003")

    # 验证初始状态
    before = sdk.get_requirement(requirement_id=req["requirement_id"])
    assert before["status"] == "CHAINED"

    # Act
    sdk.mark_requirement_completed(project_id, req["requirement_id"])

    # Assert
    after = sdk.get_requirement(requirement_id=req["requirement_id"])
    assert after["status"] == "COMPLETED"


def test_full_parallel_workflow():
    """测试完整的并行执行流程"""

    # Arrange: 创建复杂 DAG
    sdk = RequirementSDK(db_path=":memory:")
    project = sdk.manage_project(name="完整并行流程")
    project_id = project["project_id"]

    # 结构:
    #   A ──┬──> C ──> E
    #   B ──┘
    # A, B 并行, C 依赖两者, E 依赖 C

    nodes = {}
    for name in ["A", "B", "C", "E"]:
        nodes[name] = sdk.manage_requirement(
            project_id=project_id, content=f"任务{name}"
        )
        sdk.add_validation(
            requirement_id=nodes[name]["requirement_id"],
            test_cases=[{"name": f"测试{name}"}],
        )

    # 添加依赖
    sdk.add_dependency(nodes["C"]["requirement_id"], nodes["A"]["requirement_id"])
    sdk.add_dependency(nodes["C"]["requirement_id"], nodes["B"]["requirement_id"])
    sdk.add_dependency(nodes["E"]["requirement_id"], nodes["C"]["requirement_id"])

    # 链化
    result = sdk.trigger_chaining(project_id, "test-session-004")
    assert result["status"] == "completed"

    # 执行流程验证
    # 1. 第一个需求 (layer 0, can_parallel=True 因为下一个也是 layer 0)
    next_req = sdk.get_next_requirement(project_id, "test-session-004")
    assert next_req["parallel_group"] == 0
    assert next_req["can_parallel"]

    # 完成第一个需求
    first_id = next_req["requirement_id"]
    sdk.mark_requirement_completed(project_id, first_id)
    assert sdk.get_requirement(requirement_id=first_id)["status"] == "COMPLETED"

    # 2. 第二个需求 (layer 0, can_parallel=False 因为下一个 C 是 layer 1)
    next_req = sdk.get_next_requirement(project_id, "test-session-004")
    assert next_req["parallel_group"] == 0
    assert not next_req["can_parallel"]

    second_id = next_req["requirement_id"]
    sdk.mark_requirement_completed(project_id, second_id)
    assert sdk.get_requirement(requirement_id=second_id)["status"] == "COMPLETED"

    # 3. C (layer 1)
    next_req = sdk.get_next_requirement(project_id, "test-session-004")
    assert next_req["parallel_group"] == 1

    third_id = next_req["requirement_id"]
    sdk.mark_requirement_completed(project_id, third_id)
    assert sdk.get_requirement(requirement_id=third_id)["status"] == "COMPLETED"

    # 4. E (layer 2)
    next_req = sdk.get_next_requirement(project_id, "test-session-004")
    assert next_req["parallel_group"] == 2
    assert next_req["is_last"]

    fourth_id = next_req["requirement_id"]
    sdk.mark_requirement_completed(project_id, fourth_id)
    assert sdk.get_requirement(requirement_id=fourth_id)["status"] == "COMPLETED"

    # 项目完成
    final = sdk.get_next_requirement(project_id, "test-session-004")
    assert final["is_last"]
    assert final["progress_percentage"] == 100
