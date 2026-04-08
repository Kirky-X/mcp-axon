# Copyright (c) 2026 Kirky.X. All rights reserved.
# Licensed under the MIT License.
# See LICENSE file in the project root for full license information.

"""pytest 配置文件"""

import os
import pathlib
import sys
import tempfile


# 禁用字节码缓存生成
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"

# 禁用 pytest-benchmark
os.environ["PYTEST_BENCHMARK_DISABLE"] = "1"

# 设置缓存目录到系统临时目录
cache_dir = pathlib.Path(tempfile.gettempdir()) / "pytest_cache_mcp_axon"
cache_dir.mkdir(parents=True, exist_ok=True)


# 配置 pytest
def pytest_configure(config):
    """pytest 配置钩子"""

    # 禁用 benchmark 插件
    if hasattr(config, "option"):
        config.option.benchmark_disable = True

    # 设置缓存目录
    if hasattr(config, "cache"):
        config.cache.set("cache_dir", str(cache_dir))


# 确保不生成 __pycache__
sys.dont_write_bytecode = True
