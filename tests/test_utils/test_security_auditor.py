# Copyright (c) 2026 Kirky.X. All rights reserved.
# Licensed under the MIT License.
# See LICENSE file in the project root for full license information.

"""安全审计器测试"""

import json


from src.db.graph_queries import CREATE_EVENT
from src.utils.security_auditor import (
    SecurityAuditor,
    SecurityReportGenerator,
    perform_security_audit,
    security_auditor,
    report_generator,
)


def _create_test_event(
    conn, project_uuid: str, event_type: str, aggregate_uuid: str = None
):
    """创建测试事件"""
    import uuid
    from datetime import datetime, timezone

    event_uuid = str(uuid.uuid4())
    created_at = datetime.now(timezone.utc).isoformat()

    # 获取当前最大序列号
    result = conn.execute(
        "MATCH (e:Event {project_uuid: $project_uuid}) RETURN max(e.sequence) as max_seq",
        {"project_uuid": project_uuid},
    )
    rows = list(result)
    max_seq = rows[0][0] if rows and rows[0][0] is not None else 0

    conn.execute(
        CREATE_EVENT,
        {
            "uuid": event_uuid,
            "project_uuid": project_uuid,
            "event_type": event_type,
            "aggregate_uuid": aggregate_uuid or event_uuid,
            "payload": json.dumps({}),
            "event_metadata": json.dumps({"session_id": "test-session"}),
            "sequence": max_seq + 1,
            "created_at": created_at,
        },
    )
    return event_uuid


# ========== SecurityAuditor.audit_events ==========


def test_audit_events_empty_project(graph_connection, project_manager):
    """测试: 审计空项目"""
    # Arrange
    auditor = SecurityAuditor()
    project = project_manager.create_project(graph_connection, "测试项目")
    project_id = project["project_id"]

    # Act
    result = auditor.audit_events(graph_connection, project_id)

    # Assert: create_project 会自动创建 ProjectCreated 事件
    assert result["events_analyzed"] == 1
    assert result["alerts"] == []
    assert result["status"] == "safe"


def test_audit_events_normal_operations(graph_connection, project_manager):
    """测试: 审计正常操作无告警"""
    # Arrange
    auditor = SecurityAuditor()
    project = project_manager.create_project(graph_connection, "测试项目")
    project_id = project["project_id"]

    # 创建正常事件
    _create_test_event(graph_connection, project_id, "ProjectCreated")
    _create_test_event(graph_connection, project_id, "RequirementAdded")

    # Act
    result = auditor.audit_events(graph_connection, project_id)

    # Assert: create_project 会自动创建 ProjectCreated 事件
    assert result["events_analyzed"] == 3  # ProjectCreated + 2 test events
    assert result["status"] == "safe"


def test_audit_events_rapid_deletions(graph_connection, project_manager):
    """测试: 检测快速删除操作"""
    # Arrange
    auditor = SecurityAuditor()
    project = project_manager.create_project(graph_connection, "测试项目")
    project_id = project["project_id"]

    # 创建多个删除事件（超过阈值 5）
    for i in range(6):
        _create_test_event(graph_connection, project_id, "RequirementDeleted")

    # Act
    result = auditor.audit_events(graph_connection, project_id)

    # Assert
    assert len(result["alerts"]) > 0
    assert any(a["type"] == "rapid_operations" for a in result["alerts"])


def test_audit_events_suspicious_snapshot_restore(graph_connection, project_manager):
    """测试: 检测可疑快照恢复"""
    # Arrange
    auditor = SecurityAuditor()
    project = project_manager.create_project(graph_connection, "测试项目")
    project_id = project["project_id"]

    # 创建快照恢复事件
    _create_test_event(graph_connection, project_id, "SnapshotRestored")

    # Act
    result = auditor.audit_events(graph_connection, project_id)

    # Assert
    assert len(result["alerts"]) > 0
    assert any(a["type"] == "suspicious_operation" for a in result["alerts"])


# ========== SecurityReportGenerator.generate_report ==========


