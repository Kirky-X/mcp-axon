#!/usr/bin/env python
"""生成需求链化 Mermaid 图 - 包含验证节点和链化顺序"""

import os
import sys

for mod in list(sys.modules):
    if "src." in mod or "real_ladybug" in mod:
        del sys.modules[mod]

DB_PATH = "/tmp/mcp_axon_diagram.lbug"
if os.path.exists(DB_PATH):
    os.remove(DB_PATH)

os.environ["MCP_AXON_DB_PATH"] = DB_PATH
from src.core.containers import init_container  # noqa: E402
from src.core.sdk import RequirementSDK  # noqa: E402

init_container(db_path=DB_PATH)
sdk = RequirementSDK(db_path=DB_PATH)
conn = sdk._get_conn()

from src.db.graph_queries import (  # noqa: E402
    GET_DEPENDENCY_GRAPH,
    GET_REQUIREMENTS_BY_PROJECT,
)

# 创建完整场景
project = sdk.create_project("电商平台V2", "完整电商系统")
pid = project["project_id"]

root = sdk.add_requirement(
    pid,
    "实现一个完整的电商平台系统，包括用户管理、商品管理、订单管理和支付管理",
)
root_id = root["requirement_id"]

modules = []
for name in ["用户管理模块", "商品管理模块", "订单管理模块", "支付管理模块"]:
    m = sdk.add_requirement(pid, name, parent_id=root_id)
    modules.append(m)

user_reqs = []
for item in ["用户注册功能", "用户登录功能", "用户权限控制"]:
    r = sdk.add_requirement(pid, item, parent_id=modules[0]["requirement_id"])
    user_reqs.append(r)
    sdk.requirement_manager.mark_as_leaf(conn, r["requirement_id"])

goods_reqs = []
for item in ["商品信息发布功能", "商品搜索和筛选功能", "商品库存管理功能"]:
    r = sdk.add_requirement(pid, item, parent_id=modules[1]["requirement_id"])
    goods_reqs.append(r)
    sdk.requirement_manager.mark_as_leaf(conn, r["requirement_id"])

order_reqs = []
for item in ["购物车功能", "订单创建和状态管理", "订单查询和物流跟踪"]:
    r = sdk.add_requirement(pid, item, parent_id=modules[2]["requirement_id"])
    order_reqs.append(r)
    sdk.requirement_manager.mark_as_leaf(conn, r["requirement_id"])

pay_reqs = []
for item in ["支付宝和微信支付对接", "支付回调和退款功能"]:
    r = sdk.add_requirement(pid, item, parent_id=modules[3]["requirement_id"])
    pay_reqs.append(r)
    sdk.requirement_manager.mark_as_leaf(conn, r["requirement_id"])

# 依赖关系
sdk.dependency_service.add_dependency(
    conn, goods_reqs[1]["requirement_id"], goods_reqs[0]["requirement_id"]
)
# 用户登录依赖用户注册（语义依赖）
sdk.dependency_service.add_dependency(
    conn, user_reqs[1]["requirement_id"], user_reqs[0]["requirement_id"]
)
sdk.dependency_service.add_dependency(
    conn, order_reqs[1]["requirement_id"], user_reqs[1]["requirement_id"]
)
sdk.dependency_service.add_dependency(
    conn, order_reqs[1]["requirement_id"], order_reqs[0]["requirement_id"]
)
# 支付回调依赖订单创建（语义依赖）
sdk.dependency_service.add_dependency(
    conn, pay_reqs[0]["requirement_id"], order_reqs[1]["requirement_id"]
)
sdk.dependency_service.add_dependency(
    conn, pay_reqs[1]["requirement_id"], order_reqs[1]["requirement_id"]
)

# 依赖传递
sdk.dependency_service.transfer_dependencies(
    conn,
    modules[2]["requirement_id"],
    {
        order_reqs[0]["requirement_id"]: [],
        order_reqs[1]["requirement_id"]: [user_reqs[1]["requirement_id"]],
        order_reqs[2]["requirement_id"]: [order_reqs[1]["requirement_id"]],
    },
)

