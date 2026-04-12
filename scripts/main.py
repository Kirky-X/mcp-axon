# Copyright (c) 2026 Kirky.X. All rights reserved.
# Licensed under the MIT License.
# See LICENSE file in the project root for full license information.

"""Axon 主入口"""

import argparse
import asyncio
import logging
import sys

from src.api.mcp_server import main as server_main
from src.core.containers import close_database, init_container, init_database
from src.core.sdk import RequirementSDK

# 配置日志
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def init_db(db_path: str = "mcp_axon.lbug"):
    """初始化数据库"""

    logger.info(f"初始化数据库: {db_path}")

    # 初始化容器和数据库
    init_container(db_path=db_path)
    init_database()

    logger.info("数据库初始化完成")


def run_server(db_path: str = "mcp_axon.lbug"):
    """运行 MCP 服务器"""
    logger.info("启动 MCP 服务器...")

    # 运行服务器
    asyncio.run(server_main())


def run_tests():
    """运行测试"""
    import subprocess
    from pathlib import Path

    logger.info("运行测试...")
    # 获取项目根目录 (scripts/ 的父目录)
    project_root = Path(__file__).parent.parent
    result = subprocess.run(
        ["pytest", "tests/", "-v", "--cov=src", "--cov-report=term-missing"],
        cwd=str(project_root),
    )

    sys.exit(result.returncode)


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="Axon - 需求链化管理系统")

    parser.add_argument(
        "command", choices=["init", "server", "test", "demo"], help="命令"
    )

    parser.add_argument("--db-path", default="mcp_axon.lbug", help="数据库文件路径")

    args = parser.parse_args()

    if args.command == "init":
        init_db(args.db_path)

    elif args.command == "server":
        # 先初始化数据库
        init_db(args.db_path)
        # 运行服务器
        run_server(args.db_path)

    elif args.command == "test":
        run_tests()

    elif args.command == "demo":
        # 运行演示
        run_demo(args.db_path)


def run_demo(db_path: str):
    """运行演示"""
    logger.info("运行演示...")

    # 初始化数据库
    init_db(db_path)

    # 创建 SDK
    sdk = RequirementSDK(db_path)

    # 1. 创建项目
    print("\n=== 1. 创建项目 ===")
    project = sdk.create_project(name="演示项目", description="这是一个演示项目")
    print(f"项目创建成功: {project['project_id']}")
    print(f"项目名称: {project['name']}")
    print(f"下一步: {project['next_action']}")

    # 2. 添加根需求
    print("\n=== 2. 添加根需求 ===")
    root_req = sdk.add_requirement(
        project_id=project["project_id"], content="实现用户管理系统"
    )
    print(f"需求添加成功: {root_req['requirement_id']}")
    print(f"复杂度分数: {root_req['complexity_score']}")
    print(f"需要分解: {root_req['needs_decomposition']}")
    print(f"分解提示: {root_req['decompose_hints']}")

    # 3. 分解为子需求
    print("\n=== 3. 分解为子需求 ===")
    child1 = sdk.add_requirement(
        project_id=project["project_id"],
        content="用户注册功能",
        parent_id=root_req["requirement_id"],
    )
    print(f"子需求1: {child1['requirement_id']}")

    child2 = sdk.add_requirement(
        project_id=project["project_id"],
        content="用户登录功能",
        parent_id=root_req["requirement_id"],
    )
    print(f"子需求2: {child2['requirement_id']}")

    # 4. 标记为叶子节点
    print("\n=== 4. 标记为叶子节点 ===")
    sdk.mark_as_leaf(child1["requirement_id"])
    sdk.mark_as_leaf(child2["requirement_id"])
    print("已标记为叶子节点")

    # 5. 添加验证
    print("\n=== 5. 添加验证 ===")
    sdk.add_validation(
        requirement_id=child1["requirement_id"],
        test_cases=[
            {
                "name": "测试用户注册",
                "steps": ["输入用户名", "输入密码", "点击注册"],
                "expected_result": "注册成功",
            }
        ],
    )
    print("子需求1验证添加成功")

    sdk.add_validation(
        requirement_id=child2["requirement_id"],
        test_cases=[
            {
                "name": "测试用户登录",
                "steps": ["输入用户名", "输入密码", "点击登录"],
                "expected_result": "登录成功",
            }
        ],
    )
    print("子需求2验证添加成功")

    # 6. 触发链化
    print("\n=== 6. 触发链化 ===")
    chain_result = sdk.trigger_chaining(project["project_id"])
    print(f"链化状态: {chain_result['status']}")
    if chain_result["status"] == "completed":
        print(f"链表头节点: {chain_result['chain_head']}")
        print(f"总节点数: {chain_result['total_nodes']}")

    # 7. 获取项目状态
    print("\n=== 7. 项目状态 ===")
    state = sdk.get_project_state(project["project_id"])
    print(f"项目状态: {state['status']}")
    print(f"总需求数: {state['total_requirements']}")
    print(f"叶子需求数: {state['leaf_requirements']}")
    print(f"已验证需求数: {state['validated_requirements']}")
    print(f"已链化需求数: {state['chained_requirements']}")
    print(f"链化进度: {state['progress_percentage']}%")

    # 8. 获取下一个需求
    print("\n=== 8. 获取下一个需求 ===")
    next_req = sdk.get_next_requirement(project["project_id"])
    print(f"下一个需求: {next_req['requirement_id']}")
    print(f"需求内容: {next_req['content']}")
    print(f"是否最后: {next_req['is_last']}")

    print("\n=== 演示完成 ===")

    # 清理
    close_database()


if __name__ == "__main__":
    main()
