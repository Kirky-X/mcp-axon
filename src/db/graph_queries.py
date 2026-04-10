# Copyright (c) 2026 Kirky.X. All rights reserved.
# Licensed under the MIT License.
# See LICENSE file in the project root for full license information.

"""Cypher 查询模板定义"""

# ============ Project 节点查询 ============

CREATE_PROJECT = """
CREATE (p:Project {
    uuid: $uuid,
    name: $name,
    description: $description,
    status: $status,
    locked_by: $locked_by,
    locked_at: $locked_at,
    created_at: $created_at,
    updated_at: $updated_at
})
RETURN p.uuid
"""

GET_PROJECT_BY_UUID = """
MATCH (p:Project {uuid: $uuid})
RETURN p.uuid, p.name, p.description, p.status, p.locked_by, p.locked_at,
       p.created_at, p.updated_at
"""

GET_ALL_PROJECTS = """
MATCH (p:Project)
RETURN p.uuid, p.name, p.description, p.status, p.locked_by, p.locked_at,
       p.created_at, p.updated_at
ORDER BY p.created_at DESC
"""

UPDATE_PROJECT = """
MATCH (p:Project {uuid: $uuid})
SET p.name = $name,
    p.description = $description,
    p.status = $status,
    p.updated_at = $updated_at
"""

UPDATE_PROJECT_STATUS = """
MATCH (p:Project {uuid: $uuid})
SET p.status = $status, p.updated_at = $updated_at
"""

UPDATE_PROJECT_LOCK = """
MATCH (p:Project {uuid: $uuid})
SET p.locked_by = $locked_by, p.locked_at = $locked_at, p.updated_at = $updated_at
"""

DELETE_PROJECT = """
MATCH (p:Project {uuid: $uuid})
DETACH DELETE p
"""

# ============ Requirement 节点查询 ============

CREATE_REQUIREMENT = """
CREATE (r:Requirement {
    uuid: $uuid,
    project_uuid: $project_uuid,
    parent_uuid: $parent_uuid,
    content: $content,
    decompose_reason: $decompose_reason,
    status: $status,
    level: $level,
    order_in_parent: $order_in_parent,
    chain_order: $chain_order,
    created_at: $created_at,
    updated_at: $updated_at,
    version: $version
})
RETURN r.uuid
"""

GET_REQUIREMENT_BY_UUID = """
MATCH (r:Requirement {uuid: $uuid})
OPTIONAL MATCH (r)-[:DEPENDS_ON]->(dep:Requirement)
OPTIONAL MATCH (r)-[:NEXT_IN_CHAIN]->(next:Requirement)
RETURN r.uuid, r.project_uuid, r.parent_uuid, r.content, r.decompose_reason,
       r.status, r.level, r.order_in_parent, r.chain_order,
       r.created_at, r.updated_at, r.version,
       collect(dep.uuid) as dependencies,
       next.uuid as next_requirement_uuid
"""

GET_REQUIREMENTS_BY_PROJECT = """
MATCH (r:Requirement {project_uuid: $project_uuid})
OPTIONAL MATCH (r)-[:DEPENDS_ON]->(dep:Requirement)
RETURN r.uuid, r.project_uuid, r.parent_uuid, r.content, r.decompose_reason,
       r.status, r.level, r.order_in_parent, r.chain_order,
       r.created_at, r.updated_at, r.version,
       collect(dep.uuid) as dependencies
ORDER BY r.created_at ASC
"""

GET_REQUIREMENTS_BY_STATUS = """
MATCH (r:Requirement {project_uuid: $project_uuid, status: $status})
OPTIONAL MATCH (r)-[:DEPENDS_ON]->(dep:Requirement)
RETURN r.uuid, r.project_uuid, r.parent_uuid, r.content, r.decompose_reason,
       r.status, r.level, r.order_in_parent, r.chain_order,
       r.created_at, r.updated_at, r.version,
       collect(dep.uuid) as dependencies
ORDER BY r.created_at ASC
"""

GET_REQUIREMENTS_BY_PARENT = """
MATCH (r:Requirement {parent_uuid: $parent_uuid})
OPTIONAL MATCH (r)-[:DEPENDS_ON]->(dep:Requirement)
RETURN r.uuid, r.project_uuid, r.parent_uuid, r.content, r.decompose_reason,
       r.status, r.level, r.order_in_parent, r.chain_order,
       r.created_at, r.updated_at, r.version,
       collect(dep.uuid) as dependencies
ORDER BY r.order_in_parent ASC
"""

