# Copyright (c) 2026 Kirky.X. All rights reserved.
# Licensed under the MIT License.
# See LICENSE file in the project root for full license information.

"""输入验证器测试"""

import pytest

from src.utils.input_validator import InputValidator, SecurityChecker


# ========== InputValidator.validate_project_name ==========


def test_validate_project_name_valid():
    """测试: 有效项目名称通过验证"""
    # Arrange & Act
    result = InputValidator.validate_project_name("我的测试项目")

    # Assert
    assert result == "我的测试项目"


def test_validate_project_name_with_english():
    """测试: 英文项目名称通过验证"""
    result = InputValidator.validate_project_name("My Test Project")
    assert result == "My Test Project"


def test_validate_project_name_with_mixed():
    """测试: 中英文混合项目名称通过验证"""
    result = InputValidator.validate_project_name("项目 Project 2024")
    assert result == "项目 Project 2024"


def test_validate_project_name_with_common_punctuation():
    """测试: 常用标点符号通过验证"""
    result = InputValidator.validate_project_name("项目-名称_v1.0")
    assert result == "项目-名称_v1.0"


def test_validate_project_name_empty_string():
    """测试: 空字符串被拒绝"""
    with pytest.raises(ValueError, match="项目名称不能为空"):
        InputValidator.validate_project_name("")


def test_validate_project_name_whitespace_only():
    """测试: 仅空白字符被拒绝"""
    with pytest.raises(ValueError, match="项目名称不能为空"):
        InputValidator.validate_project_name("   ")


def test_validate_project_name_none():
    """测试: None 被拒绝"""
    with pytest.raises(ValueError, match="项目名称不能为空"):
        InputValidator.validate_project_name(None)


def test_validate_project_name_non_string():
    """测试: 非字符串类型被拒绝"""
    with pytest.raises(ValueError, match="项目名称不能为空"):
        InputValidator.validate_project_name(123)


def test_validate_project_name_too_long():
    """测试: 超长项目名称被拒绝"""
    long_name = "A" * 201
    with pytest.raises(ValueError, match="项目名称长度不能超过 200 字符"):
        InputValidator.validate_project_name(long_name)


def test_validate_project_name_with_xss_script():
    """测试: XSS 脚本标签被拒绝"""
    with pytest.raises(ValueError, match="包含不安全的内容"):
        InputValidator.validate_project_name("<script>alert('xss')</script>")


def test_validate_project_name_with_xss_javascript():
    """测试: JavaScript 伪协议被拒绝"""
    with pytest.raises(ValueError, match="包含不安全的内容"):
        InputValidator.validate_project_name("javascript:alert('xss')")


def test_validate_project_name_with_xss_event_handler():
    """测试: 事件处理器被拒绝"""
    with pytest.raises(ValueError, match="包含不安全的内容"):
        InputValidator.validate_project_name("test onclick=alert(1)")


def test_validate_project_name_with_xss_eval():
    """测试: eval 函数被拒绝"""
    with pytest.raises(ValueError, match="包含不安全的内容"):
        InputValidator.validate_project_name("test eval(恶意代码)")


def test_validate_project_name_with_xss_document():
    """测试: document 访问被拒绝"""
    with pytest.raises(ValueError, match="包含不安全的内容"):
        InputValidator.validate_project_name("test document.cookie")


def test_validate_project_name_with_xss_window():
    """测试: window 对象被拒绝"""
    with pytest.raises(ValueError, match="包含不安全的内容"):
        InputValidator.validate_project_name("test window.location")


def test_validate_project_name_with_xss_alert():
    """测试: alert 函数被拒绝"""
    with pytest.raises(ValueError, match="包含不安全的内容"):
        InputValidator.validate_project_name("test alert(1)")


def test_validate_project_name_with_xss_img_onerror():
    """测试: img onerror 事件被拒绝"""
    with pytest.raises(ValueError, match="包含不安全的内容"):
        InputValidator.validate_project_name("<img src=x onerror=alert(1)>")


def test_validate_project_name_strips_whitespace():
    """测试: 前后空白被去除"""
    result = InputValidator.validate_project_name("  测试项目  ")
    assert result == "测试项目"


def test_validate_project_name_exactly_max_length():
    """测试: 刚好 200 字符通过"""
    name_200 = "A" * 200
    result = InputValidator.validate_project_name(name_200)
    assert result == name_200


# ========== InputValidator.validate_requirement_content ==========


def test_validate_requirement_content_valid():
    """测试: 有效需求内容通过验证"""
    result = InputValidator.validate_requirement_content("实现用户登录功能")
    assert result == "实现用户登录功能"


