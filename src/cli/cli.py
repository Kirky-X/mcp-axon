# Copyright (c) 2026 Kirky.X. All rights reserved.
# Licensed under the MIT License.
# See LICENSE file in the project root for full license information.

"""MCP-Axon CLI - 命令行接口"""

from typing import Annotated

import typer

from src.api.tool_router import ToolRouter
from src.core.containers import init_container

app = typer.Typer(
    name="axon",
    help="MCP-Axon - 需求分解与链式执行管理系统",
    add_completion=False,
)

# 初始化 SDK
_router: ToolRouter | None = None


def get_router() -> ToolRouter:
    """获取 ToolRouter 实例（延迟初始化）"""
    global _router
    if _router is None:
        container = init_container()
        sdk = container.requirement_sdk()
        _router = ToolRouter(lambda: sdk)
    return _router


# ========== 项目管理 ==========

project_app = typer.Typer(help="项目管理")
app.add_typer(project_app, name="project")


@project_app.command("create")
def project_create(
    name: Annotated[str, typer.Option("--name", "-n", help="项目名称")],
    description: Annotated[str, typer.Option("--desc", "-d", help="项目描述")] = "",
) -> None:
    """创建新项目"""
    result = get_router().route(
        "manage_project", {"action": "create", "name": name, "description": description}
    )
    typer.echo(f"✅ 项目创建成功: {result['project_id']}")


@project_app.command("get")
def project_get(
    project_id: Annotated[str, typer.Argument(help="项目 ID")],
) -> None:
    """获取项目信息"""
    result = get_router().route(
        "manage_project", {"action": "get", "project_id": project_id}
    )
    typer.echo(f"项目: {result.get('name', 'N/A')}")
    typer.echo(f"状态: {result.get('status', 'N/A')}")
    typer.echo(f"需求总数: {result.get('total_requirements', 0)}")


@project_app.command("update")
def project_update(
    project_id: Annotated[str, typer.Argument(help="项目 ID")],
    name: Annotated[str | None, typer.Option("--name", "-n", help="新项目名称")] = None,
    description: Annotated[
        str | None, typer.Option("--desc", "-d", help="新项目描述")
    ] = None,
) -> None:
    """更新项目信息"""
    args = {"action": "update", "project_id": project_id}
    if name:
        args["name"] = name
    if description:
        args["description"] = description
    result = get_router().route("manage_project", args)
    typer.echo(f"✅ 项目更新成功: {result['project_id']}")


# ========== 需求管理 ==========

requirement_app = typer.Typer(help="需求管理")
app.add_typer(requirement_app, name="requirement")


@requirement_app.command("create")
def requirement_create(
    project_id: Annotated[str, typer.Option("--project", "-p", help="项目 ID")],
    content: Annotated[str, typer.Option("--content", "-c", help="需求内容")],
    parent_id: Annotated[str | None, typer.Option("--parent", help="父需求 ID")] = None,
) -> None:
    """创建新需求"""
    args = {"action": "create", "project_id": project_id, "content": content}
    if parent_id:
        args["parent_id"] = parent_id
    result = get_router().route("manage_requirement", args)
    typer.echo(f"✅ 需求创建成功: {result['requirement_id']}")
    if result.get("next_action"):
        typer.echo(f"下一步: {result['next_action']}")


@requirement_app.command("get")
def requirement_get(
    requirement_id: Annotated[str, typer.Argument(help="需求 ID")],
) -> None:
    """获取需求信息"""
    result = get_router().route(
        "manage_requirement", {"action": "get", "requirement_id": requirement_id}
    )
    typer.echo(f"内容: {result.get('content', 'N/A')}")
    typer.echo(f"状态: {result.get('status', 'N/A')}")
    typer.echo(f"叶子节点: {result.get('is_leaf', False)}")


@requirement_app.command("list")
def requirement_list(
    project_id: Annotated[str, typer.Option("--project", "-p", help="项目 ID")],
    status: Annotated[
        str | None, typer.Option("--status", "-s", help="状态过滤")
    ] = None,
    parent_id: Annotated[str | None, typer.Option("--parent", help="父需求 ID")] = None,
) -> None:
    """列出项目需求"""
    args = {"action": "list", "project_id": project_id}
    if status:
        args["status"] = status
    if parent_id:
        args["parent_id"] = parent_id
    result = get_router().route("manage_requirement", args)
    for req in result.get("requirements", []):
        status_icon = "✅" if req.get("status") == "completed" else "⏳"
        leaf_icon = "🍃" if req.get("is_leaf") else "📦"
        typer.echo(
            f"{status_icon} {leaf_icon} {req['requirement_id'][:8]}... {req.get('content', '')[:50]}"
        )


