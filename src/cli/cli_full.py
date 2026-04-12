#!/usr/bin/env python
# Copyright (c) 2026 Kirky.X. All rights reserved.
# Axon Full CLI - 支持所有 8 个接口的完整版本

import argparse
import json
import os
import sys

from src.api.tool_router import ToolRouter
from src.core.sdk import RequirementSDK


def get_router() -> ToolRouter:
    """获取 ToolRouter 实例"""
    db_path = os.getenv("MCP_AXON_DB_PATH", "requirements.db")
    sdk = RequirementSDK(db_path=db_path)
    return ToolRouter(lambda: sdk)


def format_result(result: dict) -> str:
    """格式化输出结果"""
    if "error" in result:
        return f"错误: {result['error']}"
    return json.dumps(result, indent=2, ensure_ascii=False)


def main():
    parser = argparse.ArgumentParser(
        prog="axon", description="Axon - 需求分解与链式执行管理系统 (完整版)"
    )
    subparsers = parser.add_subparsers(dest="command", help="命令")

    # ========== 1. version ==========
    subparsers.add_parser("version", help="显示 API 版本信息")

    # ========== 2. project ==========
    project_parser = subparsers.add_parser("project", help="项目管理接口")
    project_sub = project_parser.add_subparsers(dest="action")

    # project get
    p_get = project_sub.add_parser("get", help="获取项目详情")
    p_get.add_argument("project_id", help="项目 UUID")

    # project create
    p_create = project_sub.add_parser("create", help="创建项目")
    p_create.add_argument("--name", "-n", required=True, help="项目名称")
    p_create.add_argument("--desc", "-d", default="", help="项目描述")

    # project update
    p_update = project_sub.add_parser("update", help="更新项目")
    p_update.add_argument("project_id", help="项目 UUID")
    p_update.add_argument("--name", "-n", help="新名称")
    p_update.add_argument("--desc", "-d", help="新描述")

    # ========== 3. requirement ==========
    req_parser = subparsers.add_parser("requirement", help="需求管理接口")
    req_sub = req_parser.add_subparsers(dest="action")

    # requirement get
    r_get = req_sub.add_parser("get", help="获取需求详情")
    r_get.add_argument("requirement_id", help="需求 UUID")

    # requirement create
    r_create = req_sub.add_parser("create", help="创建需求")
    r_create.add_argument("--project", "-p", required=True, help="项目 UUID")
    r_create.add_argument("--content", "-c", required=True, help="需求内容")
    r_create.add_argument("--parent", default=None, help="父需求 UUID")
    r_create.add_argument("--order", type=int, default=0, help="排序序号")

    # requirement update
    r_update = req_sub.add_parser("update", help="更新需求")
    r_update.add_argument("requirement_id", help="需求 UUID")
    r_update.add_argument("--content", "-c", help="新内容")
    r_update.add_argument("--status", "-s", help="新状态")

    # requirement delete
    r_delete = req_sub.add_parser("delete", help="删除需求")
    r_delete.add_argument("requirement_id", help="需求 UUID")

    # requirement mark-leaf
    r_leaf = req_sub.add_parser("mark-leaf", help="标记为叶子节点")
    r_leaf.add_argument("requirement_id", help="需求 UUID")

    # requirement list
    r_list = req_sub.add_parser("list", help="列出需求")
    r_list.add_argument("--project", "-p", required=True, help="项目 UUID")
    r_list.add_argument("--status", default=None, help="筛选状态")
    r_list.add_argument("--leaf", type=bool, default=None, help="是否叶子节点")
    r_list.add_argument("--parent", default=None, help="父需求 UUID")

    # ========== 4. dependency ==========
    dep_parser = subparsers.add_parser("dependency", help="依赖管理接口")
    dep_sub = dep_parser.add_subparsers(dest="action")

    # dependency add (单个)
    dep_add = dep_sub.add_parser("add", help="添加单个依赖")
    dep_add.add_argument("--requirement", "-r", required=True, help="需求 UUID")
    dep_add.add_argument("--dependency", "-d", required=True, help="依赖 UUID")

    # dependency transfer (批量)
    dep_transfer = dep_sub.add_parser("transfer", help="批量传递依赖")
    dep_transfer.add_argument("--parent", "-p", required=True, help="父需求 UUID")
    dep_transfer.add_argument("--mapping", "-m", required=True, help="依赖映射 JSON")

    # ========== 5. validation ==========
    val_parser = subparsers.add_parser("validation", help="验证管理接口")
    val_sub = val_parser.add_subparsers(dest="action")

    # validation add
    val_add = val_sub.add_parser("add", help="添加验证规则")
    val_add.add_argument("requirement_id", help="需求 UUID")
    val_add.add_argument("--cases", default="[]", help="测试用例 JSON 数组")
    val_add.add_argument("--criteria", "-c", default="", help="验收标准")

    # validation run
    val_run = val_sub.add_parser("run", help="执行验证")
    val_run.add_argument("requirement_id", help="需求 UUID")
    val_run.add_argument("--result", "-r", required=True, help="执行结果")

    # ========== 6. execution ==========
    exec_parser = subparsers.add_parser("execution", help="执行流程管理接口")
    exec_sub = exec_parser.add_subparsers(dest="action")

    # execution next
    exec_next = exec_sub.add_parser("next", help="获取下一个需求")
    exec_next.add_argument("project_id", help="项目 UUID")
    exec_next.add_argument("--session", default="", help="会话 ID")

    # execution complete
    exec_complete = exec_sub.add_parser("complete", help="标记需求完成")
    exec_complete.add_argument("project_id", help="项目 UUID")
    exec_complete.add_argument("--requirement", "-r", required=True, help="需求 UUID")

    # execution state
    exec_state = exec_sub.add_parser("state", help="获取项目状态")
    exec_state.add_argument("project_id", help="项目 UUID")

    # execution trigger
    exec_trigger = exec_sub.add_parser("trigger", help="触发链式执行")
    exec_trigger.add_argument("project_id", help="项目 UUID")
    exec_trigger.add_argument("--session", default="", help="会话 ID")

    # ========== 7. snapshot ==========
    snap_parser = subparsers.add_parser("snapshot", help="快照管理接口")
    snap_sub = snap_parser.add_subparsers(dest="action")

    # snapshot create
    snap_create = snap_sub.add_parser("create", help="创建快照")
    snap_create.add_argument("project_id", help="项目 UUID")
    snap_create.add_argument("--session", default="", help="会话 ID")

    # snapshot restore
    snap_restore = snap_sub.add_parser("restore", help="恢复快照")
    snap_restore.add_argument("snapshot_id", help="快照 UUID")
    snap_restore.add_argument("--session", default="", help="会话 ID")

    # snapshot list
    snap_list = snap_sub.add_parser("list", help="列出快照")
    snap_list.add_argument("--project", "-p", default=None, help="项目 UUID")
    snap_list.add_argument("--limit", type=int, default=10, help="数量限制")

    # ========== 8. lock ==========
    lock_parser = subparsers.add_parser("lock", help="锁管理接口")
    lock_sub = lock_parser.add_subparsers(dest="action")

    # lock acquire
    lock_acquire = lock_sub.add_parser("acquire", help="获取锁")
    lock_acquire.add_argument("project_id", help="项目 UUID")
    lock_acquire.add_argument("--session", "-s", required=True, help="会话 ID")

    # lock release
    lock_release = lock_sub.add_parser("release", help="释放锁")
    lock_release.add_argument("project_id", help="项目 UUID")
    lock_release.add_argument("--session", "-s", required=True, help="会话 ID")

    # lock check
    lock_check = lock_sub.add_parser("check", help="检查锁状态")
    lock_check.add_argument("project_id", help="项目 UUID")

    # lock info
    lock_info = lock_sub.add_parser("info", help="获取锁信息")
    lock_info.add_argument("project_id", help="项目 UUID")

    # ========== 解析参数并执行 ==========
    args = parser.parse_args()

    if args.command == "version":
        result = get_router().route("get_api_version", {})
        print(f"当前版本: {result.get('current_version', 'N/A')}")
        print(f"支持版本: {result.get('supported_versions', [])}")
        print(f"最小版本: {result.get('min_supported_version', 'N/A')}")
        return 0

    elif args.command == "project":
        router = get_router()
        if args.action == "get":
            result = router.route(
                "manage_project", {"action": "get", "project_id": args.project_id}
            )
            print(f"项目: {result.get('name', 'N/A')}")
            print(f"状态: {result.get('status', 'N/A')}")
            print(f"描述: {result.get('description', 'N/A')}")
            return 0
        elif args.action == "create":
            result = router.route(
                "manage_project",
                {"action": "create", "name": args.name, "description": args.desc},
            )
            print(f"项目创建成功: {result['project_id']}")
            return 0
        elif args.action == "update":
            result = router.route(
                "manage_project",
                {
                    "action": "update",
                    "project_id": args.project_id,
                    "name": args.name or "",
                    "description": args.desc or "",
                },
            )
            print(f"项目更新成功: {result.get('project_id', args.project_id)}")
            return 0

    elif args.command == "requirement":
        router = get_router()
        if args.action == "get":
            result = router.route(
                "manage_requirement",
                {"action": "get", "requirement_id": args.requirement_id},
            )
            print(f"ID: {result.get('uuid', 'N/A')}")
            print(f"内容: {result.get('content', 'N/A')}")
            print(f"状态: {result.get('status', 'N/A')}")
            print(f"叶子: {result.get('is_leaf', 'N/A')}")
            return 0
        elif args.action == "create":
            result = router.route(
                "manage_requirement",
                {
                    "action": "create",
                    "project_id": args.project,
                    "content": args.content,
                    "parent_id": args.parent,
                    "order_in_parent": args.order,
                },
            )
            print(f"需求创建成功: {result['requirement_id']}")
            return 0
        elif args.action == "update":
            result = router.route(
                "manage_requirement",
                {
                    "action": "update",
                    "requirement_id": args.requirement_id,
                    "content": args.content,
                    "status": args.status,
                },
            )
            print(f"需求更新成功: {args.requirement_id}")
            return 0
        elif args.action == "delete":
            result = router.route(
                "manage_requirement",
                {"action": "delete", "requirement_id": args.requirement_id},
            )
            print(f"需求删除成功: {args.requirement_id}")
            return 0
        elif args.action == "mark-leaf":
            result = router.route(
                "manage_requirement",
                {"action": "mark_leaf", "requirement_id": args.requirement_id},
            )
            print(f"已标记为叶子节点: {args.requirement_id}")
            return 0
        elif args.action == "list":
            result = router.route(
                "manage_requirement",
                {
                    "action": "list",
                    "project_id": args.project,
                    "status": args.status,
                    "is_leaf": args.leaf,
                    "parent_id": args.parent,
                },
            )
            print(f"需求列表 (共 {len(result.get('requirements', []))} 个):")
            for req in result.get("requirements", []):
                req_id = req.get("id", req.get("uuid", "N/A"))
                content = req.get("content", "")[:50]
                status = req.get("status", "N/A")
                print(f"  {req_id[:8]}... [{status}] {content}")
            return 0

    elif args.command == "dependency":
        router = get_router()
        if args.action == "add":
            result = router.route(
                "manage_dependency",
                {"requirement_id": args.requirement, "dependency_id": args.dependency},
            )
            print(f"依赖添加成功: {args.requirement} -> {args.dependency}")
            return 0
        elif args.action == "transfer":
            try:
                mapping = json.loads(args.mapping)
            except json.JSONDecodeError:
                print("错误: mapping 参数必须是有效 JSON")
                return 1
            result = router.route(
                "manage_dependency",
                {"parent_id": args.parent, "dependency_mapping": mapping},
            )
            print(f"依赖传递成功: {args.parent}")
            print(format_result(result))
            return 0

    elif args.command == "validation":
        router = get_router()
        if args.action == "add":
            try:
                cases = json.loads(args.cases)
            except json.JSONDecodeError:
                cases = []
            result = router.route(
                "manage_validation",
                {
                    "requirement_id": args.requirement_id,
                    "test_cases": cases,
                    "acceptance_criteria": args.criteria,
                },
            )
            print(f"验证规则添加成功: {args.requirement_id}")
            return 0
        elif args.action == "run":
            result = router.route(
                "manage_validation",
                {
                    "requirement_id": args.requirement_id,
                    "execution_result": args.result,
                },
            )
            print(f"验证执行完成: {args.requirement_id}")
            print(f"结果: {'通过' if result.get('validation_passed') else '失败'}")
            return 0

    elif args.command == "execution":
        router = get_router()
        if args.action == "next":
            result = router.route(
                "manage_execution",
                {
                    "action": "next",
                    "project_id": args.project_id,
                    "_session_id": args.session,
                },
            )
            if result.get("next_requirement_id"):
                print(f"下一个需求: {result['next_requirement_id']}")
            else:
                print("无下一个待执行需求")
            return 0
        elif args.action == "complete":
            result = router.route(
                "manage_execution",
                {
                    "action": "complete",
                    "project_id": args.project_id,
                    "requirement_id": args.requirement,
                },
            )
            print(f"需求标记完成: {args.requirement}")
            print(f"进度: {result.get('progress_percentage', 'N/A')}%")
            return 0
        elif args.action == "state":
            result = router.route(
                "manage_execution", {"action": "state", "project_id": args.project_id}
            )
            print("项目状态:")
            print(f"  总需求: {result.get('total_nodes', 'N/A')}")
            print(f"  已完成: {result.get('completed_nodes', 'N/A')}")
            print(f"  进度: {result.get('progress_percentage', 'N/A')}%")
            return 0
        elif args.action == "trigger":
            result = router.route(
                "manage_execution",
                {
                    "action": "trigger",
                    "project_id": args.project_id,
                    "_session_id": args.session,
                },
            )
            print("链式执行触发成功")
            print(format_result(result))
            return 0

    elif args.command == "snapshot":
        router = get_router()
        if args.action == "create":
            result = router.route(
                "manage_snapshot",
                {
                    "action": "create",
                    "project_id": args.project_id,
                    "_session_id": args.session,
                },
            )
            print(f"快照创建成功: {result.get('snapshot_id', 'N/A')}")
            return 0
        elif args.action == "restore":
            result = router.route(
                "manage_snapshot",
                {
                    "action": "restore",
                    "snapshot_id": args.snapshot_id,
                    "_session_id": args.session,
                },
            )
            print(f"快照恢复成功: {args.snapshot_id}")
            return 0
        elif args.action == "list":
            result = router.route(
                "manage_snapshot",
                {"action": "list", "project_id": args.project, "limit": args.limit},
            )
            print(f"快照列表 (共 {len(result.get('snapshots', []))} 个):")
            for snap in result.get("snapshots", []):
                snap_id = snap.get("snapshot_id", snap.get("id", "N/A"))
                ts = snap.get("created_at", "N/A")
                print(f"  {snap_id[:8]}... {ts}")
            return 0

    elif args.command == "lock":
        router = get_router()
        if args.action == "acquire":
            result = router.route(
                "manage_lock",
                {
                    "action": "acquire",
                    "project_id": args.project_id,
                    "session_id": args.session,
                },
            )
            print(f"锁获取{'成功' if result.get('success') else '失败'}")
            print(f"消息: {result.get('message', 'N/A')}")
            return 0
        elif args.action == "release":
            result = router.route(
                "manage_lock",
                {
                    "action": "release",
                    "project_id": args.project_id,
                    "session_id": args.session,
                },
            )
            print(f"锁释放{'成功' if result.get('success') else '失败'}")
            print(f"消息: {result.get('message', 'N/A')}")
            return 0
        elif args.action == "check":
            result = router.route(
                "manage_lock", {"action": "check", "project_id": args.project_id}
            )
            print(f"锁状态: {'已锁定' if result.get('locked') else '未锁定'}")
            return 0
        elif args.action == "info":
            result = router.route(
                "manage_lock", {"action": "info", "project_id": args.project_id}
            )
            info = result.get("lock_info")
            if info:
                print("锁信息:")
                print(f"  会话: {info.get('session_id', 'N/A')}")
                print(f"  时间: {info.get('acquired_at', 'N/A')}")
            else:
                print("未锁定")
            return 0

    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())