def test_validate_requirement_content_empty():
    """测试: 空需求内容被拒绝"""
    with pytest.raises(ValueError, match="需求内容不能为空"):
        InputValidator.validate_requirement_content("")


def test_validate_requirement_content_whitespace_only():
    """测试: 仅空白被拒绝"""
    with pytest.raises(ValueError, match="需求内容不能为空"):
        InputValidator.validate_requirement_content("   ")


def test_validate_requirement_content_none():
    """测试: None 被拒绝"""
    with pytest.raises(ValueError, match="需求内容不能为空"):
        InputValidator.validate_requirement_content(None)


def test_validate_requirement_content_too_long():
    """测试: 超长需求内容被拒绝"""
    long_content = "A" * 5001
    with pytest.raises(ValueError, match="需求内容长度不能超过 5000 字符"):
        InputValidator.validate_requirement_content(long_content)


def test_validate_requirement_content_with_sql_drop():
    """测试: SQL DROP TABLE 注入被拒绝"""
    with pytest.raises(ValueError, match="包含不安全的内容"):
        InputValidator.validate_requirement_content("test; DROP TABLE requirements--")


def test_validate_requirement_content_with_sql_union():
    """测试: SQL UNION 注入被拒绝"""
    with pytest.raises(ValueError, match="包含不安全的内容"):
        InputValidator.validate_requirement_content("test' UNION SELECT * FROM users--")


def test_validate_requirement_content_with_sql_or():
    """测试: SQL OR 盲注被拒绝"""
    with pytest.raises(ValueError, match="包含不安全的内容"):
        InputValidator.validate_requirement_content("test' OR 1=1--")


def test_validate_requirement_content_with_sql_xor():
    """测试: SQL XOR 盲注被拒绝"""
    with pytest.raises(ValueError, match="包含不安全的内容"):
        InputValidator.validate_requirement_content("test' XOR 1=1--")


def test_validate_requirement_content_with_sql_comment():
    """测试: SQL 注释被拒绝"""
    with pytest.raises(ValueError, match="包含不安全的内容"):
        InputValidator.validate_requirement_content("test--comment")


def test_validate_requirement_content_with_multistatement():
    """测试: 多语句注入被拒绝"""
    with pytest.raises(ValueError, match="包含不安全的内容"):
        InputValidator.validate_requirement_content("test'; DELETE FROM users--")


def test_validate_requirement_content_strips_whitespace():
    """测试: 前后空白被去除"""
    result = InputValidator.validate_requirement_content("  需求内容  ")
    assert result == "需求内容"


def test_validate_requirement_content_exactly_max_length():
    """测试: 刚好 5000 字符通过"""
    content_5000 = "A" * 5000
    result = InputValidator.validate_requirement_content(content_5000)
    assert result == content_5000


# ========== InputValidator.validate_description ==========


def test_validate_description_valid():
    """测试: 有效描述通过验证"""
    result = InputValidator.validate_description("这是一个测试描述")
    assert result == "这是一个测试描述"


def test_validate_description_none_accepted():
    """测试: None 描述被接受"""
    result = InputValidator.validate_description(None)
    assert result is None


def test_validate_description_empty_string_returns_none():
    """测试: 空字符串返回 None"""
    result = InputValidator.validate_description("   ")
    assert result is None


def test_validate_description_non_string():
    """测试: 非字符串类型被拒绝"""
    with pytest.raises(ValueError, match="描述必须是字符串"):
        InputValidator.validate_description(123)


def test_validate_description_too_long():
    """测试: 超长描述被拒绝"""
    long_desc = "A" * 5001
    with pytest.raises(ValueError, match="描述长度不能超过 5000 字符"):
        InputValidator.validate_description(long_desc)


def test_validate_description_with_xss():
    """测试: 描述中的 XSS 不被清理（描述字段不检查危险模式）"""
    # validate_description 不检查 XSS，直接返回 strip 后的字符串
    # 这与 validate_project_name 和 validate_requirement_content 不同
    result = InputValidator.validate_description("描述 <script>alert(1)</script>")
    assert result == "描述 <script>alert(1)</script>"


def test_validate_description_strips_whitespace():
    """测试: 前后空白被去除"""
    result = InputValidator.validate_description("  描述  ")
    assert result == "描述"


# ========== InputValidator.validate_test_cases ==========


def test_validate_test_cases_valid():
    """测试: 有效测试用例通过验证"""
    test_cases = [
        {"name": "测试1", "steps": ["步骤1"], "expected_result": "结果1"},
        {"name": "测试2", "steps": ["步骤2"], "expected_result": "结果2"},
    ]
    result = InputValidator.validate_test_cases(test_cases)
    assert len(result) == 2
    assert result[0]["name"] == "测试1"