@requirement_app.command("update")
def requirement_update(
    requirement_id: Annotated[str, typer.Argument(help="需求 ID")],
    content: Annotated[
        str | None, typer.Option("--content", "-c", help="新需求内容")
    ] = None,
    status: Annotated[str | None, typer.Option("--status", "-s", help="新状态")] = None,
) -> None:
    """更新需求"""
    args = {"action": "update", "requirement_id": requirement_id}
    if content:
        args["content"] = content
    if status:
        args["status"] = status
    get_router().route("manage_requirement", args)
    typer.echo("✅ 需求更新成功")


@requirement_app.command("delete")
def requirement_delete(
    requirement_id: Annotated[str, typer.Argument(help="需求 ID")],
) -> None:
    """删除需求"""
    get_router().route(
        "manage_requirement", {"action": "delete", "requirement_id": requirement_id}
    )
    typer.echo("✅ 需求删除成功")


@requirement_app.command("mark-leaf")
def requirement_mark_leaf(
    requirement_id: Annotated[str, typer.Argument(help="需求 ID")],
) -> None:
    """标记为叶子节点"""
    get_router().route(
        "manage_requirement", {"action": "mark_leaf", "requirement_id": requirement_id}
    )
    typer.echo("✅ 已标记为叶子节点")


# ========== 依赖管理 ==========

dependency_app = typer.Typer(help="依赖管理")
app.add_typer(dependency_app, name="dependency")


@dependency_app.command("add")
def dependency_add(
    requirement_id: Annotated[str, typer.Argument(help="需求 ID")],
    dependency_id: Annotated[str, typer.Argument(help="依赖的需求 ID")],
) -> None:
    """添加依赖关系"""
    get_router().route(
        "manage_dependency",
        {"requirement_id": requirement_id, "dependency_id": dependency_id},
    )
    typer.echo("✅ 依赖添加成功")


@dependency_app.command("transfer")
def dependency_transfer(
    parent_id: Annotated[str, typer.Argument(help="父需求 ID")],
    mapping: Annotated[
        str, typer.Option("--mapping", "-m", help="依赖映射 JSON")
    ] = "{}",
) -> None:
    """传递依赖关系"""
    import json

    try:
        dependency_mapping = json.loads(mapping)
    except json.JSONDecodeError:
        typer.echo("❌ 映射 JSON 格式无效")
        raise typer.Exit(1) from None

    result = get_router().route(
        "manage_dependency",
        {"parent_id": parent_id, "dependency_mapping": dependency_mapping},
    )
    typer.echo(f"✅ 依赖传递成功，更新了 {result.get('total_children', 0)} 个子需求")


# ========== 验证管理 ==========

validation_app = typer.Typer(help="验证管理")
app.add_typer(validation_app, name="validation")


@validation_app.command("add")
def validation_add(
    requirement_id: Annotated[str, typer.Argument(help="需求 ID")],
    test_cases: Annotated[
        str, typer.Option("--tests", "-t", help="测试用例 JSON")
    ] = "[]",
) -> None:
    """添加测试用例"""
    import json

    try:
        cases = json.loads(test_cases)
    except json.JSONDecodeError:
        typer.echo("❌ 测试用例 JSON 格式无效")
        raise typer.Exit(1) from None

    result = get_router().route(
        "manage_validation",
        {"action": "add", "requirement_id": requirement_id, "test_cases": cases},
    )
    typer.echo(f"✅ 添加了 {len(result.get('test_cases', []))} 个测试用例")


@validation_app.command("run")
def validation_run(
    requirement_id: Annotated[str, typer.Argument(help="需求 ID")],
) -> None:
    """运行验证"""
    result = get_router().route(
        "manage_validation",
        {"action": "run", "requirement_id": requirement_id},
    )
    passed = result.get("passed", 0)
    failed = result.get("failed", 0)
    typer.echo(f"验证结果: ✅ {passed} 通过, ❌ {failed} 失败")


# ========== 执行管理 ==========

execution_app = typer.Typer(help="执行流程管理")
app.add_typer(execution_app, name="execution")


@execution_app.command("next")
def execution_next(
    project_id: Annotated[str, typer.Option("--project", "-p", help="项目 ID")],
    session_id: Annotated[
        str, typer.Option("--session", "-s", help="会话 ID")
    ] = "default",
) -> None:
    """获取下一个待执行需求"""
    result = get_router().route(
        "manage_execution",
        {"action": "next", "project_id": project_id, "session_id": session_id},
    )
    if result.get("requirement_id"):
        typer.echo(f"下一个需求: {result['requirement_id']}")
        typer.echo(f"内容: {result.get('content', '')[:50]}")
    else:
        typer.echo("所有需求已完成 ✅")


