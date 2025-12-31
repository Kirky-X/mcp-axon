# Copyright (c) 2026 Kirky.X. All rights reserved.
# Licensed under the MIT License.
# See LICENSE file in the project root for full license information.

"""性能验收测试 (UAT-015 ~ UAT-016)"""

import pytest
import time
from src.core.sdk import RequirementSDK


def test_uat015_database_performance():
    """UAT-015: 数据库操作性能"""

    sdk = RequirementSDK(db_path=":memory:")
    project = sdk.create_project("性能测试")

    # 执行 100 次 add_requirement 操作
    times = []
    for _ in range(100):
        start = time.perf_counter()
        sdk.add_requirement(project["project_id"], "需求")
        elapsed = (time.perf_counter() - start) * 1000
        times.append(elapsed)

    # 计算 P95
    times.sort()
    p95 = times[int(len(times) * 0.95)]

    # Assert: P95 < 50ms
    assert p95 < 50, f"P95 耗时 {p95:.2f}ms 超过 50ms"


def test_uat016_large_scale_performance():
    """UAT-016: 大规模需求树性能"""
    sdk = RequirementSDK(db_path=":memory:")
    project = sdk.create_project("大规模测试")

    # 创建 2000 个需求
    for i in range(2000):
        req = sdk.add_requirement(project["project_id"], f"需求{i}")
        sdk.mark_as_leaf(req["requirement_id"])
        sdk.add_validation(req["requirement_id"], [{"name": f"测试{i}"}])

    # 测试链化性能
    start = time.perf_counter()
    result = sdk.get_next_requirement(project["project_id"])
    elapsed = (time.perf_counter() - start) * 1000

    # Assert: < 2000ms
    assert elapsed < 2000, f"耗时 {elapsed:.2f}ms 超过 2000ms"
    assert result["status"] in ["needs_sorting", "ready"]

    # 测试项目状态查询性能
    start = time.perf_counter()
    state = sdk.get_project_state(project["project_id"])
    elapsed = (time.perf_counter() - start) * 1000

    # Assert: < 100ms
    assert elapsed < 100, f"耗时 {elapsed:.2f}ms 超过 100ms"
    assert state["total_requirements"] == 2000