GET_ROOT_REQUIREMENTS = """
MATCH (r:Requirement {project_uuid: $project_uuid, parent_uuid: ''})
OPTIONAL MATCH (r)-[:DEPENDS_ON]->(dep:Requirement)
RETURN r.uuid, r.project_uuid, r.parent_uuid, r.content, r.decompose_reason,
       r.status, r.level, r.order_in_parent, r.chain_order,
       r.created_at, r.updated_at, r.version,
       collect(dep.uuid) as dependencies
ORDER BY r.order_in_parent ASC
"""

UPDATE_REQUIREMENT = """
MATCH (r:Requirement {uuid: $uuid})
SET r.content = $content,
    r.decompose_reason = $decompose_reason,
    r.status = $status,
    r.updated_at = $updated_at,
    r.version = r.version + 1
"""

UPDATE_REQUIREMENT_STATUS = """
MATCH (r:Requirement {uuid: $uuid})
SET r.status = $status, r.updated_at = $updated_at
"""

UPDATE_REQUIREMENT_CHAIN_ORDER = """
MATCH (r:Requirement {uuid: $uuid})
SET r.chain_order = $chain_order, r.status = $status, r.updated_at = $updated_at
"""

DELETE_REQUIREMENT = """
MATCH (r:Requirement {uuid: $uuid})
DETACH DELETE r
"""

# ============ ValidationNode 节点查询 ============

CREATE_VALIDATION = """
CREATE (v:ValidationNode {
    uuid: $uuid,
    requirement_uuid: $requirement_uuid,
    test_cases: $test_cases,
    acceptance_criteria: $acceptance_criteria,
    status: $status,
    result: $result,
    validated_at: $validated_at,
    created_at: $created_at
})
RETURN v.uuid
"""

GET_VALIDATION_BY_UUID = """
MATCH (v:ValidationNode {uuid: $uuid})
RETURN v.uuid, v.requirement_uuid, v.test_cases, v.acceptance_criteria,
       v.status, v.result, v.validated_at, v.created_at
"""

GET_VALIDATION_BY_REQUIREMENT = """
MATCH (v:ValidationNode {requirement_uuid: $requirement_uuid})
RETURN v.uuid, v.requirement_uuid, v.test_cases, v.acceptance_criteria,
       v.status, v.result, v.validated_at, v.created_at
"""

UPDATE_VALIDATION = """
MATCH (v:ValidationNode {uuid: $uuid})
SET v.test_cases = $test_cases,
    v.acceptance_criteria = $acceptance_criteria,
    v.status = $status,
    v.result = $result,
    v.validated_at = $validated_at
"""

DELETE_VALIDATION = """
MATCH (v:ValidationNode {uuid: $uuid})
DETACH DELETE v
"""

DELETE_VALIDATION_BY_REQUIREMENT = """
MATCH (v:ValidationNode {requirement_uuid: $requirement_uuid})
DETACH DELETE v
"""

# ============ ChainState 节点查询 ============

CREATE_CHAIN_STATE = """
CREATE (cs:ChainState {
    uuid: $uuid,
    project_uuid: $project_uuid,
    status: $status,
    chain_head_uuid: $chain_head_uuid,
    current_node_uuid: $current_node_uuid,
    total_nodes: $total_nodes,
    completed_nodes: $completed_nodes,
    progress_percentage: $progress_percentage,
    last_chained_at: $last_chained_at,
    chain_version: $chain_version,
    created_at: $created_at,
    updated_at: $updated_at
})
RETURN cs.uuid
"""

GET_CHAIN_STATE_BY_PROJECT = """
MATCH (cs:ChainState {project_uuid: $project_uuid})
RETURN cs.uuid, cs.project_uuid, cs.status, cs.chain_head_uuid, cs.current_node_uuid,
       cs.total_nodes, cs.completed_nodes, cs.progress_percentage,
       cs.last_chained_at, cs.chain_version, cs.created_at, cs.updated_at
"""

UPDATE_CHAIN_STATE = """
MATCH (cs:ChainState {uuid: $uuid})
SET cs.status = $status,
    cs.chain_head_uuid = $chain_head_uuid,
    cs.current_node_uuid = $current_node_uuid,
    cs.total_nodes = $total_nodes,
    cs.completed_nodes = $completed_nodes,
    cs.progress_percentage = $progress_percentage,
    cs.last_chained_at = $last_chained_at,
    cs.chain_version = cs.chain_version + 1,
    cs.updated_at = $updated_at
"""