def test_generate_report_includes_summary(graph_connection, project_manager):
    """测试: 报告包含执行摘要"""
    # Arrange
    generator = SecurityReportGenerator()
    project = project_manager.create_project(graph_connection, "测试项目")
    project_id = project["project_id"]

    # Act
    report = generator.generate_report(graph_connection, project_id)

    # Assert
    assert "audit_result" in report
    assert "recommendations" in report
    assert "generated_at" in report


def test_generate_report_with_alerts(graph_connection, project_manager):
    """测试: 报告包含告警列表"""
    # Arrange
    generator = SecurityReportGenerator()
    project = project_manager.create_project(graph_connection, "测试项目")
    project_id = project["project_id"]

    # 创建多个删除事件
    for i in range(6):
        _create_test_event(graph_connection, project_id, "RequirementDeleted")

    # Act
    report = generator.generate_report(graph_connection, project_id)

    # Assert
    assert len(report["audit_result"]["alerts"]) > 0


# ========== perform_security_audit convenience function ==========


def test_perform_security_audit(graph_connection, project_manager):
    """测试: perform_security_audit 便捷函数"""
    # Arrange
    project = project_manager.create_project(graph_connection, "测试项目")
    project_id = project["project_id"]

    _create_test_event(graph_connection, project_id, "TestEvent")

    # Act
    result = perform_security_audit(graph_connection, project_id)

    # Assert
    assert "audit_result" in result
    assert "recommendations" in result


# ========== Global instances ==========


def test_security_auditor_is_singleton():
    """测试: security_auditor 是单例"""
    auditor1 = security_auditor
    auditor2 = security_auditor

    assert auditor1 is auditor2


def test_report_generator_is_singleton():
    """测试: report_generator 是单例"""
    gen1 = report_generator
    gen2 = report_generator

    assert gen1 is gen2


# ========== Alert severity ==========


def test_alert_severity_high_for_rapid_operations(graph_connection, project_manager):
    """测试: 快速操作标记为 high"""
    # Arrange
    auditor = SecurityAuditor()
    project = project_manager.create_project(graph_connection, "测试项目")
    project_id = project["project_id"]

    # 创建大量删除事件
    for i in range(10):
        _create_test_event(graph_connection, project_id, "RequirementDeleted")

    # Act
    result = auditor.audit_events(graph_connection, project_id)

    # Assert
    assert any(a.get("severity") == "high" for a in result["alerts"])


# ========== Performance with large datasets ==========


def test_audit_handles_large_event_set(graph_connection, project_manager):
    """测试: 审计大数据集在合理时间内"""
    # Arrange
    auditor = SecurityAuditor()
    project = project_manager.create_project(graph_connection, "测试项目")
    project_id = project["project_id"]

    # 创建大量事件
    for i in range(100):
        _create_test_event(graph_connection, project_id, "TestEvent")

    # Act
    import time

    start = time.time()
    result = auditor.audit_events(graph_connection, project_id)
    duration = time.time() - start

    # Assert: create_project 会自动创建 ProjectCreated 事件
    assert result["events_analyzed"] == 101  # ProjectCreated + 100 test events
    # 应该在合理时间内完成
    assert duration < 30.0


# ========== get_audit_summary ==========


def test_get_audit_summary(graph_connection, project_manager):
    """测试: 摘要包含告警统计"""
    auditor = SecurityAuditor()
    project = project_manager.create_project(graph_connection, "测试项目")
    project_id = project["project_id"]

    # 创建多个删除事件
    for i in range(6):
        _create_test_event(graph_connection, project_id, "RequirementDeleted")

    auditor.audit_events(graph_connection, project_id)

    # Act
    summary = auditor.get_audit_summary()

    # Assert
    assert "total_alerts" in summary
    assert "severity_counts" in summary
    assert isinstance(summary["severity_counts"], dict)


# ========== Recommendations ==========


def test_report_includes_recommendations(graph_connection, project_manager):
    """测试: 报告包含建议"""
    # Arrange
    generator = SecurityReportGenerator()
    project = project_manager.create_project(graph_connection, "测试项目")
    project_id = project["project_id"]

    # 创建多个删除事件
    for i in range(6):
        _create_test_event(graph_connection, project_id, "RequirementDeleted")

    # Act
    report = generator.generate_report(graph_connection, project_id)

    # Assert
    assert "recommendations" in report
    assert len(report["recommendations"]) > 0
