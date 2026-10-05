#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Scribble 模板映射

提供预定义的 Scribble 模板路径映射。
"""

import os

# 获取模板目录路径
TEMPLATES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "templates")

# Scribble 模板映射
SCRIBBLE_MAP = {
    "desk": os.path.join(TEMPLATES_DIR, "desk.png"),
    "stand": os.path.join(TEMPLATES_DIR, "stand.png"),
}

# 模板显示名称映射
SCRIBBLE_DISPLAY_NAMES = {
    "desk": "桌面 | 商品放在桌面上",
    "stand": "展示台 | 圆形展示台",
}


def get_scribble_path(key: str) -> str:
    """
    根据 key 获取 scribble 模板路径

    参数:
        key: 模板键名 (desk / stand)

    返回:
        模板文件路径
    """
    return SCRIBBLE_MAP.get(key, SCRIBBLE_MAP["desk"])


def get_scribble_options():
    """
    获取所有 scribble 选项 (用于 UI 下拉框)

    返回:
        list: 显示名称列表
    """
    return list(SCRIBBLE_DISPLAY_NAMES.values())


def parse_scribble_key(display_name: str) -> str:
    """
    从显示名称解析出 key

    参数:
        display_name: 显示名称 (如 "桌面 | 商品放在桌面上")

    返回:
        str: 模板键名，自定义画板返回 "custom"
    """
    # 处理自定义画板选项
    if display_name.startswith("自定义") or display_name.startswith("custom"):
        return "custom"
    
    for key, name in SCRIBBLE_DISPLAY_NAMES.items():
        if name == display_name or display_name.startswith(key):
            return key
    return "desk"
