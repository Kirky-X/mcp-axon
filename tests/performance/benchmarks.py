"""性能基准测试"""

import time

from src.core.sdk import RequirementSDK


def benchmark_crud_operations():
    """CRUD 操作性能基准"""
    sdk = RequirementSDK(db_path=":memory:")
    project = sdk.create_project("基准测试")
    project_id = project["project_id"]

    # 创建 1000 个需求
    start = time.perf_counter()
    req_ids = []
    for i in range(1000):
        req = sdk.add_requirement(project_id, f"需求{i}")
        req_ids.append(req["requirement_id"])
    create_time = time.perf_counter() - start

    # 查询所有需求
    start = time.perf_counter()
    state = sdk.get_project_state(project_id)
    query_time = time.perf_counter() - start

    # 更新需求
    start = time.perf_counter()
    for req_id in req_ids[:100]:
        sdk.update_requirement(req_id, content=f"更新后的需求{req_id}")
    update_time = time.perf_counter() - start

    # 删除需求
    start = time.perf_counter()
    for req_id in req_ids[:100]:
        sdk.delete_requirement(req_id)
    delete_time = time.perf_counter() - start

    print("\n=== CRUD 操作基准测试 (1000 条记录) ===")
    print(
        f"创建 1000 条: {create_time * 1000:.2f}ms (平均 {create_time * 1000 / 1000:.2f}ms/条)"
    )
    print(f"查询所有记录: {query_time * 1000:.2f}ms")
    print(
        f"更新 100 条: {update_time * 1000:.2f}ms (平均 {update_time * 1000 / 100:.2f}ms/条)"
    )
    print(
        f"删除 100 条: {delete_time * 1000:.2f}ms (平均 {delete_time * 1000 / 100:.2f}ms/条)"
    )

    return {
        "create_avg_ms": create_time * 1000 / 1000,
        "query_total_ms": query_time * 1000,
        "update_avg_ms": update_time * 1000 / 100,
        "delete_avg_ms": delete_time * 1000 / 100,
    }


def benchmark_topological_sort():
    """拓扑排序性能基准"""
    from src.utils.graph import GraphAlgorithms

    # 测试不同规模
    sizes = [100, 500, 1000, 2000]
    results = {}

    print("\n=== 拓扑排序基准测试 ===")
    for size in sizes:
        # 构建图
        graph = {}
        in_degree = {}
        for i in range(size):
            graph[f"node{i}"] = [f"node{i + 1}"] if i < size - 1 else []
            in_degree[f"node{i}"] = 1 if i > 0 else 0

        # 测试性能
        start = time.perf_counter()
        graph_algo = GraphAlgorithms()
        graph_algo.topological_sort(graph, in_degree)
        elapsed = time.perf_counter() - start

        results[size] = elapsed * 1000
        print(f"{size} 节点: {elapsed * 1000:.2f}ms")

    return results


def benchmark_chaining():
    """链化操作性能基准"""
    sdk = RequirementSDK(db_path=":memory:")
    project = sdk.create_project("链化基准测试")
    project_id = project["project_id"]

    # 测试不同规模
    sizes = [100, 500, 1000]
    results = {}

    print("\n=== 链化操作基准测试 ===")
    for size in sizes:
        # 清空数据库
        sdk = RequirementSDK(db_path=":memory:")
        project = sdk.create_project(f"链化测试{size}")
        project_id = project["project_id"]

        # 创建叶子节点
        for i in range(size):
            req = sdk.add_requirement(project_id, f"需求{i}")
            sdk.add_validation(req["requirement_id"], [{"name": f"测试{i}"}])

        # 测试链化性能
        start = time.perf_counter()
        sdk.trigger_chaining(project_id, session_id="benchmark")
        chain_time = time.perf_counter() - start

        # 测试获取下一个需求
        start = time.perf_counter()
        sdk.get_next_requirement(project_id, session_id="benchmark")
        get_next_time = time.perf_counter() - start

        results[size] = {
            "chain_time_ms": chain_time * 1000,
            "get_next_time_ms": get_next_time * 1000,
        }
        print(f"{size} 节点:")
        print(f"  链化: {chain_time * 1000:.2f}ms")
        print(f"  获取下一个: {get_next_time * 1000:.2f}ms")

    return results


def main():
    """运行所有基准测试"""
    print("=" * 60)
    print("性能基准测试")
    print("=" * 60)

    # CRUD 基准
    crud_results = benchmark_crud_operations()

    # 拓扑排序基准
    sort_results = benchmark_topological_sort()

    # 链化基准
    chain_results = benchmark_chaining()

    # 总结
    print("\n=== 性能基准总结 ===")
    print(f"CRUD 创建平均: {crud_results['create_avg_ms']:.2f}ms/条")
    print(f"拓扑排序 (2000节点): {sort_results[2000]:.2f}ms")
    print(f"链化 (1000节点): {chain_results[1000]['chain_time_ms']:.2f}ms")

    # 性能要求检查
    print("\n=== 性能要求检查 ===")
    print(
        f"CRUD < 50ms: {'✅ 通过' if crud_results['create_avg_ms'] < 50 else '❌ 失败'} ({crud_results['create_avg_ms']:.2f}ms)"
    )
    print(
        f"拓扑排序 < 1000ms: {'✅ 通过' if sort_results[2000] < 1000 else '❌ 失败'} ({sort_results[2000]:.2f}ms)"
    )
    print(
        f"链化 < 2000ms: {'✅ 通过' if chain_results[1000]['chain_time_ms'] < 2000 else '❌ 失败'} ({chain_results[1000]['chain_time_ms']:.2f}ms)"
    )


if __name__ == "__main__":
    main()