# 全部验证（同时记录名称以便绘图）
all_leaves = user_reqs + goods_reqs + order_reqs + pay_reqs
validation_names = {}
for r in all_leaves:
    vname = f"{r['content'][:12]}验证"
    validation_names[r["requirement_id"]] = vname
    sdk.add_validation(r["requirement_id"], [{"name": vname}], vname)

# 链化
sdk.trigger_chaining(pid, session_id="diagram")

# 读取数据
reqs = list(conn.execute(GET_REQUIREMENTS_BY_PROJECT, {"project_uuid": pid}))
print(f"节点数: {len(reqs)}")

# 依赖边
dep_edges = []
seen_deps = set()
for row in conn.execute(
    GET_DEPENDENCY_GRAPH, {"project_uuid": pid, "status": "CHAINED"}
):
    if row[1]:
        for dep_id in row[1]:
            edge = (row[0], dep_id)
            if edge not in seen_deps:
                dep_edges.append(edge)
                seen_deps.add(edge)

parent_edges = [(r[2], r[0]) for r in reqs if r[2]]

# 链化顺序
chain_order = {}
for r in reqs:
    if r[8] and r[8] > 0:
        chain_order[r[0]] = r[8]

# 验证节点（使用本地记录，避免解析 JSON）
validations = {
    req_id: name for req_id, name in validation_names.items() if req_id in chain_order
}

# 构建链表执行顺序
chain_list = sorted(chain_order.items(), key=lambda x: x[1])

# 生成 Mermaid
os.makedirs("temp", exist_ok=True)
lines = [
    "# 需求链化结构图",
    "",
    "## 需求树 + 验证节点 + 链化顺序",
    "",
    "```mermaid",
    "graph TD",
    "    classDef root fill:#ff6b6b,stroke:#333,color:#fff,stroke-width:2px",
    "    classDef module fill:#4ecdc4,stroke:#333,color:#fff",
    "    classDef leaf fill:#45b7d1,stroke:#333,color:#fff",
    "    classDef validation fill:#ffa726,stroke:#333,color:#fff",
    "",
]

# 节点定义（含链化顺序标记）
for r in reqs:
    uid = r[0].replace("-", "_")
    label = r[3][:25]
    order = chain_order.get(r[0], 0)
    if order > 0:
        label = f"[{order}] {label}"
    if r[6] == 0:
        cls = "root"
    elif r[0] in {r2[2] for r2 in reqs if r2[2]}:
        cls = "module"
    else:
        cls = "leaf"
    lines.append(f'    {uid}["{label}"]:::{cls}')

# 验证节点
for req_uuid, val_name in validations.items():
    uid = req_uuid.replace("-", "_")
    val_id = f"val_{uid}"
    lines.append(f'    {val_id}["{val_name}"]:::validation')
    lines.append(f"    {uid} --> {val_id}")

lines.append("")
lines.append("    %% 父子关系")
for p, c in parent_edges:
    lines.append(f"    {p.replace('-', '_')} --> {c.replace('-', '_')}")

lines.append("")
lines.append("    %% 依赖关系")
for src, dep in dep_edges:
    lines.append(f"    {src.replace('-', '_')} -. 依赖 .-> {dep.replace('-', '_')}")

lines.append("end")
lines.append("```")
lines.append("")

# 链表执行顺序
lines.append("## 链表执行顺序")
lines.append("")
lines.append("| 顺序 | 需求内容 | 验证状态 |")
lines.append("|------|----------|----------|")
for req_uuid, order in chain_list:
    req = next(r for r in reqs if r[0] == req_uuid)
    has_val = "✓" if req_uuid in validations else ""
    lines.append(f"| {order} | {req[3][:30]} | {has_val} |")

lines.append("")
lines.append(
    f"\n**数据持久化**: `/tmp/mcp_axon_diagram.lbug` ({os.path.getsize(DB_PATH)} 字节)\n"
)

with open("temp/requirement_chain.md", "w") as f:
    f.write("\n".join(lines))

print("文件已生成: temp/requirement_chain.md")
print(f"节点: {len(reqs)}, 验证: {len(validations)}, 链化: {len(chain_order)}")
