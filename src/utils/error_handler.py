# Copyright (c) 2026 Kirky.X. All rights reserved.
# Licensed under the MIT License.
# See LICENSE file in the project root for full license information.

"""错误处理工具"""

# 已知业务异常类型，可返回具体消息
_KNOWN_ERROR_PREFIXES = (
    "项目不存在",
    "需求不存在",
    "验证节点不存在",
    "项目已",
    "项目未",
    "锁",
    "快照",
    "需求",
    "内容",
    "参数",
    "创建",
    "更新",
    "删除",
    "依赖",
    "链化",
    "无法",
    "不能",
    "必须",
    "无效",
    "格式",
    "无权",
    "找不到",
)


def get_safe_error_message(error_message: str) -> str:
    """获取安全的错误消息

    仅当错误消息以已知业务关键词开头时返回原始消息，
    否则返回通用提示，防止泄露堆栈跟踪、文件路径等内部信息。
    """
    if not error_message:
        return "操作失败，请稍后重试"

    # 检查是否以已知业务异常前缀开头
    for prefix in _KNOWN_ERROR_PREFIXES:
        if error_message.startswith(prefix):
            return error_message

    return "操作失败，请稍后重试"
