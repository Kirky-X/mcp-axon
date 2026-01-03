# Copyright (c) 2026 Kirky.X. All rights reserved.
# Licensed under MIT License.
# See LICENSE file in project root for full license information.

"""依赖注入容器"""

from typing import Any, Callable, Dict


class ServiceContainer:
    """简单的依赖注入容器"""

    def __init__(self):
        """初始化服务容器"""
        self._services: Dict[str, Any] = {}
        self._factories: Dict[str, Callable] = {}

    def register_service(self, name: str, factory: Callable) -> None:
        """
        注册服务工厂函数

        Args:
            name: 服务名称
            factory: 服务工厂函数（返回服务实例）
        """
        self._factories[name] = factory

    def register_instance(self, name: str, instance: Any) -> None:
        """
        注册服务实例

        Args:
            name: 服务名称
            instance: 服务实例
        """
        self._services[name] = instance

    def get(self, name: str) -> Any:
        """
        获取服务实例

        Args:
            name: 服务名称

        Returns:
            服务实例

        Raises:
            ValueError: 服务未注册
        """
        # 首先检查是否已注册实例
        if name in self._services:
            return self._services[name]

        # 检查是否有工厂函数
        if name not in self._factories:
            raise ValueError(f"服务 '{name}' 未注册")

        # 使用工厂函数创建实例
        instance = self._factories[name]()
        self._services[name] = instance
        return instance

    def reset(self) -> None:
        """重置所有服务（主要用于测试）"""
        self._services.clear()


# 全局服务容器实例
service_container = ServiceContainer()