def test_validate_test_cases_empty_list():
    """测试: 空测试用例列表被接受"""
    result = InputValidator.validate_test_cases([])
    assert result == []


def test_validate_test_cases_not_list():
    """测试: 非列表类型被拒绝"""
    with pytest.raises(ValueError, match="测试用例必须是数组"):
        InputValidator.validate_test_cases("not a list")


def test_validate_test_case_not_dict():
    """测试: 非字典测试用例被拒绝"""
    with pytest.raises(ValueError, match="测试用例 0 必须是字典"):
        InputValidator.validate_test_cases(["not a dict"])


def test_validate_test_case_name_missing():
    """测试: 缺少 name 字段被拒绝"""
    test_cases = [{"steps": ["步骤1"]}]
    # name 字段为空字符串
    with pytest.raises(ValueError, match="测试用例 0 的 name 不能为空"):
        InputValidator.validate_test_cases(test_cases)


def test_validate_test_case_name_not_string():
    """测试: 非字符串 name 被拒绝"""
    test_cases = [{"name": 123, "steps": ["步骤1"]}]
    with pytest.raises(ValueError, match="测试用例 0 的 name 必须是字符串"):
        InputValidator.validate_test_cases(test_cases)


def test_validate_test_case_name_empty():
    """测试: 空 name 被拒绝"""
    test_cases = [{"name": "   ", "steps": ["步骤1"]}]
    with pytest.raises(ValueError, match="测试用例 0 的 name 不能为空"):
        InputValidator.validate_test_cases(test_cases)


def test_validate_test_case_name_too_long():
    """测试: 超长 name 被拒绝"""
    test_cases = [{"name": "A" * 201, "steps": ["步骤1"]}]
    with pytest.raises(ValueError, match="测试用例 0 的 name 长度不能超过 200 字符"):
        InputValidator.validate_test_cases(test_cases)


def test_validate_test_case_name_strips_whitespace():
    """测试: name 前后空白被去除"""
    test_cases = [{"name": "  测试名称  ", "steps": ["步骤1"]}]
    result = InputValidator.validate_test_cases(test_cases)
    assert result[0]["name"] == "测试名称"


def test_validate_test_case_preserves_other_fields():
    """测试: 其他字段被保留"""
    test_cases = [
        {
            "name": "测试1",
            "steps": ["步骤1", "步骤2"],
            "expected_result": "结果1",
            "priority": "high",
        }
    ]
    result = InputValidator.validate_test_cases(test_cases)
    assert result[0]["steps"] == ["步骤1", "步骤2"]
    assert result[0]["expected_result"] == "结果1"
    assert result[0]["priority"] == "high"


# ========== InputValidator.validate_uuid ==========


def test_validate_uuid_valid():
    """测试: 有效 UUID 通过验证"""
    valid_uuid = "550e8400-e29b-41d4-a716-446655440000"
    result = InputValidator.validate_uuid(valid_uuid)
    assert result == valid_uuid


def test_validate_uuid_lowercase():
    """测试: 小写 UUID 通过验证"""
    valid_uuid = "550e8400-e29b-41d4-a716-446655440000"
    result = InputValidator.validate_uuid(valid_uuid.lower())
    assert result == valid_uuid.lower()


def test_validate_uuid_uppercase():
    """测试: 大写 UUID 通过验证"""
    valid_uuid = "550E8400-E29B-41D4-A716-446655440000"
    result = InputValidator.validate_uuid(valid_uuid)
    assert result == valid_uuid


def test_validate_uuid_mixed_case():
    """测试: 混合大小写 UUID 通过验证"""
    valid_uuid = "550E8400-e29b-41d4-A716-446655440000"
    result = InputValidator.validate_uuid(valid_uuid)
    assert result == valid_uuid


def test_validate_uuid_nil():
    """测试: Nil UUID (全零) 通过验证"""
    nil_uuid = "00000000-0000-0000-0000-000000000000"
    result = InputValidator.validate_uuid(nil_uuid)
    assert result == nil_uuid


def test_validate_uuid_empty():
    """测试: 空 UUID 被拒绝"""
    with pytest.raises(ValueError, match="ID 不能为空"):
        InputValidator.validate_uuid("")


def test_validate_uuid_none():
    """测试: None UUID 被拒绝"""
    with pytest.raises(ValueError, match="ID 不能为空"):
        InputValidator.validate_uuid(None)


