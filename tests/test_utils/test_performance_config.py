# Copyright (c) 2026 Kirky.X. All rights reserved.
# Licensed under the MIT License.
# See LICENSE file in the project root for full license information.

"""性能配置管理测试"""

import tempfile
from pathlib import Path

import pytest
import yaml

from src.utils.performance_config import (
    PerformanceConfig,
    get_config,
    load_config,
    save_config,
)


# ========== load_from_file ==========


def test_load_from_valid_yaml():
    """测试: 从有效 YAML 文件加载"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yml", delete=False) as f:
        yaml.dump({"database": {"pool_size": 10}}, f)
        temp_path = Path(f.name)

    try:
        config = PerformanceConfig()
        config.load_from_file(str(temp_path))

        assert config.config["database"]["pool_size"] == 10
    finally:
        temp_path.unlink()


def test_load_from_file_not_exists():
    """测试: 文件不存在时抛出错误"""
    config = PerformanceConfig()

    with pytest.raises(ValueError, match="配置文件不存在"):
        config.load_from_file("/nonexistent/path.yml")


def test_load_from_invalid_yaml_syntax():
    """测试: YAML 语法错误时抛出错误"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yml", delete=False) as f:
        f.write("invalid: yaml: content:\n  - item1\n    item2")  # 错误缩进
        temp_path = Path(f.name)

    try:
        config = PerformanceConfig()
        with pytest.raises(ValueError, match="配置文件格式错误"):
            config.load_from_file(str(temp_path))
    finally:
        temp_path.unlink()


