# Copyright (c) 2026 Kirky.X. All rights reserved.
# Licensed under the MIT License.
# See LICENSE file in the project root for full license information.

"""性能调优配置"""

from typing import Any, Dict, Optional

import yaml


class PerformanceConfig:
    """
    性能调优配置类

    管理各种性能相关的配置参数
    """

    # 默认配置
    DEFAULT_CONFIG = {
        # 数据库配置
        "database": {
            "pool_size": 5,
            "max_overflow": 10,
            "pool_timeout": 30,
            "pool_recycle": 3600,
            "echo": False,
        },
        # 缓存配置
        "cache": {
            "enabled": True,
            "max_size": 1000,
            "ttl_seconds": 300,
        },
        # 限流配置
        "rate_limiting": {
            "enabled": True,
            "max_requests": 100,
            "window_seconds": 60,
        },
        # 性能阈值
        "performance_thresholds": {
            "slow_operation": 1.0,  # 秒
            "slow_db_query": 0.5,  # 秒
            "slow_api_call": 0.5,  # 秒
        },
        # 图算法配置
        "graph": {
            "max_nodes": 10000,
            "max_edges": 50000,
        },
        # 链化配置
        "chaining": {
            "batch_size": 100,
            "max_retries": 3,
            "retry_delay": 1,
        },
        # 日志配置
        "logging": {
            "level": "INFO",
            "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        },
        # 监控配置
        "monitoring": {
            "enabled": True,
            "export_interval": 60,  # 秒
            "prometheus_port": 9090,
        },
        # 安全配置
        "security": {
            "input_validation": True,
            "xss_protection": True,
            "sql_injection_protection": True,
            "max_content_length": 5000,
            "max_name_length": 200,
        },
    }

    def __init__(self, config_path: Optional[str] = None):
        """
        初始化配置

        Args:
            config_path: 配置文件路径（可选）
        """
        self.config = self.DEFAULT_CONFIG.copy()

        if config_path:
            self.load_from_file(config_path)

    def load_from_file(self, config_path: str) -> None:
        """
        从文件加载配置

        Args:
            config_path: 配置文件路径
        """
        try:
            with open(config_path, "r") as f:
                loaded_config = yaml.safe_load(f)

            if loaded_config:
                self._merge_config(self.config, loaded_config)

        except FileNotFoundError:
            raise ValueError(f"配置文件不存在: {config_path}")
        except yaml.YAMLError as e:
            raise ValueError(f"配置文件格式错误: {e}")

    def _merge_config(self, base: Dict, override: Dict) -> None:
        """
        递归合并配置

        Args:
            base: 基础配置
            override: 覆盖配置
        """
        for key, value in override.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                self._merge_config(base[key], value)
            else:
                base[key] = value

    def get(self, key_path: str, default: Any = None) -> Any:
        """
        获取配置值

        Args:
            key_path: 配置键路径（如 "database.pool_size"）
            default: 默认值

        Returns:
            配置值
        """
        keys = key_path.split(".")
        value = self.config

        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default

        return value

    def set(self, key_path: str, value: Any) -> None:
        """
        设置配置值

        Args:
            key_path: 配置键路径（如 "database.pool_size"）
            value: 配置值
        """
        keys = key_path.split(".")
        config: Dict[str, Any] = self.config

        for key in keys[:-1]:
            if key not in config:
                config[key] = {}
            config = config[key]

        config[keys[-1]] = value

    def save_to_file(self, config_path: str) -> None:
        """
        保存配置到文件

        Args:
            config_path: 配置文件路径
        """
        with open(config_path, "w") as f:
            yaml.dump(self.config, f, default_flow_style=False, allow_unicode=True)

    def get_database_config(self) -> Dict[str, Any]:
        """
        获取数据库配置

        Returns:
            数据库配置字典
        """
        return self.config["database"]

    def get_cache_config(self) -> Dict[str, Any]:
        """
        获取缓存配置

        Returns:
            缓存配置字典
        """
        return self.config["cache"]

    def get_performance_thresholds(self) -> Dict[str, Any]:
        """
        获取性能阈值

        Returns:
            性能阈值字典
        """
        return self.config["performance_thresholds"]

    def get_graph_config(self) -> Dict[str, Any]:
        """
        获取图算法配置

        Returns:
            图算法配置字典
        """
        return self.config["graph"]

    def get_chaining_config(self) -> Dict[str, Any]:
        """
        获取链化配置

        Returns:
            链化配置字典
        """
        return self.config["chaining"]

    def get_security_config(self) -> Dict[str, Any]:
        """
        获取安全配置

        Returns:
            安全配置字典
        """
        return self.config["security"]

    def get_monitoring_config(self) -> Dict[str, Any]:
        """
        获取监控配置

        Returns:
            监控配置字典
        """
        return self.config["monitoring"]


# 全局配置实例
performance_config = PerformanceConfig()


def get_config() -> PerformanceConfig:
    """
    获取全局配置实例

    Returns:
        性能配置实例
    """
    return performance_config


def load_config(config_path: str) -> None:
    """
    加载配置文件

    Args:
        config_path: 配置文件路径
    """
    performance_config.load_from_file(config_path)


def save_config(config_path: str) -> None:
    """
    保存配置到文件

    Args:
        config_path: 配置文件路径
    """
    performance_config.save_to_file(config_path)


# 使用示例
if __name__ == "__main__":
    # 创建示例配置文件
    config = PerformanceConfig()
    config.save_to_file("config/performance.yml")

    # 读取配置
    print(f"数据库连接池大小: {config.get('database.pool_size')}")
    print(f"慢操作阈值: {config.get('performance_thresholds.slow_operation')} 秒")
    print(f"图最大节点数: {config.get('graph.max_nodes')}")