UPDATE_CHAIN_STATE_PROGRESS = """
MATCH (cs:ChainState {uuid: $uuid})
SET cs.current_node_uuid = $current_node_uuid,
    cs.completed_nodes = cs.completed_nodes + 1,
    cs.progress_percentage = $progress_percentage,
    cs.updated_at = $updated_at
"""

RESET_CHAIN_STATE = """
MATCH (cs:ChainState {project_uuid: $project_uuid})
SET cs.status = 'IDLE',
    cs.chain_head_uuid = '',
    cs.current_node_uuid = '',
    cs.total_nodes = 0,
    cs.completed_nodes = 0,
    cs.progress_percentage = 0,
    cs.updated_at = $updated_at
"""

DELETE_CHAIN_STATE = """
MATCH (cs:ChainState {uuid: $uuid})
DETACH DELETE cs
"""

# ============ Event 节点查询 ============

CREATE_EVENT = """
CREATE (e:Event {
    uuid: $uuid,
    project_uuid: $project_uuid,
    event_type: $event_type,
    aggregate_uuid: $aggregate_uuid,
    payload: $payload,
    event_metadata: $event_metadata,
    sequence: $sequence,
    created_at: $created_at
})
RETURN e.uuid
"""

GET_EVENTS_BY_PROJECT = """
MATCH (e:Event {project_uuid: $project_uuid})
RETURN e.uuid, e.project_uuid, e.event_type, e.aggregate_uuid, e.payload,
       e.event_metadata, e.sequence, e.created_at
ORDER BY e.sequence ASC
LIMIT $limit
"""

GET_LATEST_EVENT_SEQUENCE = """
MATCH (e:Event {project_uuid: $project_uuid})
RETURN max(e.sequence) as max_sequence
"""

GET_EVENT_BY_UUID = """
MATCH (e:Event {uuid: $uuid})
RETURN e.uuid, e.project_uuid, e.event_type, e.aggregate_uuid, e.payload,
       e.event_metadata, e.sequence, e.created_at
"""

GET_EVENTS_BY_PROJECT_AND_TYPE = """
MATCH (e:Event {project_uuid: $project_uuid, event_type: $event_type})
RETURN e.uuid, e.project_uuid, e.event_type, e.aggregate_uuid, e.payload,
       e.event_metadata, e.sequence, e.created_at
ORDER BY e.created_at DESC
LIMIT $limit
"""

GET_EVENTS_BY_TIME_RANGE = """
MATCH (e:Event {project_uuid: $project_uuid})
WHERE e.created_at >= $start_time AND e.created_at <= $end_time
RETURN e.uuid, e.project_uuid, e.event_type, e.aggregate_uuid, e.payload,
       e.event_metadata, e.sequence, e.created_at
ORDER BY e.created_at ASC
"""

GET_EVENTS_BY_TYPE_TIME_RANGE = """
MATCH (e:Event {project_uuid: $project_uuid})
WHERE e.event_type = $event_type AND e.created_at >= $start_time
RETURN e.uuid, e.project_uuid, e.event_type, e.aggregate_uuid, e.payload,
       e.event_metadata, e.sequence, e.created_at
ORDER BY e.created_at ASC
"""

DELETE_EVENT = """
MATCH (e:Event {uuid: $uuid})
DETACH DELETE e
"""

# ============ 关系查询 ============

# HAS_REQUIREMENT 关系
CREATE_HAS_REQUIREMENT = """
MATCH (p:Project {uuid: $project_uuid})
MATCH (r:Requirement {uuid: $requirement_uuid})
CREATE (p)-[:HAS_REQUIREMENT]->(r)
"""

# HAS_CHILD 关系
CREATE_HAS_CHILD = """
MATCH (parent:Requirement {uuid: $parent_uuid})
MATCH (child:Requirement {uuid: $child_uuid})
CREATE (parent)-[:HAS_CHILD]->(child)
"""

GET_CHILDREN = """
MATCH (parent:Requirement {uuid: $parent_uuid})-[:HAS_CHILD]->(child:Requirement)
RETURN child.uuid
ORDER BY child.order_in_parent ASC
"""

# HAS_VALIDATION 关系
CREATE_HAS_VALIDATION = """
MATCH (r:Requirement {uuid: $requirement_uuid})
MATCH (v:ValidationNode {uuid: $validation_uuid})
CREATE (r)-[:HAS_VALIDATION]->(v)
"""