def test_load_from_merges_with_default():
    """测试: 加载时与默认配置合并"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yml", delete=False) as f:
        yaml.dump({"database": {"pool_size": 15}}, f)
        temp_path = Path(f.name)

    try:
        config = PerformanceConfig()
        original_pool_size = config.config["database"]["pool_size"]

        config.load_from_file(str(temp_path))

        # pool_size 应该被更新
        assert config.config["database"]["pool_size"] == 15
        # 其他默认配置应该保留
        assert config.config["cache"]["enabled"] is True
        assert "security" in config.config
    finally:
        temp_path.unlink()


# ========== get ==========


def test_get_nested_value():
    """测试: 获取嵌套配置值"""
    config = PerformanceConfig()

    result = config.get("database.pool_size")

    assert result == 5


def test_get_with_default_for_missing_path():
    """测试: 获取不存在路径时返回默认值"""
    config = PerformanceConfig()

    result = config.get("nonexistent.path", default="default_value")

    assert result == "default_value"


def test_get_with_default_none():
    """测试: 获取时默认 None"""
    config = PerformanceConfig()

    result = config.get("nonexistent.path")

    assert result is None


def test_get_top_level_key():
    """测试: 获取顶层配置"""
    config = PerformanceConfig()

    result = config.get("database")

    assert isinstance(result, dict)
    assert "pool_size" in result


# ========== set ==========


def test_set_nested_value():
    """测试: 设置嵌套配置值"""
    config = PerformanceConfig()

    config.set("database.pool_size", 10)

    assert config.config["database"]["pool_size"] == 10


def test_set_creates_nested_structure():
    """测试: 设置时创建嵌套结构"""
    config = PerformanceConfig()

    config.set("new_section.new_key", "value")

    assert config.config["new_section"]["new_key"] == "value"


def test_set_updates_existing_value():
    """测试: 更新现有值"""
    config = PerformanceConfig()

    original = config.config["database"]["pool_size"]
    config.set("database.pool_size", 20)

    assert config.config["database"]["pool_size"] == 20
    assert config.config["database"]["pool_size"] != original


def test_set_deep_nesting():
    """测试: 设置深层嵌套值"""
    config = PerformanceConfig()

    config.set("level1.level2.level3.value", 123)

    assert config.config["level1"]["level2"]["level3"]["value"] == 123


# ========== _merge_config ==========


def test_merge_config_updates_values():
    """测试: 合并更新值"""
    base = {"a": {"b": 1, "c": 2}}
    override = {"a": {"b": 3}}
    config = PerformanceConfig()

    config._merge_config(base, override)

    assert base["a"]["b"] == 3  # 更新
    assert base["a"]["c"] == 2  # 保留


def test_merge_config_adds_new_keys():
    """测试: 合并添加新键"""
    base = {"a": {"b": 1}}
    override = {"a": {"d": 4}}
    config = PerformanceConfig()

    config._merge_config(base, override)

    assert base["a"]["b"] == 1  # 保留
    assert base["a"]["d"] == 4  # 新增


def test_merge_config_adds_new_top_level():
    """测试: 合并添加顶层键"""
    base = {"a": 1}
    override = {"b": 2}
    config = PerformanceConfig()

    config._merge_config(base, override)

    assert base["a"] == 1
    assert base["b"] == 2


def test_merge_config_with_dicts():
    """测试: 合并递归处理字典"""
    base = {"a": {"b": {"c": 1}}}
    override = {"a": {"b": {"d": 2}}}
    config = PerformanceConfig()

    config._merge_config(base, override)

    assert base["a"]["b"]["c"] == 1
    assert base["a"]["b"]["d"] == 2


def test_merge_config_replaces_non_dict():
    """测试: 合并时非字典值被替换"""
    base = {"a": {"b": [1, 2]}}
    override = {"a": {"b": [3, 4]}}
    config = PerformanceConfig()

    config._merge_config(base, override)

    assert base["a"]["b"] == [3, 4]


# ========== save_to_file ==========


def test_save_to_file_creates_valid_yaml():
    """测试: 保存创建有效 YAML 文件"""
    config = PerformanceConfig()
    config.set("test_key", "test_value")

    with tempfile.NamedTemporaryFile(mode="w", suffix=".yml", delete=False) as f:
        temp_path = Path(f.name)

    try:
        config.save_to_file(str(temp_path))

        # 验证文件可以重新加载
        with temp_path.open("r") as f:
            loaded = yaml.safe_load(f)

        assert loaded["test_key"] == "test_value"
    finally:
        temp_path.unlink()


def test_save_to_file_preserves_structure():
    """测试: 保存保留嵌套结构"""
    config = PerformanceConfig()

    with tempfile.NamedTemporaryFile(mode="w", suffix=".yml", delete=False) as f:
        temp_path = Path(f.name)

    try:
        config.save_to_file(str(temp_path))

        # 验证嵌套结构
        with temp_path.open("r") as f:
            loaded = yaml.safe_load(f)

        assert "database" in loaded
        assert "pool_size" in loaded["database"]
    finally:
        temp_path.unlink()


def test_save_to_file_unwritable_path():
    """测试: 保存到不可写路径抛出错误"""
    config = PerformanceConfig()

    with pytest.raises((ValueError, OSError, PermissionError)):
        config.save_to_file("/root/unwritable.yml")


# ========== Type casting ==========


def test_type_casting_int():
    """测试: 整数类型转换"""
    config = PerformanceConfig()

    value = config.get("database.pool_size")

    assert isinstance(value, int)
    assert value == 5


def test_type_casting_float():
    """测试: 浮点数类型转换"""
    config = PerformanceConfig()

    value = config.get("performance_thresholds.slow_operation")

    assert isinstance(value, float)
    assert value == 1.0


def test_type_casting_bool():
    """测试: 布尔类型转换"""
    config = PerformanceConfig()

    value = config.get("cache.enabled")

    assert isinstance(value, bool)
    assert value is True


def test_type_casting_list():
    """测试: 列表类型转换"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yml", delete=False) as f:
        yaml.dump({"test": {"items": [1, 2, 3]}}, f)
        temp_path = Path(f.name)

    try:
        config = PerformanceConfig()
        config.load_from_file(str(temp_path))

        value = config.get("test.items")

        assert isinstance(value, list)
        assert value == [1, 2, 3]
    finally:
        temp_path.unlink()


# ========== Convenience getters ==========


