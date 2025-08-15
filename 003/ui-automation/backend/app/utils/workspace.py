"""
Playwright 工作空间解析与辅助。

提供统一的方法在运行时解析 Playwright 的工作空间路径，避免代码中写死绝对路径，
并允许通过环境变量与配置灵活切换。
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

from app.core.config import settings
from loguru import logger


def resolve_playwright_workspace(explicit_path: Optional[str] = None) -> Path:
    """解析 Playwright 工作空间路径。

    优先级：
    1) 函数参数 explicit_path（若传入且存在）
    2) 环境变量 PLAYWRIGHT_WORKSPACE
    3) 配置 settings.MIDSCENE_SCRIPT_PATH
    4) 项目内示例目录 ui-automation/examples/midscene-playwright
    5) 历史兜底路径 C:\\Users\\86134\\Desktop\\workspace\\playwright-workspace
    """
    # 1) 显式传入
    if explicit_path:
        p = Path(explicit_path)
        if p.exists():
            return p

    # 2) 环境变量
    env_path = os.getenv("PLAYWRIGHT_WORKSPACE", "").strip()
    if env_path:
        p = Path(env_path)
        if p.exists():
            return p

    # 3) 配置
    cfg_path = getattr(settings, "MIDSCENE_SCRIPT_PATH", None)
    if cfg_path:
        p = Path(cfg_path)
        if p.exists():
            return p

    # 4) 项目内示例目录：从当前文件向上寻找 ui-automation 根
    try:
        current = Path(__file__).resolve()
        ui_root = None
        for ancestor in current.parents:
            if ancestor.name == "ui-automation":
                ui_root = ancestor
                break
        if ui_root is not None:
            example = ui_root / "examples" / "midscene-playwright"
            if example.exists():
                return example
    except Exception as e:
        logger.debug(f"定位示例目录失败: {e}")

    # 5) 兜底路径 - 使用项目内的示例目录
    return Path(r"E:\Program Files\cursorproject\testing\003\ui-automation\examples\midscene-playwright")


