#!/usr/bin/env python3
"""
Axon 代码审查 - 自动化测试脚本

用于验证代码审查后修复的正确性
"""

import subprocess
import sys
from pathlib import Path


def run_command(cmd: str, description: str) -> bool:
    """运行命令并返回是否成功"""
    print(f"\n{'=' * 60}")
    print(f"执行: {description}")
    print(f"命令: {cmd}")
    print(f"{'=' * 60}")

    result = subprocess.run(
        cmd,
        shell=True,
        capture_output=True,
        text=True,
        cwd=Path(__file__).parent.parent,
    )

    if result.returncode == 0:
        print(f"✅ {description} - 成功")
        if result.stdout:
            # 只打印最后50行
            lines = result.stdout.strip().split("\n")
            for line in lines[-50:]:
                print(f"  {line}")
        return True
    else:
        print(f"❌ {description} - 失败")
        if result.stderr:
            print(f"错误: {result.stderr[-500:]}")
        return False


def main():
    """主测试流程"""
    print("\n" + "=" * 60)
    print("Axon 代码审查验证测试")
    print("=" * 60)

    tests = [
        # 单元测试
        (
            "python -m pytest tests/test_services/test_requirement_manager.py -v",
            "需求管理器测试",
        ),
        (
            "python -m pytest tests/test_services/test_dependency_service.py -v",
            "依赖服务测试",
        ),
        ("python -m pytest tests/test_utils/test_cache.py -v", "缓存测试"),
        (
            "python -m pytest tests/test_utils/test_input_validator.py -v",
            "输入验证器测试",
        ),
        # 集成测试
        ("python -m pytest tests/test_e2e/ -v --tb=short", "端到端测试"),
        ("python -m pytest tests/edge_cases/ -v --tb=short", "边缘案例测试"),
        # 性能测试
        ("python -m pytest tests/performance/ -v --tb=short", "性能测试"),
    ]

    results = []
    for cmd, description in tests:
        success = run_command(cmd, description)
        results.append((description, success))

    # 打印总结
    print("\n" + "=" * 60)
    print("测试总结")
    print("=" * 60)

    passed = sum(1 for _, success in results if success)
    total = len(results)

    for description, success in results:
        status = "✅ 通过" if success else "❌ 失败"
        print(f"{status} - {description}")

    print(f"\n总计: {passed}/{total} 通过")

    if passed == total:
        print("\n🎉 所有测试通过！修复验证成功！")
        return 0
    else:
        print(f"\n⚠️  {total - passed} 个测试失败，请检查问题")
        return 1


if __name__ == "__main__":
    sys.exit(main())
