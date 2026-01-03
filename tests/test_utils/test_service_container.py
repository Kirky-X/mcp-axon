# Copyright (c) 2026 Kirky.X. All rights reserved.
# Licensed under MIT License.
# See LICENSE file in project root for full license information.

"""依赖注入容器测试"""

import pytest

from src.utils.service_container import ServiceContainer, service_container


class MockService:
    """模拟服务"""

    def __init__(self):
        self.value = "mock-service"


def test_register_and_get_service():
    """测试注册和获取服务"""
    container = ServiceContainer()

    # 注册服务工厂
    container.register_service("mock_service", MockService)

    # 获取服务
    service = container.get("mock_service")

    assert isinstance(service, MockService)
    assert service.value == "mock-service"


def test_register_instance():
    """测试注册服务实例"""
    container = ServiceContainer()
    instance = MockService()

    # 注册实例
    container.register_instance("mock_service", instance)

    # 获取实例
    service = container.get("mock_service")

    assert service is instance
    assert service.value == "mock-service"


def test_singleton_behavior():
    """测试单例行为（工厂函数只调用一次）"""
    container = ServiceContainer()

    # 注册服务工厂
    container.register_service("mock_service", MockService)

    # 多次获取服务
    service1 = container.get("mock_service")
    service2 = container.get("mock_service")

    # 应该返回同一个实例
    assert service1 is service2


def test_service_not_registered():
    """测试获取未注册的服务"""
    container = ServiceContainer()

    # 尝试获取未注册的服务
    with pytest.raises(ValueError, match="服务 'unknown_service' 未注册"):
        container.get("unknown_service")


def test_reset():
    """测试重置所有服务"""
    container = ServiceContainer()

    # 注册服务
    container.register_service("mock_service", MockService)
    service1 = container.get("mock_service")

    # 重置
    container.reset()

    # 重置后再次获取应该创建新实例
    service2 = container.get("mock_service")

    assert service1 is not service2


def test_instance_overrides_factory():
    """测试实例覆盖工厂"""
    container = ServiceContainer()

    # 注册工厂
    container.register_service("mock_service", MockService)

    # 注册实例（覆盖工厂）
    instance = MockService()
    instance.value = "custom-instance"
    container.register_instance("mock_service", instance)

    # 应该返回实例，而不是工厂创建的
    service = container.get("mock_service")

    assert service.value == "custom-instance"


def test_global_container():
    """测试全局容器实例"""
    # 注册服务到全局容器
    service_container.register_service("global_mock", MockService)

    # 获取服务
    service = service_container.get("global_mock")

    assert isinstance(service, MockService)

    # 清理
    service_container.reset()