# DEPENDS_ON 关系
CREATE_DEPENDS_ON = """
MATCH (r1:Requirement {uuid: $requirement_uuid})
MATCH (r2:Requirement {uuid: $dependency_uuid})
CREATE (r1)-[:DEPENDS_ON]->(r2)
"""

DELETE_DEPENDS_ON = """
MATCH (r1:Requirement {uuid: $requirement_uuid})-[e:DEPENDS_ON]->(r2:Requirement {uuid: $dependency_uuid})
DELETE e
"""

GET_DEPENDENCIES = """
MATCH (r:Requirement {uuid: $requirement_uuid})-[:DEPENDS_ON]->(dep:Requirement)
RETURN dep.uuid
"""

GET_DEPENDENTS = """
MATCH (r:Requirement {uuid: $requirement_uuid})<-[:DEPENDS_ON]-(dependent:Requirement)
RETURN dependent.uuid
"""

# NEXT_IN_CHAIN 关系
CREATE_NEXT_IN_CHAIN = """
MATCH (r1:Requirement {uuid: $from_uuid})
MATCH (r2:Requirement {uuid: $to_uuid})
CREATE (r1)-[:NEXT_IN_CHAIN]->(r2)
"""

DELETE_ALL_NEXT_IN_CHAIN = """
MATCH (r:Requirement {project_uuid: $project_uuid})-[e:NEXT_IN_CHAIN]->()
DELETE e
"""

GET_NEXT_IN_CHAIN = """
MATCH (r:Requirement {uuid: $uuid})-[:NEXT_IN_CHAIN]->(next:Requirement)
RETURN next.uuid
"""

GET_CHAIN_HEAD = """
MATCH (cs:ChainState {project_uuid: $project_uuid})
RETURN cs.chain_head_uuid
"""

# HAS_CHAIN_STATE 关系
CREATE_HAS_CHAIN_STATE = """
MATCH (p:Project {uuid: $project_uuid})
MATCH (cs:ChainState {uuid: $chain_state_uuid})
CREATE (p)-[:HAS_CHAIN_STATE]->(cs)
"""

# HAS_EVENT 关系
CREATE_HAS_EVENT = """
MATCH (p:Project {uuid: $project_uuid})
MATCH (e:Event {uuid: $event_uuid})
CREATE (p)-[:HAS_EVENT]->(e)
"""

# ============ 图算法查询 ============

# 环路检测（添加依赖前预检查）
CHECK_WOULD_CREATE_CYCLE = """
MATCH path = (dep:Requirement {uuid: $dependency_uuid})
             -[:DEPENDS_ON*0..30]->(req:Requirement {uuid: $requirement_uuid})
RETURN path
LIMIT 1
"""

# 项目级环路检测 (LadybugDB 不支持 nodes() 函数和列表推导)
DETECT_CYCLE_IN_PROJECT = """
MATCH path = (r:Requirement {project_uuid: $project_uuid})
             -[:DEPENDS_ON*1..30]->(r)
RETURN r.uuid as cycle_start
LIMIT 1
"""

# 获取依赖图（用于拓扑排序）
GET_DEPENDENCY_GRAPH = """
MATCH (r:Requirement {project_uuid: $project_uuid, status: $status})
OPTIONAL MATCH (r)-[:DEPENDS_ON]->(dep:Requirement)
RETURN r.uuid as node_id, collect(dep.uuid) as dependencies
"""

# 获取反向依赖图（依赖 -> 被依赖）
GET_REVERSE_DEPENDENCY_GRAPH = """
MATCH (r:Requirement {project_uuid: $project_uuid, status: $status})
OPTIONAL MATCH (dep)-[:DEPENDS_ON]->(r)
RETURN r.uuid as node_id, collect(dep.uuid) as dependents
"""

# 链遍历
GET_CHAIN_NODES = """
MATCH (head:Requirement {uuid: $chain_head_uuid})
MATCH path = (head)-[:NEXT_IN_CHAIN*0..]->(node:Requirement)
RETURN node.uuid, node.chain_order
ORDER BY node.chain_order ASC
"""

# 批量重置链化状态
RESET_ALL_CHAIN_ORDERS = """
MATCH (r:Requirement {project_uuid: $project_uuid})
SET r.chain_order = NULL, r.status = 'VALIDATED', r.updated_at = $updated_at
"""

# ============ 统计查询 ============

COUNT_REQUIREMENTS_BY_STATUS = """
MATCH (r:Requirement {project_uuid: $project_uuid})
RETURN r.status as status, count(r) as count
"""