def test_get_database_config():
    """测试: 获取数据库配置"""
    config = PerformanceConfig()

    db_config = config.get_database_config()

    assert isinstance(db_config, dict)
    assert "pool_size" in db_config
    assert db_config["pool_size"] == 5


def test_get_cache_config():
    """测试: 获取缓存配置"""
    config = PerformanceConfig()

    cache_config = config.get_cache_config()

    assert isinstance(cache_config, dict)
    assert "enabled" in cache_config
    assert cache_config["enabled"] is True


def test_get_performance_thresholds():
    """测试: 获取性能阈值"""
    config = PerformanceConfig()

    thresholds = config.get_performance_thresholds()

    assert isinstance(thresholds, dict)
    assert "slow_operation" in thresholds
    assert thresholds["slow_operation"] == 1.0


def test_get_graph_config():
    """测试: 获取图算法配置"""
    config = PerformanceConfig()

    graph_config = config.get_graph_config()

    assert isinstance(graph_config, dict)
    assert "max_nodes" in graph_config
    assert graph_config["max_nodes"] == 10000


def test_get_chaining_config():
    """测试: 获取链化配置"""
    config = PerformanceConfig()

    chaining_config = config.get_chaining_config()

    assert isinstance(chaining_config, dict)
    assert "batch_size" in chaining_config
    assert chaining_config["batch_size"] == 100


def test_get_security_config():
    """测试: 获取安全配置"""
    config = PerformanceConfig()

    security_config = config.get_security_config()

    assert isinstance(security_config, dict)
    assert "input_validation" in security_config
    assert security_config["input_validation"] is True


def test_get_monitoring_config():
    """测试: 获取监控配置"""
    config = PerformanceConfig()

    monitoring_config = config.get_monitoring_config()

    assert isinstance(monitoring_config, dict)
    assert "enabled" in monitoring_config
    assert monitoring_config["enabled"] is True


# ========== Global config ==========


def test_get_config_returns_singleton():
    """测试: get_config 返回单例"""
    config1 = get_config()
    config2 = get_config()

    assert config1 is config2


def test_performance_config_has_defaults():
    """测试: PerformanceConfig 初始化包含默认值"""
    config = PerformanceConfig()

    assert "database" in config.config
    assert "cache" in config.config
    assert "rate_limiting" in config.config


def test_load_config_updates_global():
    """测试: load_config 更新全局配置"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yml", delete=False) as f:
        yaml.dump({"database": {"pool_size": 20}}, f)
        temp_path = Path(f.name)

    try:
        load_config(str(temp_path))

        config = get_config()
        assert config.get("database.pool_size") == 20
    finally:
        temp_path.unlink()


def test_save_config_saves_global():
    """测试: save_config 保存全局配置"""
    config = get_config()
    config.set("test", "value")

    with tempfile.NamedTemporaryFile(mode="w", suffix=".yml", delete=False) as f:
        temp_path = Path(f.name)

    try:
        save_config(str(temp_path))

        # 验证保存的内容
        with temp_path.open("r") as f:
            loaded = yaml.safe_load(f)

        assert loaded["test"] == "value"
    finally:
        temp_path.unlink()


# ========== Edge cases ==========


def test_get_empty_string_key():
    """测试: 空字符串键"""
    config = PerformanceConfig()

    config.set("", "value")

    assert config.get("") == "value"


def test_set_overwrites_scalar_with_dict():
    """测试: 设置时标量值被字典替换"""
    config = PerformanceConfig()
    config.config["test"] = "scalar"

    config.set("test", {"nested": "value"})

    assert config.config["test"] == {"nested": "value"}


def test_get_preserves_original_config():
    """测试: get 不修改原始配置"""
    config = PerformanceConfig()
    original_value = config.config["database"]["pool_size"]

    config.get("database.pool_size")

    assert config.config["database"]["pool_size"] == original_value


def test_merge_empty_override():
    """测试: 合并空覆盖不修改基础"""
    base = {"a": {"b": 1}}
    override = {}
    config = PerformanceConfig()

    config._merge_config(base, override)

    assert base == {"a": {"b": 1}}
