#!/usr/bin/env python
# Copyright (c) 2026 Kirky.X. All rights reserved.
# Licensed under the MIT License.
# See LICENSE file in the project root for full license information.

"""独立的 HTTP API 服务器启动脚本

使用方式:
    python run_http_server.py                    # 默认端口 8080
    python run_http_server.py --port 9000        # 自定义端口
    python run_http_server.py --host 127.0.0.1   # 自定义地址
"""

import argparse
import os
import sys

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.api.mcp_server import start_http_server, stop_http_server


def main():
    parser = argparse.ArgumentParser(description="MCP-Axon HTTP API 服务器")
    parser.add_argument(
        "--host",
        default="0.0.0.0",
        help="绑定地址 (默认: 0.0.0.0)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8080,
        help="端口号 (默认: 8080)",
    )
    args = parser.parse_args()

    print("=" * 50)
    print("MCP-Axon HTTP API 服务器")
    print("=" * 50)
    print()
    print(f"服务器地址: http://{args.host}:{args.port}")
    print()
    print("可用端点:")
    print("  GET /health       - 健康检查")
    print("  GET /metrics      - 性能指标")
    print("  GET /api_version  - API 版本信息")
    print("  GET /             - 根路径信息")
    print()
    print("启动 MCP 服务器模式:")
    print("  python -m src.api.mcp_server --mode mcp")
    print()
    print("同时启动 MCP 和 HTTP 服务器:")
    print("  python -m src.api.mcp_server --mode both --http-port 8080")
    print()
    print("按 Ctrl+C 停止服务器")
    print("=" * 50)

    # 启动 HTTP 服务器
    start_http_server(host=args.host, port=args.port)

    # 保持运行
    try:
        while True:
            import time

            time.sleep(1)
    except KeyboardInterrupt:
        print("\n收到停止信号，正在关闭服务器...")
        stop_http_server()
        print("服务器已关闭")


if __name__ == "__main__":
    main()