def test_validate_uuid_non_string():
    """测试: 非字符串 UUID 被拒绝"""
    with pytest.raises(ValueError, match="ID 不能为空"):
        InputValidator.validate_uuid(123)


def test_validate_uuid_invalid_format():
    """测试: 无效格式 UUID 被拒绝"""
    with pytest.raises(ValueError, match="ID 格式不正确，必须是有效的 UUID"):
        InputValidator.validate_uuid("not-a-uuid")


def test_validate_uuid_missing_hyphens():
    """测试: 缺少连字符的 UUID 被拒绝"""
    with pytest.raises(ValueError, match="ID 格式不正确，必须是有效的 UUID"):
        InputValidator.validate_uuid("550e8400e29b41d4a716446655440000")


def test_validate_uuid_custom_field_name():
    """测试: 自定义字段名称在错误消息中"""
    with pytest.raises(ValueError, match="project ID 格式不正确"):
        InputValidator.validate_uuid("invalid", "project ID")


# ========== InputValidator.sanitize_html ==========


def test_sanitize_html_basic():
    """测试: 基本 HTML 特殊字符被转义"""
    result = InputValidator.sanitize_html("<b>bold</b> & <i>italic</i>")
    assert result == "&lt;b&gt;bold&lt;/b&gt; &amp; &lt;i&gt;italic&lt;/i&gt;"


def test_sanitize_html_ampersand():
    """测试: & 符号被转义"""
    result = InputValidator.sanitize_html("A & B")
    assert result == "A &amp; B"


def test_sanitize_html_less_than():
    """测试: < 符号被转义"""
    result = InputValidator.sanitize_html("A < B")
    assert result == "A &lt; B"


def test_sanitize_html_greater_than():
    """测试: > 符号被转义"""
    result = InputValidator.sanitize_html("A > B")
    assert result == "A &gt; B"


def test_sanitize_html_double_quote():
    """测试: 双引号被转义"""
    result = InputValidator.sanitize_html('He said "hello"')
    assert result == "He said &quot;hello&quot;"


def test_sanitize_html_single_quote():
    """测试: 单引号被转义"""
    result = InputValidator.sanitize_html("It's mine")
    assert result == "It&#x27;s mine"


def test_sanitize_html_multiple_chars():
    """测试: 多个特殊字符被正确转义"""
    result = InputValidator.sanitize_html("<>&'\"")
    assert result == "&lt;&gt;&amp;&#x27;&quot;"


def test_sanitize_html_no_special_chars():
    """测试: 无特殊字符保持不变"""
    result = InputValidator.sanitize_html("normal text 123")
    assert result == "normal text 123"


def test_sanitize_html_chinese_characters():
    """测试: 中文字符保持不变"""
    result = InputValidator.sanitize_html("中文内容")
    assert result == "中文内容"


# ========== InputValidator.validate_dependency_mapping ==========


def test_validate_dependency_mapping_valid():
    """测试: 有效依赖映射通过验证"""
    mapping = {
        "550e8400-e29b-41d4-a716-446655440000": [
            "660e8400-e29b-41d4-a716-446655440000"
        ],
        "770e8400-e29b-41d4-a716-446655440000": [],
    }
    result = InputValidator.validate_dependency_mapping(mapping)
    assert len(result) == 2
    assert "550e8400-e29b-41d4-a716-446655440000" in result


def test_validate_dependency_mapping_empty():
    """测试: 空依赖映射被接受"""
    result = InputValidator.validate_dependency_mapping({})
    assert result == {}


def test_validate_dependency_mapping_not_dict():
    """测试: 非字典类型被拒绝"""
    with pytest.raises(ValueError, match="依赖映射必须是字典"):
        InputValidator.validate_dependency_mapping("not a dict")


def test_validate_dependency_mapping_invalid_req_id():
    """测试: 无效需求 ID 被拒绝"""
    mapping = {"invalid-uuid": []}
    with pytest.raises(ValueError, match="需求 ID 格式不正确，必须是有效的 UUID"):
        InputValidator.validate_dependency_mapping(mapping)


def test_validate_dependency_mapping_deps_not_list():
    """测试: 依赖不是列表被拒绝"""
    mapping = {"550e8400-e29b-41d4-a716-446655440000": "not a list"}
    with pytest.raises(
        ValueError, match="需求 550e8400-e29b-41d4-a716-446655440000 的依赖必须是数组"
    ):
        InputValidator.validate_dependency_mapping(mapping)


def test_validate_dependency_mapping_invalid_dep_id():
    """测试: 无效依赖 ID 被拒绝"""
    mapping = {"550e8400-e29b-41d4-a716-446655440000": ["invalid-uuid"]}
    with pytest.raises(ValueError, match="依赖 ID 格式不正确，必须是有效的 UUID"):
        InputValidator.validate_dependency_mapping(mapping)