@execution_app.command("complete")
def execution_complete(
    requirement_id: Annotated[str, typer.Argument(help="需求 ID")],
    project_id: Annotated[str, typer.Option("--project", "-p", help="项目 ID")] = "",
    session_id: Annotated[
        str, typer.Option("--session", "-s", help="会话 ID")
    ] = "default",
) -> None:
    """标记需求完成"""
    result = get_router().route(
        "manage_execution",
        {
            "action": "complete",
            "project_id": project_id,
            "requirement_id": requirement_id,
            "session_id": session_id,
        },
    )
    progress = result.get("progress_percentage", 0)
    typer.echo(f"✅ 需求完成，进度: {progress}%")


@execution_app.command("state")
def execution_state(
    project_id: Annotated[str, typer.Option("--project", "-p", help="项目 ID")] = "",
    session_id: Annotated[
        str, typer.Option("--session", "-s", help="会话 ID")
    ] = "default",
) -> None:
    """获取执行状态"""
    result = get_router().route(
        "manage_execution",
        {"action": "state", "project_id": project_id, "session_id": session_id},
    )
    typer.echo(f"总需求: {result.get('total_requirements', 0)}")
    typer.echo(f"已完成: {result.get('completed_requirements', 0)}")
    typer.echo(f"进度: {result.get('progress_percentage', 0)}%")


# ========== 快照管理 ==========

snapshot_app = typer.Typer(help="快照管理")
app.add_typer(snapshot_app, name="snapshot")


@snapshot_app.command("create")
def snapshot_create(
    project_id: Annotated[str, typer.Option("--project", "-p", help="项目 ID")] = "",
    session_id: Annotated[
        str, typer.Option("--session", "-s", help="会话 ID")
    ] = "default",
) -> None:
    """创建快照"""
    result = get_router().route(
        "manage_snapshot",
        {"action": "create", "project_id": project_id, "session_id": session_id},
    )
    typer.echo(f"✅ 快照创建成功: {result.get('snapshot_id', 'N/A')}")


@snapshot_app.command("restore")
def snapshot_restore(
    snapshot_id: Annotated[str, typer.Argument(help="快照 ID")],
    session_id: Annotated[
        str, typer.Option("--session", "-s", help="会话 ID")
    ] = "default",
) -> None:
    """恢复快照"""
    get_router().route(
        "manage_snapshot",
        {"action": "restore", "snapshot_id": snapshot_id, "session_id": session_id},
    )
    typer.echo("✅ 快照恢复成功")


@snapshot_app.command("list")
def snapshot_list(
    project_id: Annotated[str, typer.Option("--project", "-p", help="项目 ID")] = "",
    limit: Annotated[int, typer.Option("--limit", "-l", help="数量限制")] = 10,
) -> None:
    """列出快照"""
    result = get_router().route(
        "manage_snapshot",
        {"action": "list", "project_id": project_id, "limit": limit},
    )
    for snap in result.get("snapshots", []):
        typer.echo(f"{snap['snapshot_id'][:8]}... {snap.get('created_at', 'N/A')}")


# ========== 锁管理 ==========

lock_app = typer.Typer(help="锁管理")
app.add_typer(lock_app, name="lock")


@lock_app.command("acquire")
def lock_acquire(
    project_id: Annotated[str, typer.Option("--project", "-p", help="项目 ID")] = "",
    session_id: Annotated[
        str, typer.Option("--session", "-s", help="会话 ID")
    ] = "default",
) -> None:
    """获取锁"""
    result = get_router().route(
        "manage_lock",
        {"action": "acquire", "project_id": project_id, "session_id": session_id},
    )
    if result.get("acquired"):
        typer.echo("✅ 锁获取成功")
    else:
        typer.echo("❌ 锁获取失败，项目已被锁定")


@lock_app.command("release")
def lock_release(
    project_id: Annotated[str, typer.Option("--project", "-p", help="项目 ID")] = "",
    session_id: Annotated[
        str, typer.Option("--session", "-s", help="会话 ID")
    ] = "default",
) -> None:
    """释放锁"""
    result = get_router().route(
        "manage_lock",
        {"action": "release", "project_id": project_id, "session_id": session_id},
    )
    if result.get("released"):
        typer.echo("✅ 锁释放成功")
    else:
        typer.echo("❌ 锁释放失败")


@lock_app.command("check")
def lock_check(
    project_id: Annotated[str, typer.Option("--project", "-p", help="项目 ID")] = "",
) -> None:
    """检查锁状态"""
    result = get_router().route(
        "manage_lock",
        {"action": "check", "project_id": project_id},
    )
    if result.get("locked"):
        typer.echo(f"🔒 项目已锁定，会话: {result.get('session_id', 'N/A')}")
    else:
        typer.echo("🔓 项目未锁定")


# ========== 版本查询 ==========


@app.command("version")
def version() -> None:
    """显示 API 版本信息"""
    result = get_router().route("get_api_version", {})
    typer.echo(f"当前版本: {result.get('current_version', 'N/A')}")
    typer.echo(f"支持版本: {result.get('supported_versions', [])}")


def entry_point() -> None:
    """CLI 入口点"""
    app()
