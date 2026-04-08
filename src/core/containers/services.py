# Copyright (c) 2026 Kirky.X. All rights reserved.
# Licensed under the MIT License.
# See LICENSE file in the project root for full license information.

"""业务服务 Provider"""

from dependency_injector import containers, providers

from src.services.chain_builder import ChainBuilder
from src.services.chain_orchestrator import ChainOrchestrator
from src.services.complexity_evaluator import ComplexityEvaluator
from src.services.decomposition_advisor import DecompositionAdvisor
from src.services.dependency_service import DependencyService
from src.services.project_manager import ProjectManager
from src.services.requirement_manager import RequirementManager
from src.services.validation_service import ValidationService
from src.utils.cache import CacheManager
from src.utils.graph import GraphAlgorithms
from src.utils.snapshot_manager import SnapshotManager


class ServicesContainer(containers.DeclarativeContainer):
    """业务服务容器"""

    # 配置
    config = providers.Configuration()

    # 外部依赖（通过 wiring 注入）
    cache_manager = providers.Dependency(instance_of=CacheManager)
    graph_algorithms = providers.Dependency(instance_of=GraphAlgorithms)
    snapshot_manager = providers.Dependency(instance_of=SnapshotManager)

    # 无依赖的辅助服务 (Singleton)
    complexity_evaluator = providers.Singleton(ComplexityEvaluator)
    decomposition_advisor = providers.Singleton(DecompositionAdvisor)

    # 无依赖的核心服务 (Singleton)
    dependency_service = providers.Singleton(DependencyService)
    validation_service = providers.Singleton(ValidationService)

    # 有依赖的核心服务 (Singleton)
    project_manager = providers.Singleton(
        ProjectManager,
        cache=cache_manager,
    )

    requirement_manager = providers.Singleton(
        RequirementManager,
        cache=cache_manager,
        complexity_evaluator=complexity_evaluator,
        decomposition_advisor=decomposition_advisor,
    )

    chain_builder = providers.Singleton(
        ChainBuilder,
        cache=cache_manager,
        graph_algorithms=graph_algorithms,
    )

    chain_orchestrator = providers.Singleton(
        ChainOrchestrator,
        chain_builder=chain_builder,
        snapshot_manager=snapshot_manager,
    )