COUNT_ALL_REQUIREMENTS = """
MATCH (r:Requirement {project_uuid: $project_uuid})
RETURN count(r) as total
"""

COUNT_LEAF_REQUIREMENTS = """
MATCH (r:Requirement {project_uuid: $project_uuid})
WHERE NOT EXISTS { MATCH (r)-[:HAS_CHILD]->() }
RETURN count(r) as leaf_count
"""

# ============ 删除前检查查询 ============

# 检查入边依赖详情（返回依赖者信息）
GET_INCOMING_DEPENDENCIES_DETAILS = """
MATCH (r:Requirement {uuid: $requirement_uuid})<-[:DEPENDS_ON]-(dep:Requirement)
RETURN dep.uuid as uuid, dep.content as content, dep.status as status
"""

# 检查需求是否在执行链中
GET_CHAIN_POSITION = """
MATCH (cs:ChainState {project_uuid: $project_uuid})
WHERE cs.current_node_uuid = $requirement_uuid OR EXISTS {
    MATCH (head:Requirement {uuid: cs.chain_head_uuid})
    MATCH path = (head)-[:NEXT_IN_CHAIN*]->(r:Requirement {uuid: $requirement_uuid})
    RETURN path
}
RETURN cs.current_node_uuid as current_uuid, cs.status as chain_status
"""

# 检查需求的 chain_order 和是否被 NEXT_IN_CHAIN 引用
GET_REQUIREMENT_CHAIN_INFO = """
MATCH (r:Requirement {uuid: $requirement_uuid})
OPTIONAL MATCH (prev:Requirement)-[:NEXT_IN_CHAIN]->(r)
OPTIONAL MATCH (r)-[:NEXT_IN_CHAIN]->(next:Requirement)
RETURN r.chain_order as chain_order,
       prev.uuid as prev_uuid,
       next.uuid as next_uuid,
       prev.content as prev_content,
       next.content as next_content
"""

# ============ 快照相关查询 ============

SNAPSHOT_LIST_QUERY = """
MATCH (e:Event {project_uuid: $project_uuid, event_type: $event_type})
RETURN e.uuid, e.created_at, e.sequence
ORDER BY e.created_at DESC
LIMIT $limit
"""

SNAPSHOT_DELETE_REQUIREMENT = """
MATCH (r:Requirement {uuid: $uuid}) DETACH DELETE r
"""

SNAPSHOT_CHECK_REQUIREMENT_EXISTS = """
MATCH (r:Requirement {uuid: $uuid}) RETURN r.uuid
"""

SNAPSHOT_UPDATE_REQUIREMENT = """
MATCH (r:Requirement {uuid: $uuid})
SET r.status = $status,
    r.chain_order = $chain_order,
    r.updated_at = $updated_at
"""

SNAPSHOT_CLEAR_DEPENDENCIES = """
MATCH (r:Requirement {uuid: $uuid})-[e:DEPENDS_ON]->() DELETE e
"""

SNAPSHOT_ADD_DEPENDENCY = """
MATCH (r1:Requirement {uuid: $req_uuid})
MATCH (r2:Requirement {uuid: $dep_uuid})
CREATE (r1)-[:DEPENDS_ON]->(r2)
"""

SNAPSHOT_CLEAR_NEXT_IN_CHAIN = """
MATCH (r:Requirement {uuid: $uuid})-[e:NEXT_IN_CHAIN]->() DELETE e
"""

SNAPSHOT_SET_NEXT_IN_CHAIN = """
MATCH (r1:Requirement {uuid: $from_uuid})
MATCH (r2:Requirement {uuid: $to_uuid})
CREATE (r1)-[:NEXT_IN_CHAIN]->(r2)
"""

SNAPSHOT_UPDATE_CHAIN_STATE = """
MATCH (cs:ChainState {project_uuid: $project_uuid})
SET cs.status = $status,
    cs.chain_head_uuid = $chain_head_uuid,
    cs.current_node_uuid = $current_node_uuid,
    cs.total_nodes = $total_nodes,
    cs.completed_nodes = $completed_nodes,
    cs.progress_percentage = $progress_percentage,
    cs.chain_version = cs.chain_version + 1,
    cs.updated_at = $updated_at
"""

SNAPSHOT_CREATE_HAS_EVENT = """
MATCH (p:Project {uuid: $project_uuid})
MATCH (e:Event {uuid: $event_uuid})
CREATE (p)-[:HAS_EVENT]->(e)
"""