def test_validate_dependency_mapping_preserves_structure():
    """测试: 映射结构被保留"""
    mapping = {
        "550e8400-e29b-41d4-a716-446655440000": [
            "660e8400-e29b-41d4-a716-446655440000",
            "770e8400-e29b-41d4-a716-446655440000",
        ]
    }
    result = InputValidator.validate_dependency_mapping(mapping)
    assert len(result["550e8400-e29b-41d4-a716-446655440000"]) == 2


# ========== SecurityChecker.check_for_malicious_input ==========


def test_check_malicious_input_safe_string():
    """测试: 安全字符串输入返回 True"""
    assert SecurityChecker.check_for_malicious_input("normal text") is True


def test_check_malicious_input_with_xss():
    """测试: XSS 输入返回 False"""
    assert (
        SecurityChecker.check_for_malicious_input("<script>alert(1)</script>") is False
    )


def test_check_malicious_input_with_sql():
    """测试: SQL 注入输入返回 False"""
    assert SecurityChecker.check_for_malicious_input("'; DROP TABLE--") is False


def test_check_malicious_input_dict_with_safe_values():
    """测试: 字典安全值返回 True"""
    input_data = {"name": "test", "value": "123"}
    assert SecurityChecker.check_for_malicious_input(input_data) is True


def test_check_malicious_input_dict_with_malicious_value():
    """测试: 字典恶意值返回 False（不安全）"""
    input_data = {"name": "test", "content": "<script>alert(1)</script>"}
    assert (
        SecurityChecker.check_for_malicious_input(input_data) is False
    )  # 检测到恶意内容，返回 False


def test_check_malicious_input_list_with_safe_values():
    """测试: 列表安全值返回 True"""
    input_data = ["item1", "item2", "item3"]
    assert SecurityChecker.check_for_malicious_input(input_data) is True


def test_check_malicious_input_list_with_malicious_value():
    """测试: 列表恶意值返回 False（不安全）"""
    input_data = ["safe", "<script>alert(1)</script>", "also safe"]
    assert (
        SecurityChecker.check_for_malicious_input(input_data) is False
    )  # 检测到恶意内容，返回 False


def test_check_malicious_input_nested_structure():
    """测试: 嵌套结构不递归检查 dict 内的 list（dict 分支只检查字符串值）"""
    input_data = {"items": ["<script>", "safe"], "count": 2}
    # 实现只检查 dict 顶层的字符串值，不递归检查嵌套列表
    assert SecurityChecker.check_for_malicious_input(input_data) is True


# ========== SecurityChecker.check_depth_limit ==========


def test_check_depth_limit_within_limit():
    """测试: 深度在限制内通过"""
    SecurityChecker.check_depth_limit(5, max_depth=10)  # 不应抛出异常


def test_check_depth_limit_at_limit():
    """测试: 深度等于限制通过"""
    SecurityChecker.check_depth_limit(10, max_depth=10)  # 不应抛出异常


def test_check_depth_limit_exceeds():
    """测试: 深度超过限制被拒绝"""
    with pytest.raises(ValueError, match="深度 \\(11\\) 超过最大限制 \\(10\\)"):
        SecurityChecker.check_depth_limit(11, max_depth=10)


def test_check_depth_limit_custom_max():
    """测试: 自定义最大深度"""
    with pytest.raises(ValueError, match="深度 \\(101\\) 超过最大限制 \\(100\\)"):
        SecurityChecker.check_depth_limit(101, max_depth=100)


# ========== SecurityChecker.check_node_count ==========


def test_check_node_count_within_limit():
    """测试: 节点数在限制内通过"""
    SecurityChecker.check_node_count(5000, max_count=10000)  # 不应抛出异常


def test_check_node_count_at_limit():
    """测试: 节点数等于限制通过"""
    SecurityChecker.check_node_count(10000, max_count=10000)  # 不应抛出异常


def test_check_node_count_exceeds():
    """测试: 节点数超过限制被拒绝"""
    with pytest.raises(
        ValueError, match="节点数量 \\(10001\\) 超过最大限制 \\(10000\\)"
    ):
        SecurityChecker.check_node_count(10001, max_count=10000)


def test_check_node_count_custom_max():
    """测试: 自定义最大节点数"""
    with pytest.raises(ValueError, match="节点数量 \\(1001\\) 超过最大限制 \\(1000\\)"):
        SecurityChecker.check_node_count(1001, max_count=1000)
