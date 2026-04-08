# Copyright (c) 2026 Kirky.X. All rights reserved.
# Licensed under the MIT License.
# See LICENSE file in the project root for full license information.

"""状态快照管理器"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import real_ladybug as lb

from src.db.graph_queries import (
    CREATE_EVENT,
    GET_EVENT_BY_UUID,
    GET_EVENTS_BY_PROJECT_AND_TYPE,
    GET_LATEST_EVENT_SEQUENCE,
    GET_REQUIREMENTS_BY_PROJECT,
    GET_CHAIN_STATE_BY_PROJECT,
    DELETE_EVENT,
    GET_DEPENDENCIES,
    GET_NEXT_IN_CHAIN,
)
from src.db.graph_models import deserialize_json, serialize_json
from src.utils.event_logger import log_event

logger = logging.getLogger(__name__)


class SnapshotManager:
    """状态快照管理器"""

    def create_snapshot(
        self, conn: lb.Connection, project_id: str, session_id: str
    ) -> str:
        """
        创建状态快照

        Args:
            conn: LadybugDB 连接
            project_id: 项目 ID
            session_id: 会话 ID（用于权限验证）

        Returns:
            快照 ID（事件 ID）
        """
        logger.info(f"创建快照: {project_id}")

        # 获取所有需求
        result = conn.execute(GET_REQUIREMENTS_BY_PROJECT, {"project_uuid": project_id})
        requirements = self._parse_requirements(result)

        # 获取链化状态
        result = conn.execute(GET_CHAIN_STATE_BY_PROJECT, {"project_uuid": project_id})
        chain_state = self._parse_chain_state(list(result))

        # 构建快照数据
        snapshot_data: Dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "requirements": {},
            "chain_state": {},  # 空对象而非 None
        }

        # 收集需求状态
        for req in requirements:
            # 获取依赖
            dep_result = conn.execute(
                GET_DEPENDENCIES, {"requirement_uuid": req["uuid"]}
            )
            dependencies = [row[0] for row in dep_result]

            # 获取下一个需求
            next_result = conn.execute(GET_NEXT_IN_CHAIN, {"uuid": req["uuid"]})
            next_rows = list(next_result)
            next_uuid = next_rows[0][0] if next_rows else None

            snapshot_data["requirements"][req["uuid"]] = {
                "status": req["status"],
                "chain_order": req.get("chain_order")
                if req.get("chain_order") is not None
                else -1,
                "next_requirement_uuid": next_uuid if next_uuid is not None else "",
                "dependencies": dependencies,
            }

        # 链化状态
        if chain_state:
            snapshot_data["chain_state"] = {
                "status": chain_state["status"],
                "chain_head_uuid": chain_state.get("chain_head_uuid") or "",
                "current_node_uuid": chain_state.get("current_node_uuid") or "",
                "total_nodes": chain_state.get("total_nodes", 0),
                "completed_nodes": chain_state.get("completed_nodes", 0),
                "progress_percentage": chain_state.get("progress_percentage", 0),
            }

        # 保存快照到事件表
        snapshot_uuid = self._create_snapshot_event(
            conn, project_id, snapshot_data, session_id
        )

        logger.info(f"快照创建成功: {snapshot_uuid}")

        return snapshot_uuid

    def restore_snapshot(
        self, conn: lb.Connection, snapshot_id: str, session_id: str
    ) -> Dict[str, Any]:
        """
        从快照恢复

        Args:
            conn: LadybugDB 连接
            snapshot_id: 快照 ID（事件 ID）
            session_id: 会话 ID（用于权限验证）

        Returns:
            恢复结果
        """
        logger.info(f"从快照恢复: {snapshot_id}")

        # 获取快照事件
        result = conn.execute(GET_EVENT_BY_UUID, {"uuid": snapshot_id})
        rows = list(result)
        if not rows:
            raise ValueError(f"快照不存在: {snapshot_id}")

        snapshot_event = self._parse_event(rows[0])

        if snapshot_event["event_type"] != "SnapshotCreated":
            raise ValueError(f"事件类型不是快照: {snapshot_event['event_type']}")

        # 验证权限：快照必须属于当前会话创建的
        event_metadata = snapshot_event.get("event_metadata")
        if event_metadata and "session_id" in event_metadata:
            snapshot_session_id = event_metadata["session_id"]
            if snapshot_session_id != session_id:
                logger.warning(
                    f"权限拒绝: 会话 {session_id} 尝试恢复会话 {snapshot_session_id} 创建的快照"
                )
                raise ValueError("无权恢复此快照")

        snapshot_data = snapshot_event.get("payload")
        if not snapshot_data:
            raise ValueError("快照数据为空")

        project_id = snapshot_event["project_uuid"]

        # 获取快照中的需求 ID 集合
        snapshot_req_uuids = set(snapshot_data.get("requirements", {}).keys())

        # 获取当前所有需求
        result = conn.execute(GET_REQUIREMENTS_BY_PROJECT, {"project_uuid": project_id})
        current_requirements = self._parse_requirements(result)

        # 删除快照后创建的需求（不在快照中的需求）
        deleted_count = 0
        for current_req in current_requirements:
            if current_req["uuid"] not in snapshot_req_uuids:
                logger.info(f"删除快照后创建的需求: {current_req['uuid']}")
                conn.execute(
                    "MATCH (r:Requirement {uuid: $uuid}) DETACH DELETE r",
                    {"uuid": current_req["uuid"]},
                )
                deleted_count += 1

        # 恢复需求状态
        req_data = snapshot_data.get("requirements", {})
        restored_count = 0
        missing_count = 0

        for req_uuid, state in req_data.items():
            # 检查需求是否存在
            check_result = conn.execute(
                "MATCH (r:Requirement {uuid: $uuid}) RETURN r.uuid",
                {"uuid": req_uuid},
            )
            if not list(check_result):
                missing_count += 1
                logger.warning(f"快照中的需求在数据库中不存在: {req_uuid}")
                continue

            # 更新需求状态
            conn.execute(
                """
                MATCH (r:Requirement {uuid: $uuid})
                SET r.status = $status,
                    r.chain_order = $chain_order,
                    r.updated_at = $updated_at
                """,
                {
                    "uuid": req_uuid,
                    "status": state["status"],
                    "chain_order": state.get("chain_order"),
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                },
            )

            # 清除现有依赖关系
            conn.execute(
                "MATCH (r:Requirement {uuid: $uuid})-[e:DEPENDS_ON]->() DELETE e",
                {"uuid": req_uuid},
            )

            # 重建依赖关系
            for dep_uuid in state.get("dependencies", []):
                conn.execute(
                    """
                    MATCH (r1:Requirement {uuid: $req_uuid})
                    MATCH (r2:Requirement {uuid: $dep_uuid})
                    CREATE (r1)-[:DEPENDS_ON]->(r2)
                    """,
                    {"req_uuid": req_uuid, "dep_uuid": dep_uuid},
                )

            # 清除现有 NEXT_IN_CHAIN 关系
            conn.execute(
                "MATCH (r:Requirement {uuid: $uuid})-[e:NEXT_IN_CHAIN]->() DELETE e",
                {"uuid": req_uuid},
            )

            # 重建 NEXT_IN_CHAIN 关系
            next_uuid = state.get("next_requirement_uuid")
            if next_uuid:
                conn.execute(
                    """
                    MATCH (r1:Requirement {uuid: $from_uuid})
                    MATCH (r2:Requirement {uuid: $to_uuid})
                    CREATE (r1)-[:NEXT_IN_CHAIN]->(r2)
                    """,
                    {"from_uuid": req_uuid, "to_uuid": next_uuid},
                )

            restored_count += 1

        if missing_count > 0:
            logger.warning(f"快照恢复警告: {missing_count} 个需求在数据库中不存在")

        # 恢复链化状态
        chain_data = snapshot_data.get("chain_state")
        if chain_data:
            result = conn.execute(
                GET_CHAIN_STATE_BY_PROJECT, {"project_uuid": project_id}
            )
            chain_rows = list(result)

            if chain_rows:
                conn.execute(
                    """
                    MATCH (cs:ChainState {project_uuid: $project_uuid})
                    SET cs.status = $status,
                        cs.chain_head_uuid = $chain_head_uuid,
                        cs.current_node_uuid = $current_node_uuid,
                        cs.total_nodes = $total_nodes,
                        cs.completed_nodes = $completed_nodes,
                        cs.progress_percentage = $progress_percentage,
                        cs.chain_version = cs.chain_version + 1,
                        cs.updated_at = $updated_at
                    """,
                    {
                        "project_uuid": project_id,
                        "status": chain_data["status"],
                        "chain_head_uuid": chain_data.get("chain_head_uuid"),
                        "current_node_uuid": chain_data.get("current_node_uuid"),
                        "total_nodes": chain_data.get("total_nodes", 0),
                        "completed_nodes": chain_data.get("completed_nodes", 0),
                        "progress_percentage": chain_data.get("progress_percentage", 0),
                        "updated_at": datetime.now(timezone.utc).isoformat(),
                    },
                )
            else:
                logger.warning(f"项目中不存在链化状态: {project_id}")

        # 记录恢复事件
        log_event(
            conn,
            project_id,
            "SnapshotRestored",
            project_id,
            {
                "snapshot_id": snapshot_id,
                "restored_count": restored_count,
                "deleted_count": deleted_count,
                "missing_count": missing_count,
            },
        )

        logger.info(
            f"快照恢复成功: {snapshot_id}, 恢复 {restored_count} 个需求, 删除 {deleted_count} 个"
        )

        return {
            "snapshot_id": snapshot_id,
            "restored_count": restored_count,
            "deleted_count": deleted_count,
            "missing_count": missing_count,
            "message": "快照恢复成功",
        }

    def get_latest_snapshot(
        self, conn: lb.Connection, project_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        获取最新的快照

        Args:
            conn: LadybugDB 连接
            project_id: 项目 ID

        Returns:
            快照数据，如果没有快照则返回 None
        """
        result = conn.execute(
            GET_EVENTS_BY_PROJECT_AND_TYPE,
            {"project_uuid": project_id, "event_type": "SnapshotCreated", "limit": 1},
        )
        rows = list(result)
        if not rows:
            return None

        event = self._parse_event(rows[0])
        return {
            "snapshot_id": event["uuid"],
            "created_at": event["created_at"].isoformat()
            if event["created_at"]
            else None,
            "data": event.get("payload"),
        }

    def list_snapshots(
        self, conn: lb.Connection, project_id: str, limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        列出项目的所有快照

        Args:
            conn: LadybugDB 连接
            project_id: 项目 ID
            limit: 返回数量限制

        Returns:
            快照列表
        """
        query = """
        MATCH (e:Event {project_uuid: $project_uuid, event_type: 'SnapshotCreated'})
        RETURN e.uuid, e.created_at, e.sequence
        ORDER BY e.created_at DESC
        LIMIT $limit
        """
        result = conn.execute(query, {"project_uuid": project_id, "limit": limit})

        snapshots = []
        for row in result:
            snapshots.append(
                {
                    "snapshot_id": row[0],
                    "created_at": row[1],
                    "sequence": row[2],
                }
            )
        return snapshots

    def delete_snapshot(self, conn: lb.Connection, snapshot_id: str) -> bool:
        """
        删除快照

        Args:
            conn: LadybugDB 连接
            snapshot_id: 快照 ID

        Returns:
            是否删除成功
        """
        # 检查快照是否存在
        result = conn.execute(GET_EVENT_BY_UUID, {"uuid": snapshot_id})
        rows = list(result)
        if not rows:
            return False

        event = self._parse_event(rows[0])
        if event["event_type"] != "SnapshotCreated":
            return False

        conn.execute(DELETE_EVENT, {"uuid": snapshot_id})

        logger.info(f"快照删除成功: {snapshot_id}")

        return True

    def _create_snapshot_event(
        self,
        conn: lb.Connection,
        project_id: str,
        snapshot_data: Dict[str, Any],
        session_id: str,
    ) -> str:
        """创建快照事件"""
        # 获取最新序列号
        result = conn.execute(GET_LATEST_EVENT_SEQUENCE, {"project_uuid": project_id})
        rows = list(result)
        max_sequence = rows[0][0] if rows and rows[0][0] else 0
        sequence = max_sequence + 1

        # 生成 UUID
        import uuid

        event_uuid = str(uuid.uuid4())

        # 创建事件
        conn.execute(
            CREATE_EVENT,
            {
                "uuid": event_uuid,
                "project_uuid": project_id,
                "event_type": "SnapshotCreated",
                "aggregate_uuid": project_id,
                "payload": serialize_json(snapshot_data),
                "event_metadata": serialize_json({"session_id": session_id}),
                "sequence": sequence,
                "created_at": datetime.now(timezone.utc).isoformat(),
            },
        )

        # 创建 HAS_EVENT 关系
        conn.execute(
            """
            MATCH (p:Project {uuid: $project_uuid})
            MATCH (e:Event {uuid: $event_uuid})
            CREATE (p)-[:HAS_EVENT]->(e)
            """,
            {"project_uuid": project_id, "event_uuid": event_uuid},
        )

        return event_uuid

    def _parse_requirements(self, result) -> List[Dict[str, Any]]:
        """解析需求结果"""
        requirements = []
        for row in result:
            req = {
                "uuid": row[0],
                "project_uuid": row[1],
                "parent_uuid": row[2],
                "content": row[3],
                "decompose_reason": row[4],
                "status": row[5],
                "level": row[6],
                "order_in_parent": row[7],
                "chain_order": row[8],
                "created_at": row[9],
                "updated_at": row[10],
                "version": row[11],
                "dependencies": row[12] if len(row) > 12 else [],
            }
            requirements.append(req)
        return requirements

    def _parse_chain_state(self, rows: List) -> Optional[Dict[str, Any]]:
        """解析链化状态结果"""
        if not rows:
            return None
        row = rows[0]
        return {
            "uuid": row[0],
            "project_uuid": row[1],
            "status": row[2],
            "chain_head_uuid": row[3],
            "current_node_uuid": row[4],
            "total_nodes": row[5],
            "completed_nodes": row[6],
            "progress_percentage": row[7],
            "last_chained_at": row[8],
            "chain_version": row[9],
            "created_at": row[10],
            "updated_at": row[11],
        }

    def _parse_event(self, row) -> Dict[str, Any]:
        """解析事件结果"""
        return {
            "uuid": row[0],
            "project_uuid": row[1],
            "event_type": row[2],
            "aggregate_uuid": row[3],
            "payload": self._parse_json(row[4]),
            "event_metadata": self._parse_json(row[5]),
            "sequence": row[6],
            "created_at": self._parse_datetime(row[7]),
        }

    def _parse_json(self, data: Optional[str]) -> Optional[Dict]:
        """解析 JSON 数据"""
        if not data:
            return None
        try:
            return deserialize_json(data)
        except Exception:
            return None

    def _parse_datetime(self, dt_str: Optional[str]) -> Optional[datetime]:
        """解析日期时间字符串"""
        if not dt_str:
            return None
        try:
            dt = datetime.fromisoformat(dt_str)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        except ValueError:
            return None
