# Copyright (c) 2026 Kirky.X. All rights reserved.
# Licensed under the MIT License.
# See LICENSE file in the project root for full license information.

"""安全审计工具

用于分析事件日志，检测安全问题和异常行为
"""

import logging
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from src.db.models import Event

logger = logging.getLogger(__name__)


class SecurityAuditor:
    """
    安全审计器

    分析事件日志，检测安全问题和异常行为
    """

    # 可疑事件类型
    SUSPICIOUS_EVENT_TYPES = [
        "SnapshotRestored",  # 快照恢复可能回滚恶意更改
        "RequirementDeleted",  # 删除需求可能破坏数据完整性
        "ProjectLocked",  # 锁定项目可能阻止合法用户
    ]

    # 危险操作阈值
    DANGEROUS_OPERATION_THRESHOLD = {
        "RequirementDeleted": 5,  # 5 分钟内删除超过 5 个需求
        "SnapshotRestored": 2,  # 5 分钟内恢复超过 2 个快照
        "ProjectLocked": 3,  # 5 分钟内锁定超过 3 个项目
    }

    def __init__(self, time_window_minutes: int = 5):
        """
        初始化审计器

        Args:
            time_window_minutes: 时间窗口（分钟）
        """
        self.time_window = timedelta(minutes=time_window_minutes)
        self.alerts: List[Dict[str, Any]] = []

    def audit_events(
        self, session: Session, project_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        审计事件

        Args:
            session: 数据库会话
            project_id: 项目 ID（可选）

        Returns:
            审计结果
        """
        self.alerts.clear()

        # 获取时间窗口内的事件
        cutoff_time = datetime.now(timezone.utc) - self.time_window

        query = session.query(Event).filter(Event.created_at >= cutoff_time)

        if project_id:
            query = query.filter_by(project_id=project_id)

        events = query.all()

        # 执行各种审计检查
        self._check_suspicious_operations(events)
        self._check_rapid_operations(events)
        self._check_unusual_patterns(events)
        self._check_session_anomalies(events)

        return {
            "time_window_minutes": self.time_window.seconds // 60,
            "events_analyzed": len(events),
            "alerts_detected": len(self.alerts),
            "alerts": self.alerts,
            "status": "safe" if not self.alerts else "warning",
        }

    def _check_suspicious_operations(self, events: List[Event]) -> None:
        """
        检查可疑操作

        Args:
            events: 事件列表
        """
        suspicious_events = [
            e for e in events if e.event_type in self.SUSPICIOUS_EVENT_TYPES
        ]

        for event in suspicious_events:
            alert = {
                "severity": "medium",
                "type": "suspicious_operation",
                "event_type": event.event_type,
                "project_id": event.project_id,
                "aggregate_id": event.aggregate_id,
                "timestamp": event.created_at.isoformat(),
                "session_id": (
                    event.event_metadata.get("session_id")
                    if event.event_metadata
                    else None
                ),
                "description": f"检测到可疑操作: {event.event_type}",
            }
            self.alerts.append(alert)

    def _check_rapid_operations(self, events: List[Event]) -> None:
        """
        检查快速操作（可能表示攻击）

        Args:
            events: 事件列表
        """
        # 按事件类型和会话统计
        operation_counts: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))

        for event in events:
            session_id = (
                event.event_metadata.get("session_id")
                if event.event_metadata
                else "unknown"
            )
            # 确保 session_id 是字符串
            session_id_str = str(session_id) if session_id is not None else "unknown"
            operation_counts[event.event_type][session_id_str] += 1

        # 检查是否超过阈值
        for event_type, counts in operation_counts.items():
            threshold = self.DANGEROUS_OPERATION_THRESHOLD.get(event_type, float("inf"))

            for session_id, count in counts.items():
                if count > threshold:
                    alert = {
                        "severity": "high",
                        "type": "rapid_operations",
                        "event_type": event_type,
                        "count": count,
                        "threshold": threshold,
                        "session_id": session_id,
                        "description": (
                            f"检测到快速操作: {event_type} 在 {self.time_window.seconds // 60} 分钟内"
                            f"执行了 {count} 次（阈值: {threshold}）"
                        ),
                    }
                    self.alerts.append(alert)

    def _check_unusual_patterns(self, events: List[Event]) -> None:
        """
        检查异常模式

        Args:
            events: 事件列表
        """
        # 检查循环依赖检测失败
        cycle_detection_events = [e for e in events if e.event_type == "CycleDetected"]

        if len(cycle_detection_events) > 0:
            alert = {
                "severity": "medium",
                "type": "cycle_dependency",
                "count": len(cycle_detection_events),
                "description": f"检测到 {len(cycle_detection_events)} 次循环依赖",
            }
            self.alerts.append(alert)

        # 检查链化失败
        chain_failure_events = [e for e in events if e.event_type == "ChainFailed"]

        if len(chain_failure_events) > 0:
            alert = {
                "severity": "high",
                "type": "chain_failure",
                "count": len(chain_failure_events),
                "description": f"检测到 {len(chain_failure_events)} 次链化失败",
            }
            self.alerts.append(alert)

    def _check_session_anomalies(self, events: List[Event]) -> None:
        """
        检查会话异常

        Args:
            events: 事件列表
        """
        # 按会话统计事件数
        session_counts: Dict[str, int] = defaultdict(int)

        for event in events:
            session_id = (
                event.event_metadata.get("session_id")
                if event.event_metadata
                else "unknown"
            )
            # 确保 session_id 是字符串
            session_id_str = str(session_id) if session_id is not None else "unknown"
            session_counts[session_id_str] += 1

        # 检查异常活跃的会话
        avg_events = len(events) / len(session_counts) if session_counts else 0

        for session_id, count in session_counts.items():
            if count > avg_events * 3:  # 超过平均值 3 倍
                alert = {
                    "severity": "medium",
                    "type": "session_anomaly",
                    "session_id": session_id,
                    "event_count": count,
                    "average_count": avg_events,
                    "description": (
                        f"会话 {session_id} 异常活跃: {count} 次操作"
                        f"（平均: {avg_events:.1f} 次）"
                    ),
                }
                self.alerts.append(alert)

    def get_audit_summary(self) -> Dict[str, Any]:
        """
        获取审计摘要

        Returns:
            审计摘要
        """
        severity_counts: Dict[str, int] = defaultdict(int)

        for alert in self.alerts:
            severity_counts[alert["severity"]] += 1

        return {
            "total_alerts": len(self.alerts),
            "severity_counts": dict(severity_counts),
            "alert_types": list(set(alert["type"] for alert in self.alerts)),
        }


class SecurityReportGenerator:
    """
    安全报告生成器

    生成详细的安全审计报告
    """

    def __init__(self):
        """初始化报告生成器"""
        self.auditor = SecurityAuditor()

    def generate_report(
        self, session: Session, project_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        生成安全报告

        Args:
            session: 数据库会话
            project_id: 项目 ID（可选）

        Returns:
            安全报告
        """
        # 执行审计
        audit_result = self.auditor.audit_events(session, project_id)

        # 生成报告
        report = {
            "report_type": "security_audit",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "project_id": project_id,
            "audit_result": audit_result,
            "recommendations": self._generate_recommendations(audit_result),
        }

        return report

    def _generate_recommendations(
        self, audit_result: Dict[str, Any]
    ) -> List[Dict[str, str]]:
        """
        根据审计结果生成建议

        Args:
            audit_result: 审计结果

        Returns:
            建议列表
        """
        recommendations = []

        for alert in audit_result["alerts"]:
            severity = alert["severity"]
            alert_type = alert["type"]

            if alert_type == "suspicious_operation":
                recommendations.append(
                    {
                        "priority": "high" if severity == "high" else "medium",
                        "recommendation": (
                            f"审查可疑操作 '{alert['event_type']}'，"
                            f"确认是否为合法用户操作"
                        ),
                    }
                )

            elif alert_type == "rapid_operations":
                recommendations.append(
                    {
                        "priority": "high",
                        "recommendation": (
                            f"检测到快速操作 '{alert['event_type']}'，"
                            f"可能存在自动化攻击，建议检查会话 {alert['session_id']}"
                        ),
                    }
                )

            elif alert_type == "cycle_dependency":
                recommendations.append(
                    {
                        "priority": "medium",
                        "recommendation": (
                            "检测到循环依赖，建议审查需求依赖关系，"
                            "避免创建复杂的依赖网络"
                        ),
                    }
                )

            elif alert_type == "chain_failure":
                recommendations.append(
                    {
                        "priority": "high",
                        "recommendation": (
                            "检测到链化失败，建议检查需求验证状态和依赖关系"
                        ),
                    }
                )

            elif alert_type == "session_anomaly":
                recommendations.append(
                    {
                        "priority": "medium",
                        "recommendation": (
                            f"会话 {alert['session_id']} 异常活跃，"
                            f"建议检查是否为合法用户或自动化工具"
                        ),
                    }
                )

        return recommendations


# 全局审计器实例
security_auditor = SecurityAuditor()
report_generator = SecurityReportGenerator()


def perform_security_audit(
    session: Session, project_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    执行安全审计

    Args:
        session: 数据库会话
        project_id: 项目 ID（可选）

    Returns:
        审计结果
    """
    return report_generator.generate_report(session, project_id)


# 使用示例
if __name__ == "__main__":
    print("安全审计工具已加载")
