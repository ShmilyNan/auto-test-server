"""公共配置读取工具，降低 src/server 直接耦合。"""
from __future__ import annotations
import os
from typing import Optional


def get_env_str(name: str, default: Optional[str] = None) -> Optional[str]:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip()


def get_env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        return int(raw)
    except ValueError:
        return default
