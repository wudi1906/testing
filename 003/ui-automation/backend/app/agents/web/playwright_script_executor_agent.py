"""
Playwright执行智能体 - 全新改造版本
负责执行基于MidScene.js + Playwright的测试脚本
执行环境：C:/Users/86134/Desktop/workspace/playwright-workspace
"""
import os
import json
import uuid
import asyncio
import subprocess
import re
import webbrowser
import time
import random
from typing import Dict, List, Any, Optional
from datetime import datetime
from pathlib import Path
import aiohttp
import json

from autogen_core import message_handler, type_subscription, MessageContext
from loguru import logger

from app.core.messages.web import PlaywrightExecutionRequest
from app.core.agents.base import BaseAgent
from app.core.types import TopicTypes, AgentTypes, AGENT_NAMES
from app.services.test_report_service import test_report_service
from app.core.config import settings
from .playwright_script_executor_agent_enhancement import PlaywrightExecutorEnhancement


@type_subscription(topic_type=TopicTypes.PLAYWRIGHT_EXECUTOR.value)
class PlaywrightExecutorAgent(BaseAgent):
    """Playwright执行智能体，负责执行MidScene.js + Playwright测试脚本"""

    def __init__(self, model_client_instance=None, **kwargs):
        """初始化Playwright执行智能体"""
        super().__init__(
            agent_id=AgentTypes.PLAYWRIGHT_EXECUTOR.value,
            agent_name=AGENT_NAMES[AgentTypes.PLAYWRIGHT_EXECUTOR.value],
            model_client_instance=model_client_instance,
            **kwargs
        )
        self.execution_records: Dict[str, Dict[str, Any]] = {}
        # 解析并统一确定 Playwright 工作空间（环境变量/配置/示例目录/最终兜底）
        self.playwright_workspace = self._resolve_playwright_workspace()
        
        # 初始化增强执行器
        self.enhancer = PlaywrightExecutorEnhancement(self)

        logger.info(f"Playwright执行智能体初始化完成: {self.agent_name}")
        logger.info(f"执行环境路径: {self.playwright_workspace}")

        # AdsPower 集成开关（只使用指纹浏览器，不回退本地Chromium）
        self.force_adspower_only = os.getenv("FORCE_ADSPOWER_ONLY", "true").lower() == "true"
        # AdsPower 默认本地服务域名按官方为 local.adspower.net
        self.adsp_base_url = os.getenv("ADSP_BASE_URL", "http://local.adspower.net:50325")
        self.adsp_token = os.getenv("ADSP_TOKEN", os.getenv("ADSP_POWER_TOKEN", ""))
        self.adsp_token_param = os.getenv("ADSP_TOKEN_PARAM", "token")
        self.adsp_profile_id = None
        # 🔧 强制删除profile确保每次都是全新环境
        self.adsp_delete_on_exit = os.getenv("ADSP_DELETE_PROFILE_ON_EXIT", "true").lower() == "true"
        self.adsp_ua_auto = os.getenv("ADSP_UA_AUTO", "true").lower() != "false"
        self.adsp_ua_min = int(os.getenv("ADSP_UA_MIN_VERSION", "138"))
        self.adsp_device = os.getenv("ADSP_DEVICE", "desktop")  # desktop/mobile
        self.adsp_fp_raw = os.getenv("ADSP_FP_CONFIG_JSON", "")
        # 批次/分组缓存
        self.batch_id_env_keys = ["EXECUTION_BATCH_ID", "BATCH_ID", "ADSP_BATCH_ID"]
        self.group_cache_file = (self.playwright_workspace / "adspower_groups.json")
        self.adsp_group_required = os.getenv("ADSP_GROUP_REQUIRED", "false").lower() == "true"
        # 路径/字段覆盖与调试
        self.adsp_group_list_path = os.getenv("ADSP_GROUP_LIST_PATH", "").strip()
        self.adsp_group_create_path = os.getenv("ADSP_GROUP_CREATE_PATH", "").strip()
        self.adsp_user_create_path = os.getenv("ADSP_USER_CREATE_PATH", "").strip()
        self.adsp_browser_start_path = os.getenv("ADSP_BROWSER_START_PATH", "").strip()
        self.adsp_group_name_key = os.getenv("ADSP_GROUP_CREATE_NAME_KEY", "").strip()
        self.adsp_user_name_key = os.getenv("ADSP_USER_CREATE_NAME_KEY", "").strip()
        self.adsp_group_key_override = os.getenv("ADSP_GROUP_KEY", "").strip()
        self.adsp_proxy_key_override = os.getenv("ADSP_PROXY_KEY", "").strip()
        self.adsp_fp_key_override = os.getenv("ADSP_FP_KEY", "").strip()
        self.adsp_prefer_v1 = os.getenv("ADSP_PREFER_V1", "false").lower() == "true"
        self.adsp_verbose = os.getenv("ADSP_VERBOSE_LOG", "false").lower() == "true"
        self.adsp_rate_delay_ms = int(os.getenv("ADSP_RATE_LIMIT_DELAY_MS", "1200"))

        # 加载本地非敏感配置（可持久化，无需每次设置）
        try:
            self._load_adspower_local_config()
        except Exception as e:
            logger.warning(f"加载 AdsPower 本地配置失败（忽略继续）: {e}")

        # 读取可选 proxyid（优先环境变量，其次本地配置在 _load_adspower_local_config 中）
        self.adsp_proxy_id: Optional[object] = None
        pid_env = os.getenv("ADSP_PROXY_ID") or os.getenv("ADSP_PROXYID")
        if pid_env:
            try:
                self.adsp_proxy_id = int(pid_env)
            except Exception:
                self.adsp_proxy_id = pid_env

        # AdsPower 并发限流（同进程内最大并发窗口数）
        if not hasattr(PlaywrightExecutorAgent, "adsp_semaphore"):
            try:
                max_conc = int(os.getenv("ADSP_MAX_CONCURRENCY", "15"))
            except Exception:
                max_conc = 15
            PlaywrightExecutorAgent.adsp_max_concurrency = max_conc
            PlaywrightExecutorAgent.adsp_semaphore = asyncio.Semaphore(max_conc)
        self._adsp_slot_acquired: bool = False

    def _load_adspower_local_config(self) -> None:
        """从工作空间下的 adspower.local.json 读取非敏感配置，覆盖默认值。
        仅允许覆盖非敏感项：接口路径/字段名/日志与优先级/退避间隔。
        敏感项（Token/青果认证信息）只允许通过环境变量传入。
        文件位置：<playwright_workspace>/adspower.local.json
        示例：
        {
          "prefer_v1": true,
          "verbose": true,
          "rate_limit_delay_ms": 1500,
          "paths": {
            "group_list": "/api/v1/group/list",
            "group_create": "/api/v1/group/create",
            "user_create": "/api/v1/user/create",
            "browser_start": "/api/v1/browser/start"
          },
          "fields": {
            "group_name_key": "group_name",
            "user_name_key": "user_name",
            "group_key": "group_id",
            "proxy_key": "user_proxy_config",
            "fp_key": "fingerprint_config"
          }
        }
        """
        cfg_path = self.playwright_workspace / "adspower.local.json"
        if not cfg_path.exists():
            return
        raw = cfg_path.read_text(encoding="utf-8")
        data = json.loads(raw)
        # 优先级/日志/退避
        if isinstance(data.get("prefer_v1"), bool):
            self.adsp_prefer_v1 = data["prefer_v1"]
        if isinstance(data.get("verbose"), bool):
            self.adsp_verbose = data["verbose"]
        if isinstance(data.get("rate_limit_delay_ms"), int):
            self.adsp_rate_delay_ms = data["rate_limit_delay_ms"]
        # 路径
        paths = data.get("paths") or {}
        if isinstance(paths.get("group_list"), str) and not self.adsp_group_list_path:
            self.adsp_group_list_path = paths["group_list"].strip()
        if isinstance(paths.get("group_create"), str) and not self.adsp_group_create_path:
            self.adsp_group_create_path = paths["group_create"].strip()
        if isinstance(paths.get("user_create"), str) and not self.adsp_user_create_path:
            self.adsp_user_create_path = paths["user_create"].strip()
        if isinstance(paths.get("browser_start"), str) and not self.adsp_browser_start_path:
            self.adsp_browser_start_path = paths["browser_start"].strip()
        # 字段
        fields = data.get("fields") or {}
        if isinstance(fields.get("group_name_key"), str) and not self.adsp_group_name_key:
            self.adsp_group_name_key = fields["group_name_key"].strip()
        if isinstance(fields.get("user_name_key"), str) and not self.adsp_user_name_key:
            self.adsp_user_name_key = fields["user_name_key"].strip()
        if isinstance(fields.get("group_key"), str) and not self.adsp_group_key_override:
            self.adsp_group_key_override = fields["group_key"].strip()
        if isinstance(fields.get("proxy_key"), str) and not self.adsp_proxy_key_override:
            self.adsp_proxy_key_override = fields["proxy_key"].strip()
        if isinstance(fields.get("fp_key"), str) and not self.adsp_fp_key_override:
            self.adsp_fp_key_override = fields["fp_key"].strip()
        # 读取可选 proxyid 与并发上限（仅当未由环境变量设置时）
        if self.adsp_proxy_id is None:
            proxyid_val = data.get("proxyid")
            if proxyid_val is not None:
                try:
                    self.adsp_proxy_id = int(proxyid_val)
                except Exception:
                    self.adsp_proxy_id = proxyid_val
        max_conc_cfg = data.get("max_concurrency")
        if isinstance(max_conc_cfg, int) and hasattr(PlaywrightExecutorAgent, "adsp_semaphore"):
            # 仅在类属性已初始化的情况下调整阈值
            PlaywrightExecutorAgent.adsp_max_concurrency = max_conc_cfg

    # ====== 辅助：日志与脱敏 ======
    def _mask(self, value: Optional[str], keep: int = 2) -> str:
        try:
            if not value:
                return ""
            v = str(value)
            if len(v) <= keep:
                return "*" * len(v)
            return v[:keep] + "***"
        except Exception:
            return "***"

    def _snippet(self, text: str, limit: int = 200) -> str:
        try:
            return text[:limit]
        except Exception:
            return ""

    def _validate_workspace(self) -> bool:
        """验证Playwright工作空间是否存在且配置正确"""
        try:
            if not self.playwright_workspace.exists():
                logger.error(f"Playwright工作空间不存在: {self.playwright_workspace}")
                return False

            # 检查package.json是否存在
            package_json = self.playwright_workspace / "package.json"
            if not package_json.exists():
                logger.error(f"package.json不存在: {package_json}")
                return False

            # 检查e2e目录是否存在
            e2e_dir = self.playwright_workspace / "e2e"
            if not e2e_dir.exists():
                logger.warning(f"e2e目录不存在，将自动创建: {e2e_dir}")
                e2e_dir.mkdir(exist_ok=True)

            logger.info("Playwright工作空间验证通过")
            return True

        except Exception as e:
            logger.error(f"验证Playwright工作空间失败: {str(e)}")
            return False

    async def _get_existing_script_path(self, script_name: str) -> Path:
        """获取现有脚本文件路径"""
        try:
            # 如果script_name是绝对路径，直接使用
            if os.path.isabs(script_name):
                script_path = Path(script_name)
                if not script_path.exists():
                    raise FileNotFoundError(f"脚本文件不存在: {script_name}")
                logger.info(f"使用绝对路径脚本文件: {script_path}")
                return script_path

            # 否则在e2e目录中查找
            e2e_dir = self.playwright_workspace / "e2e"
            script_path = e2e_dir / script_name

            if not script_path.exists():
                raise FileNotFoundError(f"脚本文件不存在: {script_name}")

            logger.info(f"找到现有脚本文件: {script_path}")
            return script_path

        except Exception as e:
            logger.error(f"获取脚本文件路径失败: {str(e)}")
            raise

    def _resolve_playwright_workspace(self) -> Path:
        """解析 Playwright 工作空间路径。

        优先级：
        1) 环境变量 PLAYWRIGHT_WORKSPACE
        2) 配置 settings.MIDSCENE_SCRIPT_PATH
        3) 项目内示例目录 examples/midscene-playwright
        4) 兜底到历史固定路径 C:\\Users\\86134\\Desktop\\workspace\\playwright-workspace
        """
        try:
            # 1) 环境变量
            env_path = os.getenv("PLAYWRIGHT_WORKSPACE", "").strip()
            if env_path:
                p = Path(env_path)
                if p.exists():
                    return p

            # 2) 配置
            if getattr(settings, "MIDSCENE_SCRIPT_PATH", None):
                cfg = Path(settings.MIDSCENE_SCRIPT_PATH)
                if cfg.exists():
                    return cfg

            # 3) 项目内示例目录（相对定位到 ui-automation/examples/midscene-playwright）
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
            except Exception:
                pass

            # 4) 兜底路径
            return Path(r"C:\\Users\\86134\\Desktop\\workspace\\playwright-workspace")
        except Exception as e:
            logger.warning(f"解析Playwright工作空间失败，使用兜底路径: {e}")
            return Path(r"C:\\Users\\86134\\Desktop\\workspace\\playwright-workspace")

    @message_handler
    async def handle_execution_request(self, message: PlaywrightExecutionRequest, ctx: MessageContext) -> None:
        """处理Playwright执行请求"""
        monitor_id = None
        execution_id = None
        try:
            monitor_id = self.start_performance_monitoring("playwright_execution")
            execution_id = str(uuid.uuid4())

            await self.send_response(f"🚀 开始执行Playwright测试脚本: {execution_id}")

            # 验证工作空间
            if not self._validate_workspace():
                await self.send_error("Playwright工作空间验证失败")
                return

            # 创建执行记录
            self.execution_records[execution_id] = {
                "execution_id": execution_id,
                "status": "running",
                "start_time": datetime.now().isoformat(),
                "script_name": message.script_name,
                "test_content": message.test_content,
                "config": message.execution_config.model_dump() if message.execution_config else {},
                "logs": [],
                "screenshots": [],
                "results": None,
                "error_message": None,
                "playwright_output": None,
                "report_path": None
            }

            # 执行Playwright测试
            execution_result = await self._execute_playwright_test(execution_id, message)

            # 更新执行记录
            self.execution_records[execution_id].update(execution_result)

            # 保存执行记录到数据库
            await self._save_execution_record_to_database(execution_id, message, execution_result)

            # 保存测试报告到数据库
            await self._save_test_report_to_database(execution_id, message, execution_result)

            # 如果有报告路径，尝试在浏览器中打开
            # if execution_result.get("report_path"):
            #     await self._open_report_in_browser(execution_result["report_path"])

            await self.send_response(
                f"✅ Playwright测试执行完成: {execution_result['status']}",
                is_final=True,
                result={
                    "execution_id": execution_id,
                    "execution_result": execution_result,
                    "performance_metrics": self.performance_metrics
                }
            )

            if monitor_id:
                self.end_performance_monitoring(monitor_id)

        except Exception as e:
            if monitor_id:
                self.end_performance_monitoring(monitor_id)
            await self.handle_exception("handle_execution_request", e)

    async def _execute_playwright_test(self, execution_id: str, message: PlaywrightExecutionRequest) -> Dict[str, Any]:
        """执行Playwright测试"""
        try:
            record = self.execution_records[execution_id]

            # 确定测试文件路径
            if message.script_name:
                # 使用指定的脚本文件
                test_file_path = await self._get_existing_script_path(message.script_name)
                logger.info(f"使用现有脚本文件: {test_file_path}")
            else:
                # 创建新的测试文件
                test_file_path = await self._create_test_file(execution_id, message.test_content, message.execution_config or {})
                logger.info(f"创建新测试文件: {test_file_path}")

            # 运行测试
            execution_result = await self._run_playwright_test(test_file_path, execution_id)

            # 解析结果和报告
            parsed_result = self._parse_playwright_result(execution_result)

            # 如果是临时创建的文件，清理它
            # if not message.script_name and message.test_content:
            #     await self._cleanup_test_file(test_file_path)

            return parsed_result

        except Exception as e:
            logger.error(f"执行Playwright测试失败: {str(e)}")
            return {
                "status": "error",
                "end_time": datetime.now().isoformat(),
                "error_message": str(e),
                "duration": 0.0
            }
        finally:
            # 关闭 AdsPower 窗口，按需回收资源
            try:
                await self._adspower_teardown()
            except Exception as _e:
                logger.warning(f"执行结束后的 AdsPower 清理异常: {_e}")

    def _precompute_window_bounds(self, tile_index: int = 0) -> Dict[str, int]:
        """预计算窗口边界，在 AdsPower 创建前就确定 2×5 网格的位置和尺寸。"""
        # 固定 5×2 网格配置（默认设置，不依赖环境变量）
        cols = 5
        rows = 2
        margin = 8
        total_tiles = cols * rows
        
        # 获取屏幕分辨率
        screen = self._get_screen_size_sync()
        bounds = self._calc_tile_bounds(tile_index, total_tiles, screen['w'], screen['h'], cols, rows, margin)
        
        logger.info(f"[预计算窗口] 屏幕={screen['w']}x{screen['h']}, 网格={cols}x{rows}, 格子#{tile_index}")
        logger.info(f"[预计算窗口] 位置=({bounds['left']},{bounds['top']}) 尺寸={bounds['width']}x{bounds['height']}")
        
        return bounds

    def _get_screen_size_sync(self) -> Dict[str, int]:
        """同步获取屏幕尺寸（支持预计算阶段调用）。"""
        try:
            import platform
            if platform.system() == 'Windows':
                import ctypes
                user32 = ctypes.windll.user32
                w = user32.GetSystemMetrics(0)  # SM_CXSCREEN
                h = user32.GetSystemMetrics(1)  # SM_CYSCREEN
                if w > 0 and h > 0:
                    return {"w": w, "h": h}
        except Exception:
            pass
        # 兜底默认值
        return {"w": 1920, "h": 1080}

    async def _adspower_apply_precomputed_bounds(self, ws_endpoint: str, bounds: Dict[str, int]) -> None:
        """将预计算的窗口边界应用到 AdsPower 实例（兜底机制，优先在创建时设置）。"""
        if not ws_endpoint or not bounds:
            return
        try:
            from playwright.async_api import async_playwright
            
            async with async_playwright() as p:
                browser = await p.chromium.connect_over_cdp(ws_endpoint)
                context = browser.contexts[0] if browser.contexts else await browser.new_context()
                page = context.pages[0] if context.pages else await context.new_page()

                # 获取 windowId 并设置边界
                cdp_page = await context.new_cdp_session(page)
                ti = await cdp_page.send('Target.getTargetInfo')
                target_id = (ti.get('targetInfo') or {}).get('targetId') or ti.get('targetId')
                
                if target_id:
                    cdp = await browser.new_browser_cdp_session()
                    
                    # Windows DPI 缩放处理
                    scale = 1.0
                    try:
                        import platform, ctypes
                        if platform.system() == 'Windows':
                            dpi = ctypes.windll.user32.GetDpiForSystem()
                            scale = max(1.0, float(dpi) / 96.0) if dpi else 1.0
                    except Exception:
                        pass
                    
                    bounds_dip = {
                        'left': max(1, int(round(bounds['left'] / scale))),
                        'top': max(1, int(round(bounds['top'] / scale))),
                        'width': max(1, int(round(bounds['width'] / scale))),
                        'height': max(1, int(round(bounds['height'] / scale))),
                    }
                    
                    try:
                        info = await cdp.send('Browser.getWindowForTarget', {'targetId': target_id})
                        window_id = info.get('windowId')
                        
                        if window_id:
                            # 最小化 → 设置尺寸 → 正常显示
                            await cdp.send('Browser.setWindowBounds', {
                                'windowId': window_id,
                                'bounds': {'windowState': 'minimized'}
                            })
                            await asyncio.sleep(0.05)
                            
                            await cdp.send('Browser.setWindowBounds', {
                                'windowId': window_id,
                                'bounds': {
                                    'left': bounds_dip['left'],
                                    'top': bounds_dip['top'],
                                    'width': bounds_dip['width'],
                                    'height': bounds_dip['height'],
                                    'windowState': 'normal'
                                }
                            })
                            
                            logger.info(f"✅ 应用预计算边界: DIP {bounds_dip['left']},{bounds_dip['top']} {bounds_dip['width']}x{bounds_dip['height']}")
                            
                            # 同步 viewport
                            await asyncio.sleep(0.1)
                            inner = await page.evaluate("()=>({w: window.innerWidth, h: window.innerHeight})")
                            if inner and inner.get('w', 0) > 0:
                                await page.set_viewport_size({'width': inner['w'], 'height': inner['h']})
                        else:
                            logger.warning("⚠️ 无法获取 AdsPower 窗口 ID")
                    except Exception as e:
                        logger.warning(f"CDP 窗口边界设置失败: {e}")
                        
        except Exception as e:
            logger.warning(f"应用预计算窗口边界失败: {e}")

    async def _adspower_apply_bounds_via_cdp_ws(self, ws_endpoint: str, bounds: Dict[str, int]) -> bool:
        """不依赖 Playwright，直接通过 CDP WebSocket 设置窗口位置与尺寸，并同步页面 viewport。
        返回是否成功。"""
        if not ws_endpoint or not bounds:
            return False
        try:
            import aiohttp
            import json
            # Windows DPI 缩放
            scale = 1.0
            try:
                import platform, ctypes
                if platform.system() == 'Windows':
                    dpi = ctypes.windll.user32.GetDpiForSystem()
                    scale = max(1.0, float(dpi) / 96.0) if dpi else 1.0
            except Exception:
                pass
            def to_dip(v: int) -> int:
                try:
                    return max(1, int(round(v / scale)))
                except Exception:
                    return v
            b = {
                'left': to_dip(bounds['left']),
                'top': to_dip(bounds['top']),
                'width': to_dip(bounds['width']),
                'height': to_dip(bounds['height']),
            }

            async with aiohttp.ClientSession() as session:
                async with session.ws_connect(ws_endpoint, heartbeat=15) as ws:
                    req_id = 0
                    async def send(method: str, params: Dict[str, Any] = None, session_id: Optional[str] = None) -> Dict[str, Any]:
                        nonlocal req_id
                        req_id += 1
                        payload: Dict[str, Any] = {"id": req_id, "method": method}
                        if params:
                            payload["params"] = params
                        if session_id:
                            payload["sessionId"] = session_id
                        await ws.send_str(json.dumps(payload))
                        # 等待对应的响应
                        while True:
                            msg = await asyncio.wait_for(ws.receive(), timeout=3)
                            if msg.type == aiohttp.WSMsgType.TEXT:
                                data = json.loads(msg.data)
                                if data.get("id") == req_id:
                                    return data.get("result") or {}
                            elif msg.type in (aiohttp.WSMsgType.CLOSE, aiohttp.WSMsgType.CLOSED, aiohttp.WSMsgType.ERROR):
                                raise RuntimeError("WebSocket closed")

                    # 选取一个 page target
                    targets = await send('Target.getTargets')
                    target_id = None
                    for t in targets.get('targetInfos', []):
                        if t.get('type') == 'page':
                            target_id = t.get('targetId')
                            break
                    if not target_id:
                        # 新开一个 about:blank 页面作为定位对象
                        created = await send('Target.createTarget', {"url": "about:blank"})
                        target_id = created.get('targetId')
                    if not target_id:
                        raise RuntimeError('No page target available')

                    # 获取窗口并设置边界
                    info = await send('Browser.getWindowForTarget', {"targetId": target_id})
                    window_id = info.get('windowId')
                    if not window_id:
                        raise RuntimeError('No windowId from Browser.getWindowForTarget')

                    # 先确保 normal 状态
                    try:
                        await send('Browser.setWindowBounds', {"windowId": window_id, "bounds": {"windowState": "normal"}})
                    except Exception:
                        pass
                    await send('Browser.setWindowBounds', {
                        "windowId": window_id,
                        "bounds": {"left": b['left'], "top": b['top'], "width": b['width'], "height": b['height'], "windowState": "normal"}
                    })

                    # 附加到目标，设置设备指标以匹配 viewport
                    attached = await send('Target.attachToTarget', {"targetId": target_id, "flatten": True})
                    session_id = attached.get('sessionId')
                    if session_id:
                        await send('Emulation.setDeviceMetricsOverride', {"width": b['width'], "height": b['height'], "deviceScaleFactor": 1, "mobile": False}, session_id=session_id)
                    # 读取回读值用于日志
                    bb = await send('Browser.getWindowBounds', {"windowId": window_id})
                    logger.info(f"[CDP-WS window] set -> left={bb.get('bounds',{}).get('left')} top={bb.get('bounds',{}).get('top')} w={bb.get('bounds',{}).get('width')} h={bb.get('bounds',{}).get('height')} state={(bb.get('bounds',{}) or {}).get('windowState')}")
            return True
        except Exception as e:
            logger.warning(f"CDP WS 设置窗口失败: {e!r}")
            return False

    async def _prepare_adspower_with_proxy(self) -> Optional[str]:
        """获取青果代理 → 创建/更新 AdsPower Profile → 启动 → 返回 wsEndpoint。
        要求：FORCE_ADSPOWER_ONLY=true 时，失败抛异常；否则返回 None。
        """
        try:
            # 并发限流：最多同时 N 个窗口
            await PlaywrightExecutorAgent.adsp_semaphore.acquire()
            self._adsp_slot_acquired = True
            if self.adsp_verbose:
                logger.info(f"[ADSP concurrency] acquired 1 slot, in_use={PlaywrightExecutorAgent.adsp_max_concurrency - PlaywrightExecutorAgent.adsp_semaphore._value}/{PlaywrightExecutorAgent.adsp_max_concurrency}")

            if not self.adsp_token:
                logger.warning("未配置 ADSP_TOKEN，跳过 AdsPower")
                return None

            # 🎯 关键修复：在方法开始就预计算窗口边界，确保整个方法中都可访问
            window_bounds = self._precompute_window_bounds(0)  # 默认使用第一个格子
            screen_info = self._get_screen_size_sync()

            # 1) 取青果代理（若提供）
            qg_endpoint = os.getenv("QG_TUNNEL_ENDPOINT", "tun-szbhry.qg.net:17790").strip()
            qg_authkey = os.getenv("QG_AUTHKEY", "").strip()
            qg_authpwd = os.getenv("QG_AUTHPWD", "").strip()
            proxy_conf: Optional[Dict[str, Any]] = None
            if qg_endpoint:
                # 解析 host:port
                host = qg_endpoint
                port = None
                if ':' in qg_endpoint:
                    host, port = qg_endpoint.split(':', 1)
                try:
                    port = int(port) if port else 0
                except Exception:
                    port = 0
                proxy_conf = {
                    "proxy_type": "http",
                    "proxy_address": f"{host}:{port}" if port else host,
                    "proxy_host": host,
                    "proxy_port": port,
                }
                if qg_authkey and qg_authpwd:
                    proxy_conf.update({
                        "proxy_username": qg_authkey,
                        "proxy_password": qg_authpwd,
                    })
                masked = f"http://{qg_authkey or ''}:{'***' if qg_authpwd else ''}@{qg_endpoint}"
                logger.info(f"🧩 使用青果隧道代理: {masked}")

            headers = {
                "Content-Type": "application/json",
                # 兼容不同版本：有的用 Bearer，有的用 X-API-KEY
                "Authorization": f"Bearer {self.adsp_token}",
                "X-API-KEY": self.adsp_token,
            }
            if self.adsp_verbose:
                logger.info(f"[ADSP cfg] base_url={self.adsp_base_url} token={self._mask(self.adsp_token, 4)} prefer_v1={self.adsp_prefer_v1} verbose={self.adsp_verbose} rate_delay_ms={self.adsp_rate_delay_ms}")
                
                # 🚀 商用级预防性延迟：避免触发频率限制
                initial_delay = 2.0  # 初始2秒延迟
                logger.info(f"⏰ [AdsPower] 预防性延迟 {initial_delay}s - 避免频率限制")
                await asyncio.sleep(initial_delay)
            async with aiohttp.ClientSession(headers=headers, timeout=aiohttp.ClientTimeout(total=30)) as session:
                # 🧹 清理超限账户（解决15个账户限制问题）
                try:
                    list_resp = await self._adspower_api_call(session, "GET", "/api/v1/user/list?page_size=100")
                    if list_resp and list_resp.get("code") == 0 and list_resp.get("data"):
                        users = list_resp["data"].get("list", [])
                        if len(users) >= 14:  # 接近15个限制时开始清理
                            logger.info(f"🧹 检测到{len(users)}个AdsPower账户，开始清理旧账户...")
                            # 删除最旧的几个账户
                            for user in users[:max(1, len(users) - 10)]:
                                user_id = user.get("user_id")
                                if user_id:
                                    try:
                                        await self._adspower_api_call(session, "DELETE", f"/api/v1/user/delete", {"user_ids": [user_id]})
                                        logger.info(f"🗑️ 已删除旧账户: {user_id}")
                                        await asyncio.sleep(0.5)  # 避免频率限制
                                    except Exception as e:
                                        logger.warning(f"删除账户失败: {e}")
                except Exception as e:
                    logger.warning(f"清理账户失败，继续执行: {e}")

                # 0) 计算/获取 batchId 与对应的分组ID
                batch_id = None
                for k in self.batch_id_env_keys:
                    v = os.getenv(k)
                    if v:
                        batch_id = v
                        break
                if not batch_id:
                    # 若前端没传，自动生成批次ID
                    batch_id = f"batch_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                    os.environ["EXECUTION_BATCH_ID"] = batch_id
                group_id = await self._ensure_adspower_group(session, batch_id)
                if self.adsp_verbose:
                    logger.info(f"[ADSP group] batch_id={batch_id} group_id={group_id or '<none>'}")
                # 2) 创建或更新 Profile（这里简化为创建）
                # 设备与UA策略：强制桌面端，开启 ua_auto（最低版本控制通过 min_version）
                desktop_ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36"
                # 使用预计算的窗口边界，为 AdsPower 提供准确的屏幕尺寸
                
                # 🎯 全新指纹方案：每次创建完全独立的指纹环境
                # 生成随机但真实的硬件指纹
                canvas_fingerprint = f"canvas_{random.randint(100000, 999999)}"
                webgl_vendor = random.choice(["NVIDIA Corporation", "AMD", "Intel Inc."])
                webgl_renderer = random.choice([
                    "NVIDIA GeForce RTX 4090", "NVIDIA GeForce RTX 4080", "NVIDIA GeForce RTX 4070",
                    "AMD Radeon RX 7900 XTX", "AMD Radeon RX 7800 XT", "Intel Arc A770"
                ])
                cpu_cores = random.choice([8, 12, 16, 20, 24])
                memory_gb = random.choice([16, 32, 64])
                
                fp_cfg = {
                    # 🔥 核心配置：最新Chrome内核 + 最强反检测
                    "device_type": "desktop",
                    "ua_auto": True,
                    "ua_min_version": 130,  # 使用最新Chrome版本
                    "ua": desktop_ua,
                    "user_agent": desktop_ua,
                    "platform": "Win32",
                    "os": "win",
                    "os_type": "windows",
                    "system": "windows",
                    "is_mobile": False,
                    "mobile": False,
                    
                    # 🌍 地理位置（AdsPower标准格式）
                    "timezone": "Asia/Shanghai",
                    "language": ["zh-CN", "zh", "en"],  # AdsPower期望的数组格式
                    "languages": ["zh-CN", "zh", "en"],  # 保持一致
                    
                    # 🖥️ 屏幕配置
                    "screen_resolution": f"{screen_info['w']}_{screen_info['h']}",
                    "screen_width": screen_info['w'],
                    "screen_height": screen_info['h'],
                    "window_width": window_bounds['width'],
                    "window_height": window_bounds['height'],
                    "window_left": window_bounds['left'],
                    "window_top": window_bounds['top'],
                    
                    # 🔒 反检测核心配置
                    "webdriver": False,  # 隐藏webdriver特征
                    "automation": False,  # 隐藏自动化特征
                    "headless": False,   # 强制有头模式
                    
                    # 🎨 Canvas/WebGL指纹
                    "canvas_fingerprint": canvas_fingerprint,
                    "webgl_vendor": webgl_vendor,
                    "webgl_renderer": webgl_renderer,
                    "canvas_noise": True,
                    "webgl_noise": True,
                    
                    # 💻 硬件指纹
                    "hardware_concurrency": cpu_cores,
                    "device_memory": memory_gb,
                    "max_touch_points": 0,  # 桌面设备
                    
                    # 🔊 音频指纹
                    "audio_noise": True,
                    "audio_context": True,
                    
                    # 📦 插件和权限
                    "plugins_enabled": True,
                    "permissions": {
                        "geolocation": "default",
                        "notifications": "default", 
                        "camera": "default",
                        "microphone": "default"
                    },
                    
                    # 🚀 性能优化
                    "dns_cache": True,
                    "font_rendering": "natural",
                    "startup_acceleration": True,
                    
                    # ⭐ 关键：每次都是全新Profile，彻底清除状态
                    "fresh_profile": True,  # 标记为全新Profile
                    
                    # 🧹 确保全新状态（根本解决方案）
                    "disable_browser_cache": True,        # 禁用浏览器缓存
                    "disable_local_storage": True,        # 禁用localStorage
                    "disable_session_storage": True,      # 禁用sessionStorage
                    "disable_indexeddb": True,            # 禁用IndexedDB
                    "disable_web_sql": True,              # 禁用WebSQL
                    "disable_application_cache": True,    # 禁用应用缓存
                    "disable_service_workers": True,      # 禁用Service Workers
                    "disable_cookies": False,             # 允许cookies但每次都清新
                    "clear_cookies_on_start": True,       # 启动时清除cookies
                    "clear_history_on_start": True,       # 启动时清除历史记录
                    "private_mode": True,                 # 隐私模式
                    
                    # 🔒 完全隔离的浏览会话
                    "isolated_session": True,             # 完全隔离的会话
                    "no_referrer": True,                  # 无引用者信息
                    "first_party_isolation": True,        # 第一方隔离
                }
                # 用户自定义覆盖
                if self.adsp_fp_raw:
                    try:
                        fp_user = json.loads(self.adsp_fp_raw)
                        fp_cfg.update(fp_user)
                    except Exception:
                        logger.warning("ADSP_FP_CONFIG_JSON 无法解析，忽略")
                # 仅使用 v1 user/create
                create_candidates = []
                if self.adsp_user_create_path:
                    create_candidates.append({
                        "path": self.adsp_user_create_path,
                        "name_keys": [self.adsp_user_name_key] if self.adsp_user_name_key else ["user_name", "name"],
                        "group_keys": [self.adsp_group_key_override] if self.adsp_group_key_override else ["group_id"],
                        "proxy_keys": [self.adsp_proxy_key_override] if self.adsp_proxy_key_override else ["user_proxy_config", "proxy"],
                        "fp_keys": [self.adsp_fp_key_override] if self.adsp_fp_key_override else ["fingerprint_config", "fingerprint"],
                    })
                if not create_candidates:
                    create_candidates = [{
                        "path": "/api/v1/user/create",
                        "name_keys": ["user_name", "name"],
                        "group_keys": ["group_id"],
                        "proxy_keys": ["user_proxy_config", "proxy"],
                        "fp_keys": ["fingerprint_config", "fingerprint"]
                    }]

                created = False
                for cand in create_candidates:
                    try:
                        url = f"{self.adsp_base_url}{cand['path']}?{self.adsp_token_param}={self.adsp_token}"
                        # 组合尝试 name/proxy/fingerprint 的不同键名
                        for name_key in cand["name_keys"]:
                            for proxy_key in cand["proxy_keys"]:
                                for fp_key in cand["fp_keys"]:
                                    # 基础 payload
                                    # 🔧 确保绝对唯一：每次都是完全新的profile，时间戳+UUID确保不会复用
                                    timestamp = int(time.time() * 1000)  # 毫秒级时间戳
                                    unique_id = uuid.uuid4().hex[:8]
                                    payload_base = {
                                        name_key: f"fresh-{timestamp}-{unique_id}"
                                    }
                                    # v2常见要求 email 字段
                                    if cand['path'].startswith('/api/v2/user/create'):
                                        payload_base.setdefault('email', f"auto_{uuid.uuid4().hex[:8]}@example.com")
                                        payload_base.setdefault('password', uuid.uuid4().hex[:12])
                                    if group_id:
                                        for gk in cand["group_keys"]:
                                            payload_base[gk] = group_id

                                    # 🎯 按照官方文档，构建标准请求配置（一次性）
                                    host = (proxy_conf or {}).get('proxy_host') if isinstance(proxy_conf, dict) else None
                                    port = (proxy_conf or {}).get('proxy_port') if isinstance(proxy_conf, dict) else None
                                    username = (proxy_conf or {}).get('proxy_username') if isinstance(proxy_conf, dict) else None
                                    password = (proxy_conf or {}).get('proxy_password') if isinstance(proxy_conf, dict) else None
                                    
                                    # 确保端口是整数
                                    if port and isinstance(port, str):
                                        try:
                                            port = int(port)
                                        except ValueError:
                                            logger.error(f"🚨 [AdsPower] 端口格式错误: {port}")
                                            raise RuntimeError("代理端口格式错误")
                                    
                                    # 🎯 标准AdsPower API格式（严格按照官方文档）
                                    proxy_config = None
                                    if proxy_key == 'user_proxy_config' and host and port and username and password:
                                        proxy_config = {
                                            "proxy_soft": "other",
                                            "proxy_type": "http", 
                                            "proxy_host": str(host),
                                            "proxy_port": int(port),
                                            "proxy_user": str(username),
                                            "proxy_password": str(password)
                                        }
                                    elif self.adsp_proxy_id is not None:
                                        # 使用预设代理ID
                                        proxy_config = {'proxyid': self.adsp_proxy_id}
                                        
                                    if not proxy_config:
                                        logger.error("🚨 [AdsPower] 代理配置不完整，无法创建Profile")
                                        raise RuntimeError("代理配置不完整")
                                    
                                    logger.info(f"🎯 [AdsPower] 标准代理配置: {proxy_config}")
                                    
                                    # 标准指纹配置
                                    fingerprint_config = fp_cfg if fp_cfg else {}

                                    # 🎯 构建最终请求负载（一次性标准请求）
                                    payload = {**payload_base}
                                    if proxy_config:
                                        payload[proxy_key] = proxy_config
                                    if fingerprint_config:
                                        payload[fp_key] = fingerprint_config
                                    
                                    logger.info(f"🚀 [AdsPower] 发送标准API请求: {list(payload.keys())}")
                                    
                                    # 🎯 单次标准API调用（严格按照官方文档）
                                    async with session.post(url, json=payload) as resp:
                                        text = await resp.text()
                                        logger.info(f"[ADSP user.create] url={url} status={resp.status} resp={self._snippet(text)}")
                                        
                                        if resp.status != 200:
                                            logger.error(f"🚨 [AdsPower] HTTP错误: {resp.status}")
                                            raise RuntimeError(f"AdsPower API HTTP错误: {resp.status}")
                                        
                                        if not text:
                                            logger.error("🚨 [AdsPower] 空响应")
                                            raise RuntimeError("AdsPower API返回空响应")
                                        
                                        try:
                                            import json
                                            data = json.loads(text)
                                        except Exception as e:
                                            logger.error(f"🚨 [AdsPower] JSON解析失败: {e}")
                                            raise RuntimeError(f"AdsPower API响应格式错误: {e}")
                                        
                                        code = data.get("code")
                                        if code not in (0, 200):
                                            msg = data.get("msg", "未知错误")
                                            logger.error(f"🚨 [AdsPower] API错误: {msg}")
                                            raise RuntimeError(f"AdsPower API错误: {msg}")
                                        
                                        self.adsp_profile_id = data.get("data", {}).get("user_id") or data.get("data", {}).get("id")
                                        if not self.adsp_profile_id:
                                            logger.error("🚨 [AdsPower] 未返回Profile ID")
                                            raise RuntimeError("AdsPower API未返回有效的Profile ID")
                                        
                                        logger.info(f"✅ [AdsPower] Profile创建成功: {self.adsp_profile_id}")
                                        created = True
                                        break
                    except Exception as e:
                        logger.error(f"🚨 [AdsPower] 创建Profile失败: {e}")
                        continue
                if not created or not self.adsp_profile_id:
                    logger.error("🚨 [AdsPower] 所有配置变体都已尝试，无法创建Profile")
                    raise RuntimeError("创建 AdsPower profile 失败: 频率限制或配置错误")
                # 3) 启动浏览器（仅 v1）
                start_candidates = []
                if self.adsp_browser_start_path:
                    start_candidates.append(f"{self.adsp_base_url}{self.adsp_browser_start_path}?user_id={self.adsp_profile_id}&{self.adsp_token_param}={self.adsp_token}")
                defaults_start = [
                    f"{self.adsp_base_url}/api/v1/browser/start?user_id={self.adsp_profile_id}&{self.adsp_token_param}={self.adsp_token}"
                ]
                start_candidates.extend([u for u in defaults_start if u not in start_candidates])
                ws = None
                for start_url in start_candidates:
                    try:
                        async with session.get(start_url) as resp:
                            text = await resp.text()
                            if self.adsp_verbose:
                                logger.info(f"[ADSP browser.start] url={start_url} status={resp.status} resp={self._snippet(text)}")
                            if resp.status != 200 or not text:
                                continue
                            try:
                                data = json.loads(text)
                            except Exception:
                                continue
                            if data.get("code") not in (0, 200):
                                continue
                            inner = data.get("data", {})
                            ws = inner.get("wsUrl") or inner.get("ws_url") or inner.get("wsEndpoint")
                            if not ws:
                                ws_field = inner.get("ws")
                                if isinstance(ws_field, dict):
                                    ws = ws_field.get("puppeteer") or ws_field.get("playwright") or ws_field.get("cdp") or ws_field.get("ws")
                            if ws:
                                break
                    except Exception:
                        continue
                if not ws:
                    raise RuntimeError("未获得 wsEndpoint")
                # 🎯 单次窗口边界设置（标准化）
                if ws:
                    # 优先使用原生 CDP WS 进行窗口定位，失败回退 Playwright CDP
                    applied = False
                    try:
                        applied = await self._adspower_apply_bounds_via_cdp_ws(ws, window_bounds)
                        logger.info("✅ CDP WS 窗口边界设置成功")
                    except Exception as e:
                        logger.info(f"CDP WS失败，回退Playwright: {e}")
                        try:
                            await self._adspower_apply_precomputed_bounds(ws, window_bounds)
                            applied = True
                            logger.info("✅ Playwright CDP 窗口边界设置成功")
                        except Exception as e:
                            logger.warning(f"窗口边界设置失败: {e}")
                    
                    if applied:
                        logger.info("✅ 预计算窗口边界已应用")
                        
                        # 🎯 确保真正的全新浏览器环境
                        try:
                            import websockets
                            import json
                            
                            # 获取第一个页面的WebSocket
                            resp = await self._adspower_api_call('get', f"{self.adsp_base_url}/api/v1/browser/active", {"user_id": self.adsp_profile_id})
                            if resp.status == 200:
                                data = await resp.json()
                                if data.get("code") == 0:
                                    tabs = data.get("data", {}).get("tabs", [])
                                    if tabs:
                                        page_ws = tabs[0].get("webSocketDebuggerUrl")
                                        if page_ws:
                                            async with websockets.connect(page_ws) as page_websocket:
                                                # 确保桌面端User-Agent
                                                await page_websocket.send(json.dumps({
                                                    "id": 1,
                                                    "method": "Network.setUserAgentOverride",
                                                    "params": {
                                                        "userAgent": desktop_ua,
                                                        "platform": "Win32"
                                                    }
                                                }))
                                                await page_websocket.recv()
                                                
                                                # 确保桌面端设备指标
                                                await page_websocket.send(json.dumps({
                                                    "id": 2,
                                                    "method": "Emulation.setDeviceMetricsOverride",
                                                    "params": {
                                                        "width": window_bounds['width'],
                                                        "height": window_bounds['height'],
                                                        "deviceScaleFactor": 1,
                                                        "mobile": False,
                                                        "fitWindow": False
                                                    }
                                                }))
                                                await page_websocket.recv()
                                                
                                                # 🧹 彻底清除浏览器状态（根本解决方案）
                                                # 清除所有存储
                                                await page_websocket.send(json.dumps({
                                                    "id": 3,
                                                    "method": "Storage.clearDataForOrigin",
                                                    "params": {
                                                        "origin": "*",
                                                        "storageTypes": "all"
                                                    }
                                                }))
                                                await page_websocket.recv()
                                                
                                                # 禁用缓存
                                                await page_websocket.send(json.dumps({
                                                    "id": 4,
                                                    "method": "Network.setCacheDisabled", 
                                                    "params": {"cacheDisabled": True}
                                                }))
                                                await page_websocket.recv()
                                                
                                                # 清除网络状态
                                                await page_websocket.send(json.dumps({
                                                    "id": 5,
                                                    "method": "Network.clearBrowserCache"
                                                }))
                                                await page_websocket.recv()
                                                
                                                logger.info("🧹 已彻底清除浏览器状态，确保全新环境")
                        except Exception as e:
                            logger.warning(f"浏览器状态清除失败: {e}")
                        
                        return ws
            return ws
        except Exception as e:
            logger.error(f"_prepare_adspower_with_proxy 失败: {e}")
            if self.force_adspower_only:
                raise
            return None

    async def _adspower_api_call(self, session: aiohttp.ClientSession, method: str, path: str, data: dict = None) -> Optional[dict]:
        """AdsPower API 统一调用方法"""
        try:
            url = f"{self.adsp_base_url}{path}"
            if "?" not in path:
                url += f"?token={self.adsp_token}"
            else:
                url += f"&token={self.adsp_token}"
            
            if method.upper() == "GET":
                async with session.get(url) as resp:
                    return await resp.json()
            elif method.upper() in ["POST", "DELETE"]:
                async with session.post(url, json=data) as resp:
                    return await resp.json()
        except Exception as e:
            logger.warning(f"AdsPower API调用失败: {method} {path} - {e}")
            return None

    async def _get_screen_size(self) -> Dict[str, int]:
        """获取主显示器尺寸，失败回退 1920x1080。仅 Windows 使用 OS API。"""
        try:
            import ctypes
            user32 = ctypes.windll.user32
            user32.SetProcessDPIAware()
            w = int(user32.GetSystemMetrics(0))
            h = int(user32.GetSystemMetrics(1))
            if w > 0 and h > 0:
                return {"w": w, "h": h}
        except Exception:
            pass
        return {"w": 1920, "h": 1080}

    def _calc_tile_bounds(self, index: int, total: int, screen_w: int, screen_h: int,
                           cols: int = 5, rows: int = 2, margin: int = 8) -> Dict[str, int]:
        """计算 5×2 单屏10宫格中的单格窗口像素位置与尺寸。index 从0开始。"""
        if total <= 0:
            total = 1
        if index < 0:
            index = 0
        if index >= total:
            index = total - 1
        import math
        cell_w = max(200, int((screen_w - (cols + 1) * margin) / cols))
        cell_h = max(150, int((screen_h - (rows + 1) * margin) / rows))
        r = index // cols
        c = index % cols
        left = margin + c * (cell_w + margin)
        top = margin + r * (cell_h + margin)
        return {"left": left, "top": top, "width": cell_w, "height": cell_h}

    async def _adspower_prepare_window(self, ws_endpoint: str) -> None:
        """连接到 AdsPower 实例并进行窗口定型：
        - 将最外层窗口定位到单屏 5×2（可配）网格中的一个单元（像素级）
        - 使页面 viewport 与 window.innerWidth/innerHeight 保持一致
        - 避免“先大后小”闪烁
        可配置环境变量（均为可选）：
        - ADSP_GRID_COLS, ADSP_GRID_ROWS（默认 5×2）
        - ADSP_TILE_INDEX（默认 0）
        - ADSP_TILE_TOTAL（默认 rows*cols）
        - ADSP_MARGIN_PX（默认 8）
        - ADSP_SCREEN_RES（如 1920x1080；若未设置则读取系统分辨率）
        """
        if not ws_endpoint:
            return
        try:
            from playwright.async_api import async_playwright
        except Exception:
            # 若未安装 playwright（后端尺寸预设非必须），直接略过
            return
        try:
            async with async_playwright() as p:
                browser = await p.chromium.connect_over_cdp(ws_endpoint)
                context = browser.contexts[0] if browser.contexts else await browser.new_context()
                # 只复用唯一页，不新开；不 bring_to_front 以降低可见闪动
                page = context.pages[0] if context.pages else await context.new_page()
                # 计算网格与单元像素
                cols = max(1, int(os.getenv("ADSP_GRID_COLS", "5") or 5))
                rows = max(1, int(os.getenv("ADSP_GRID_ROWS", "2") or 2))
                total = int(os.getenv("ADSP_TILE_TOTAL", str(cols * rows)) or cols * rows)
                index = int(os.getenv("ADSP_TILE_INDEX", "0") or 0)
                margin = max(0, int(os.getenv("ADSP_MARGIN_PX", "8") or 8))

                # 屏幕分辨率：优先环境变量，其次系统查询
                env_res = os.getenv("ADSP_SCREEN_RES") or os.getenv("ADSP_MONITOR_RES") or os.getenv("ADSP_RESOLUTION")
                if env_res and ("x" in env_res or "_" in env_res):
                    sep = "x" if "x" in env_res else "_"
                    try:
                        sw, sh = [int(x) for x in env_res.split(sep, 1)]
                        scr = {"w": sw, "h": sh}
                    except Exception:
                        scr = await self._get_screen_size()
                else:
                    scr = await self._get_screen_size()

                # Windows 上 DevTools Browser.setWindowBounds 采用 DIP（device-independent pixels）
                # 若系统缩放不为 100%，需要将像素转换为 DIP
                scale = 1.0
                try:
                    import platform
                    if platform.system() == 'Windows':
                        try:
                            import ctypes
                            # Windows 10+：GetDpiForSystem 可用
                            dpi = ctypes.windll.user32.GetDpiForSystem()
                            scale = max(1.0, float(dpi) / 96.0) if dpi else 1.0
                        except Exception:
                            # 备用：shcore.GetScaleFactorForDevice（返回百分比）
                            try:
                                shcore = ctypes.windll.shcore
                                factor = ctypes.c_int()
                                # PROCESS_PER_MONITOR_DPI_AWARE
                                try:
                                    shcore.SetProcessDpiAwareness(2)
                                except Exception:
                                    pass
                                if shcore.GetScaleFactorForDevice(0, ctypes.byref(factor)) == 0 and factor.value:
                                    scale = max(1.0, float(factor.value) / 100.0)
                            except Exception:
                                scale = 1.0
                except Exception:
                    scale = 1.0

                bounds = self._calc_tile_bounds(index, total, scr['w'], scr['h'], cols, rows, margin)
                # 记录像素与 DIP 的尺寸
                try:
                    logger.info(f"[ADSP screen] px={scr['w']}x{scr['h']} scale={scale:.2f} -> dip={int(scr['w']/scale)}x{int(scr['h']/scale)}")
                    logger.info(f"[ADSP tile(px)] left={bounds['left']} top={bounds['top']} w={bounds['width']} h={bounds['height']}")
                except Exception:
                    pass

                # 转为 DIP
                def _to_dip(v: int) -> int:
                    try:
                        return max(1, int(round(v / scale)))
                    except Exception:
                        return v

                bounds_dip = {
                    'left': _to_dip(bounds['left']),
                    'top': _to_dip(bounds['top']),
                    'width': _to_dip(bounds['width']),
                    'height': _to_dip(bounds['height']),
                }
                try:
                    logger.info(f"[ADSP tile(dip)] left={bounds_dip['left']} top={bounds_dip['top']} w={bounds_dip['width']} h={bounds_dip['height']}")
                except Exception:
                    pass
                # 绑定当前 page 的 targetId，确保定位最外层真实窗口（多策略兜底）
                try:
                    cdp_page = await context.new_cdp_session(page)
                    ti = await cdp_page.send('Target.getTargetInfo')
                    target_id = (ti.get('targetInfo') or {}).get('targetId') or ti.get('targetId')
                    cdp = await browser.new_browser_cdp_session()

                    async def _resolve_window_id() -> int:
                        try:
                            info1 = await cdp.send('Browser.getWindowForTarget', {'targetId': target_id})
                            if info1 and info1.get('windowId'):
                                return info1.get('windowId')
                        except Exception:
                            pass
                        try:
                            info2 = await cdp.send('Browser.getWindowForTarget')
                            if info2 and info2.get('windowId'):
                                return info2.get('windowId')
                        except Exception:
                            pass
                        # 遍历所有 page target 逐一尝试
                        try:
                            tgts = await cdp.send('Target.getTargets')
                            for t in (tgts.get('targetInfos') or []):
                                if t.get('type') == 'page':
                                    try:
                                        info3 = await cdp.send('Browser.getWindowForTarget', {'targetId': t.get('targetId')})
                                        if info3 and info3.get('windowId'):
                                            return info3.get('windowId')
                                    except Exception:
                                        continue
                        except Exception:
                            pass
                        return 0

                    # 🎯 单次获取window ID（无需重试循环）
                    window_id = await _resolve_window_id()
                    if not window_id:
                        # 等待一次后再试
                        await asyncio.sleep(0.1)
                        window_id = await _resolve_window_id()
                    if window_id:
                        # 先最小化→再设定位置尺寸→normal，尽量避免默认大窗可见
                        try:
                            await cdp.send('Browser.setWindowBounds', {
                                'windowId': window_id,
                                'bounds': { 'windowState': 'minimized' }
                            })
                            await asyncio.sleep(0.05)
                        except Exception:
                            pass
                        try:
                            cur = await cdp.send('Browser.getWindowBounds', { 'windowId': window_id })
                            state = (cur.get('bounds') or {}).get('windowState') or cur.get('windowState')
                            if state in ('maximized','fullscreen','minimized'):
                                await cdp.send('Browser.setWindowBounds', { 'windowId': window_id, 'bounds': { 'windowState': 'normal' } })
                                await asyncio.sleep(0.05)
                        except Exception:
                            pass
                        await cdp.send('Browser.setWindowBounds', {
                            'windowId': window_id,
                            'bounds': {
                                'left': bounds_dip['left'], 'top': bounds_dip['top'],
                                'width': bounds_dip['width'], 'height': bounds_dip['height'],
                                'windowState': 'normal'
                            }
                        })
                        try:
                            cur2 = await cdp.send('Browser.getWindowBounds', { 'windowId': window_id })
                            bb = cur2.get('bounds') or {}
                            logger.info(f"[ADSP window] bounds set -> left={bb.get('left')} top={bb.get('top')} w={bb.get('width')} h={bb.get('height')} state={bb.get('windowState')}")
                        except Exception:
                            pass
                        # 🎯 精确同步viewport到窗口内部实际尺寸（关键修复）
                        await page.wait_for_timeout(500)  # 增加等待时间确保窗口稳定
                        
                        # 多次尝试获取精确的内部尺寸
                        inner_w, inner_h = bounds['width'], bounds['height']
                        for attempt in range(3):
                            try:
                                inner = await page.evaluate("""() => ({
                                    w: window.innerWidth,
                                    h: window.innerHeight,
                                    outer_w: window.outerWidth,
                                    outer_h: window.outerHeight,
                                    screen_w: screen.width,
                                    screen_h: screen.height
                                })""")
                                
                                if inner and inner.get('w', 0) > 0 and inner.get('h', 0) > 0:
                                    inner_w = max(1, int(inner.get('w')))
                                    inner_h = max(1, int(inner.get('h')))
                                    logger.info(f"🖥️ [Viewport-{attempt+1}] 获取内部尺寸: {inner_w}x{inner_h}")
                                    logger.info(f"🖥️ [Viewport-{attempt+1}] 外部尺寸: {inner.get('outer_w')}x{inner.get('outer_h')}")
                                    break
                                else:
                                    await page.wait_for_timeout(200)
                            except Exception as e:
                                logger.warning(f"⚠️ [Viewport-{attempt+1}] 获取窗口尺寸失败: {e}")
                                await page.wait_for_timeout(200)
                        
                        # 强制设置viewport匹配实际窗口
                        try:
                            await page.set_viewport_size({'width': inner_w, 'height': inner_h})
                            logger.info(f"✅ [Viewport] 页面视口已设置为: {inner_w}x{inner_h}")
                            
                            # 验证viewport是否正确设置
                            await page.wait_for_timeout(200)
                            actual_viewport = await page.evaluate("() => ({w: window.innerWidth, h: window.innerHeight})")
                            if actual_viewport:
                                logger.info(f"✅ [Viewport] 验证实际视口: {actual_viewport.get('w')}x{actual_viewport.get('h')}")
                        except Exception as e:
                            logger.error(f"❌ [Viewport] 设置失败: {e}")
                        try:
                            cdp_page2 = await context.new_cdp_session(page)
                            await cdp_page2.send('Emulation.setDeviceMetricsOverride', {
                                'width': inner_w,
                                'height': inner_h,
                                'deviceScaleFactor': 1,
                                'mobile': False
                            })
                        except Exception:
                            pass
                except Exception:
                    pass
                try:
                    await browser.close()
                except Exception:
                    pass
        except Exception:
            # 所有异常均忽略，不阻断主流程
            pass

    async def _adspower_teardown(self):
        """关闭 AdsPower 浏览器，按需删除 profile。"""
        try:
            if not self.adsp_profile_id:
                return
            headers = {"Content-Type": "application/json", "Authorization": f"Bearer {self.adsp_token}"}
            async with aiohttp.ClientSession(headers=headers, timeout=aiohttp.ClientTimeout(total=20)) as session:
                # 1) stop（必须）
                stop_url = f"{self.adsp_base_url}/api/v1/browser/stop?user_id={self.adsp_profile_id}&{self.adsp_token_param}={self.adsp_token}"
                try:
                    await session.get(stop_url)
                except Exception:
                    pass
                await asyncio.sleep(0.3)
                # 2) 清缓存（可选，404 忽略）
                try:
                    await session.get(f"{self.adsp_base_url}/api/v1/browser/clear_cache?user_id={self.adsp_profile_id}&{self.adsp_token_param}={self.adsp_token}")
                except Exception:
                    pass
                await asyncio.sleep(0.2)
                # 3) delete（按需）- 单次标准请求
                if self.adsp_delete_on_exit:
                    try:
                        # 🎯 标准AdsPower删除API调用（一次性）
                        delete_url = f"{self.adsp_base_url}/api/v1/user/delete?{self.adsp_token_param}={self.adsp_token}"
                        delete_payload = {"user_ids": [self.adsp_profile_id]}
                        
                        async with session.post(delete_url, json=delete_payload) as resp:
                            txt = await resp.text()
                            try:
                                data = json.loads(txt)
                                code = data.get("code")
                                if code in (0, 200):
                                    logger.info(f"✅ [AdsPower] Profile删除成功: {self.adsp_profile_id}")
                                else:
                                    msg = data.get("msg", "未知错误")
                                    logger.warning(f"⚠️ [AdsPower] 删除失败: {msg}")
                            except Exception as e:
                                logger.warning(f"⚠️ [AdsPower] 删除响应解析失败: {e}")
                    except Exception as e:
                        logger.warning(f"⚠️ [AdsPower] Profile删除异常: {e}")
        except Exception as e:
            logger.warning(f"AdsPower 资源清理失败: {e}")
        finally:
            # 释放并发槽位
            try:
                if self._adsp_slot_acquired:
                    PlaywrightExecutorAgent.adsp_semaphore.release()
                    self._adsp_slot_acquired = False
                    if self.adsp_verbose:
                        logger.info(f"[ADSP concurrency] released 1 slot, in_use={PlaywrightExecutorAgent.adsp_max_concurrency - PlaywrightExecutorAgent.adsp_semaphore._value}/{PlaywrightExecutorAgent.adsp_max_concurrency}")
            except Exception:
                pass

    async def _ensure_adspower_group(self, session: aiohttp.ClientSession, batch_id: str) -> str:
        """确保存在与 batchId 对应的 AdsPower 分组，返回 group_id。并在本地缓存映射。"""
        # 0) 显式指定优先
        env_gid = os.getenv("ADSP_USER_GROUP_ID")
        if env_gid:
            return env_gid
        # 本地缓存优先
        try:
            cache = {}
            if self.group_cache_file.exists():
                cache = json.loads(self.group_cache_file.read_text(encoding='utf-8') or '{}')
            if batch_id in cache:
                return cache[batch_id]
        except Exception:
            pass

        # 仅使用 v1（更稳定）
        list_paths = []
        if self.adsp_group_list_path:
            list_paths.append(self.adsp_group_list_path)
        defaults = [
            "/api/v1/group/list",
            "/api/v1/group/getList",
        ]
        list_paths.extend([p for p in defaults if p not in list_paths])
        for p in list_paths:
            try:
                url = f"{self.adsp_base_url}{p}?{self.adsp_token_param}={self.adsp_token}"
                async with session.get(url) as resp:
                    text = await resp.text()
                    if resp.status != 200 or not text:
                        continue
                    try:
                        data = json.loads(text)
                    except Exception:
                        continue
                    if data.get('code') not in (0, 200):
                        continue
                    groups = data.get('data', []) or data.get('list', [])
                    for g in groups:
                        name = g.get('name') or g.get('group_name')
                        gid = g.get('group_id') or g.get('id')
                        if name == batch_id:
                            self._cache_group(batch_id, gid)
                            return gid
            except Exception:
                continue

        # 不存在则创建（仅 v1）
        create_paths = []
        if self.adsp_group_create_path:
            create_paths.append(self.adsp_group_create_path)
        defaults_create = [
            "/api/v1/group/create",
        ]
        create_paths.extend([p for p in defaults_create if p not in create_paths])
        for p in create_paths:
            # 1) POST JSON 形式（字段名兼容 name / group_name）
            for field_name in ("name", "group_name"):
                try:
                    url = f"{self.adsp_base_url}{p}?{self.adsp_token_param}={self.adsp_token}"
                    use_key = self.adsp_group_name_key or field_name
                    payload = {use_key: batch_id}
                    async with session.post(url, json=payload) as resp:
                        text = await resp.text()
                        if resp.status != 200 or not text:
                            continue
                        try:
                            data = json.loads(text)
                        except Exception:
                            continue
                        if data.get('code') not in (0, 200):
                            continue
                        gid = data.get('data', {}).get('group_id') or data.get('data', {}).get('id')
                        if gid:
                            self._cache_group(batch_id, gid)
                            return gid
                except Exception:
                    continue
            # 2) GET 查询参数形式（很多本地版本接口使用GET）
            for query_key in ("name", "group_name"):
                try:
                    use_key = self.adsp_group_name_key or query_key
                    url = f"{self.adsp_base_url}{p}?{self.adsp_token_param}={self.adsp_token}&{use_key}={batch_id}"
                    async with session.get(url) as resp:
                        text = await resp.text()
                        if resp.status != 200 or not text:
                            continue
                        try:
                            data = json.loads(text)
                        except Exception:
                            continue
                        if data.get('code') not in (0, 200):
                            continue
                        gid = data.get('data', {}).get('group_id') or data.get('data', {}).get('id')
                        if gid:
                            self._cache_group(batch_id, gid)
                            return gid
                except Exception:
                    continue
        if self.adsp_group_required:
            raise RuntimeError("无法创建或获取 AdsPower 分组（请检查 Local API 版本与权限）")
        # 回退：返回一个虚拟分组ID，后续创建 profile 不传 user_group_id
        return ""

    def _cache_group(self, batch_id: str, group_id: str) -> None:
        try:
            cache = {}
            if self.group_cache_file.exists():
                cache = json.loads(self.group_cache_file.read_text(encoding='utf-8') or '{}')
            cache[batch_id] = group_id
            self.group_cache_file.write_text(json.dumps(cache, ensure_ascii=False, indent=2), encoding='utf-8')
        except Exception as e:
            logger.warning(f"写入分组缓存失败: {e}")

    async def _create_test_file(self, execution_id: str, test_content: str,
                              config: Dict[str, Any]) -> Path:
        """在固定工作空间中创建测试文件"""
        try:
            # 确保e2e目录存在
            e2e_dir = self.playwright_workspace / "e2e"
            e2e_dir.mkdir(exist_ok=True)

            # 创建fixture.ts（如果不存在）
            fixture_path = e2e_dir / "fixture.ts"
            if not fixture_path.exists():
                fixture_content = self._generate_fixture_content(config)
                with open(fixture_path, "w", encoding="utf-8") as f:
                    f.write(fixture_content)
                logger.info(f"创建fixture文件: {fixture_path}")

            # 创建测试文件
            test_filename = f"test-{execution_id}.spec.ts"
            test_file_path = e2e_dir / test_filename

            test_file_content = self._generate_test_file(test_content, config)
            with open(test_file_path, "w", encoding="utf-8") as f:
                f.write(test_file_content)

            logger.info(f"创建测试文件: {test_file_path}")
            return test_file_path

        except Exception as e:
            logger.error(f"创建测试文件失败: {str(e)}")
            raise

    def _generate_fixture_content(self, config: Dict[str, Any]) -> str:
        """生成fixture.ts内容"""
        network_idle_timeout = config.get("network_idle_timeout", 2000) if isinstance(config, dict) else getattr(config, "network_idle_timeout", 2000)

        return f"""import {{ test as base }} from '@playwright/test';
import type {{ PlayWrightAiFixtureType }} from '@midscene/web/playwright';
import {{ PlaywrightAiFixture }} from '@midscene/web/playwright';

export const test = base.extend<PlayWrightAiFixtureType>(PlaywrightAiFixture({{
  waitForNetworkIdleTimeout: {network_idle_timeout},
}}));

export {{ expect }} from '@playwright/test';
"""

    def _generate_test_file(self, test_content: str, config: Dict[str, Any]) -> str:
        """生成测试文件内容"""
        base_url = config.get("base_url", "https://example.com") if isinstance(config, dict) else getattr(config, "base_url", "https://example.com")
        
        # 如果test_content是JavaScript代码，直接使用
        if test_content.strip().startswith("import") or "test(" in test_content:
            return test_content
        
        # 否则生成基础的测试模板
        return f"""import {{ expect }} from "@playwright/test";
import {{ test }} from "./fixture";

test.beforeEach(async ({{ page }}) => {{
  await page.goto("{base_url}");
  await page.waitForLoadState("networkidle");
}});

test("AI自动化测试", async ({{ 
  ai, 
  aiQuery, 
  aiAssert,
  aiInput,
  aiTap,
  aiScroll,
  aiWaitFor,
  aiHover,
  aiKeyboardPress
}}) => {{
  {test_content}
}});
"""

    async def _run_playwright_test(self, test_file_path: Path, execution_id: str) -> Dict[str, Any]:
        """运行Playwright测试"""
        try:
            record = self.execution_records[execution_id]
            start_time = datetime.now()

            record["logs"].append("开始执行Playwright测试...")
            await self.send_response("🎭 开始执行Playwright测试...")

            # 构建测试命令 - 使用相对路径，在Windows上转换路径分隔符
            relative_test_path = test_file_path.relative_to(self.playwright_workspace)
            # 在Windows上将反斜杠转换为正斜杠，因为npx playwright期望正斜杠
            import platform
            if platform.system() == "Windows":
                relative_path_str = str(relative_test_path).replace('\\', '/')
            else:
                relative_path_str = str(relative_test_path)
            command = ["npx", "playwright", "test", relative_path_str]

            # 检查是否需要添加 --headed 参数
            config = record.get("config", {})
            if config:
                # 处理不同类型的配置对象
                if hasattr(config, 'headed'):
                    headed = config.headed
                elif isinstance(config, dict):
                    headed = config.get('headed', False)
                else:
                    headed = False

                # 如果配置为有头模式，添加 --headed 参数
                if headed:
                    command.append("--headed")
                    record["logs"].append("启用有头模式（显示浏览器界面）")
                    await self.send_response("🖥️ 启用有头模式（显示浏览器界面）")
                    logger.info("添加 --headed 参数到Playwright命令")

            # 设置环境变量
            env = os.environ.copy()

            # —— 临时禁用AdsPower，使用本地Chromium测试基础功能 ——
            # AdsPower + 青果代理：获取 wsEndpoint 并透传
            try:
                ws_endpoint = await self._prepare_adspower_with_proxy()
                if not ws_endpoint and self.force_adspower_only:
                    raise RuntimeError("AdsPower wsEndpoint 获取失败，且已启用仅AdsPower模式")
                if ws_endpoint:
                    # 窗口边界已在 AdsPower 创建/启动时预设，无需额外处理
                    logger.info(f"✅ AdsPower 窗口已通过预计算边界启动: {ws_endpoint}")
                    env["PW_TEST_CONNECT_WS_ENDPOINT"] = ws_endpoint
                    env["PW_WS_ENDPOINT"] = ws_endpoint
                    logger.info(f"🔌 使用AdsPower浏览器会话: wsEndpoint={ws_endpoint} (已注入 PW_TEST_CONNECT_WS_ENDPOINT 与 PW_WS_ENDPOINT)")
            except Exception as e:
                logger.error(f"AdsPower 初始化失败: {e}")
                if self.force_adspower_only:
                    raise
            
            # 🧠 智能AI模型选择：利用项目的8个顶级AI模型优势
            from app.core.config import settings as app_settings
            from app.tests.test_ai_models import AIModelTester
            
            # 商用级智能选择：自动选择最优AI模型
            logger.info("🧠 启动商用级AI模型智能选择...")
            model_tester = AIModelTester()
            
            try:
                # 快速检测可用模型（简化版，避免影响性能）
                available_models = []
                for model_id, config in model_tester.models_config.items():
                    if config["api_key"] and not config["api_key"].startswith('your-'):
                        available_models.append((model_id, config))
                
                # 按优先级排序，选择最佳模型
                if available_models:
                    available_models.sort(key=lambda x: x[1]["priority"])
                    best_model_id, best_config = available_models[0]
                    
                    logger.info(f"🎯 选择最优AI模型: {best_config['name']}")
                    logger.info(f"📊 优先级: {best_config['priority']}, 性价比: {best_config['cost_rating']}")
                    logger.info(f"🎯 专长: {best_config['use_case']}")
                    
                    # 根据最优模型设置Midscene环境变量
                    if model_id in ["qwen_vl", "qwen"]:
                        selected_provider = "qwen"
                    elif model_id in ["glm_4v"]:
                        selected_provider = "glm"
                    elif model_id in ["deepseek_vl", "deepseek_chat"]:
                        selected_provider = "deepseek"
                    elif model_id == "ui_tars":
                        selected_provider = "ui_tars"
                    elif model_id == "openai_gpt4o":
                        selected_provider = "openai"
                    else:
                        selected_provider = "qwen"  # 默认最优
                        
                else:
                    logger.warning("⚠️ 未找到可用AI模型，使用默认配置")
                    selected_provider = "qwen"
                    
            except Exception as e:
                logger.warning(f"⚠️ AI模型选择失败，使用默认: {e}")
                selected_provider = "qwen"

            def _get_from_settings(k: str) -> str:
                mapping = {
                    'QWEN_API_KEY': getattr(app_settings, 'QWEN_API_KEY', ''),
                    'QWEN_VL_API_KEY': getattr(app_settings, 'QWEN_VL_API_KEY', ''),
                    'GLM_API_KEY': getattr(app_settings, 'GLM_API_KEY', ''),
                    'DEEPSEEK_API_KEY': getattr(app_settings, 'DEEPSEEK_API_KEY', ''),
                    'UI_TARS_API_KEY': getattr(app_settings, 'UI_TARS_API_KEY', ''),
                    'GEMINI_API_KEY': getattr(app_settings, 'GEMINI_API_KEY', ''),
                    'OPENAI_API_KEY': getattr(app_settings, 'OPENAI_API_KEY', ''),
                }
                return mapping.get(k, '') or ''

            ai_key_mappings = {}
            for key in ['QWEN_API_KEY', 'QWEN_VL_API_KEY', 'GLM_API_KEY', 'DEEPSEEK_API_KEY', 'OPENAI_API_KEY', 'UI_TARS_API_KEY', 'GEMINI_API_KEY']:
                env_value = os.getenv(key, '')
                cfg_value = _get_from_settings(key)
                value = env_value or cfg_value
                if value and value.strip() and not value.startswith('your-'):
                    ai_key_mappings[key] = value
                    src = '环境变量' if env_value else '配置文件(settings)'
                    logger.info(f"🔑 使用{src}中的API密钥: {key}")
                else:
                    logger.warning(f"⚠️ API密钥未设置: {key}")
            
            # 添加OpenAI密钥（如果存在）
            openai_key = os.getenv('OPENAI_API_KEY', '') or _get_from_settings('OPENAI_API_KEY')
            if openai_key:
                ai_key_mappings['OPENAI_API_KEY'] = openai_key
                logger.info("🔑 使用环境变量中的OpenAI API密钥")
            
            logger.info("🔍 API密钥映射配置完成")
            
            # 设置有效的API密钥到环境变量
            logger.info("🔍 开始设置AI API密钥到子进程环境变量...")
            for key, value in ai_key_mappings.items():
                try:
                    if value and value.strip() and not value.startswith('your-'):
                        env[key] = value
                        logger.info(f"🔑 设置AI密钥到子进程: {key} = {value[:10]}...")
                    elif key in os.environ and os.environ[key]:
                        env[key] = os.environ[key]
                        logger.info(f"🔑 从环境变量传递AI密钥到子进程: {key}")
                    else:
                        logger.warning(f"⚠️ API密钥未设置: {key}")
                except Exception as e:
                    logger.error(f"❌ 设置API密钥失败 {key}: {e}")
            
            logger.info(f"🔍 API密钥设置完成，共设置 {len([k for k, v in env.items() if k.endswith('_API_KEY')])} 个密钥")
            
            if config:
                # 处理不同类型的配置对象中的环境变量
                env_vars = None
                if hasattr(config, 'environment_variables'):
                    env_vars = config.environment_variables
                elif isinstance(config, dict):
                    env_vars = config.get('environment_variables')

                if env_vars:
                    env.update(env_vars)
                    logger.info(f"添加配置中的环境变量: {list(env_vars.keys())}")

            logger.info(f"执行命令: {' '.join(command)}")
            logger.info(f"工作目录: {self.playwright_workspace}")
            
            # 透传Mock相关环境变量，保障前端能切换到mock配置
            for k in [
                'AI_MOCK_MODE',
                'MIDSCENE_MOCK_BASE_URL',
                'MOCK_API_KEY'
            ]:
                v = os.getenv(k)
                if v is not None:
                    env[k] = v
                    logger.info(f"  透传环境变量: {k}={v}")

            # 如果所有关键密钥均无效，强制回落到 Mock 模式，保障页面一次点击即可跑通
            def _valid(k: str, v: str) -> bool:
                if not v or not v.strip():
                    return False
                if k in ['QWEN_API_KEY', 'QWEN_VL_API_KEY', 'DEEPSEEK_API_KEY']:
                    return v.startswith('sk-') and len(v) > 30
                if k == 'GLM_API_KEY':
                    return '.' in v and len(v) > 40
                if k == 'OPENAI_API_KEY':
                    return (v.startswith('sk-') or v.startswith('sk-proj-')) and len(v) > 30
                return True

            keys_to_check = ['QWEN_VL_API_KEY','QWEN_API_KEY','GLM_API_KEY','DEEPSEEK_API_KEY','OPENAI_API_KEY']
            has_any_valid = any(_valid(k, env.get(k, '')) for k in keys_to_check)
            if not has_any_valid:
                env['AI_MOCK_MODE'] = env.get('AI_MOCK_MODE', 'true') or 'true'
                logger.warning('⚠️ 未检测到任何有效AI密钥，已自动启用 Mock 模式 (AI_MOCK_MODE=true)')

            # 在启动前执行通道预检，仅做连通性校验与日志提示，不强制写入 Provider
            selected_provider = await self._probe_and_select_provider(env)
            if selected_provider:
                logger.info(f"✅ 预检通过，可用Provider: {selected_provider}")
                try:
                    # 使用Midscene标准环境变量，不再使用MIDSCENE_FORCE_*
                    def set_standard_env(backend_name: str, base_url: str, model: str, key_envs: List[str], use_flag: str = None):
                        api_key = None
                        for k in key_envs:
                            if env.get(k):
                                api_key = env.get(k)
                                break
                        
                        if api_key:
                            # 使用Midscene标准环境变量
                            env['OPENAI_API_KEY'] = api_key
                            env['OPENAI_BASE_URL'] = base_url  
                            env['MIDSCENE_MODEL_NAME'] = model
                            env['MIDSCENE_DEBUG_MODE'] = 'true'  # 启用调试模式
                            
                            # 设置特定模型的使用标志
                            if use_flag:
                                env[use_flag] = 'true'
                                
                            # 清空所有冲突的视觉模型设置
                            vision_flags = ['MIDSCENE_USE_VLM_UI_TARS', 'MIDSCENE_USE_GEMINI_VL', 'MIDSCENE_USE_CLAUDE_VL']
                            for flag in vision_flags:
                                if flag != use_flag:
                                    env[flag] = ''
                                
                            logger.info(f"🔧 设置标准AI环境变量: {backend_name}")
                            logger.info(f"   OPENAI_API_KEY = {api_key[:10] if api_key else 'None'}...")
                            logger.info(f"   OPENAI_BASE_URL = {base_url}")
                            logger.info(f"   MIDSCENE_MODEL_NAME = {model}")
                            if use_flag:
                                logger.info(f"   {use_flag} = true")

                    if selected_provider == 'qwen':
                        # 只启用QWEN_VL，明确禁用其他视觉模型
                        set_standard_env('qwen', settings.QWEN_VL_BASE_URL, settings.QWEN_VL_MODEL, ['QWEN_VL_API_KEY', 'QWEN_API_KEY'], 'MIDSCENE_USE_QWEN_VL')
                        # 启用中文UI理解
                        env['MIDSCENE_PREFERRED_LANGUAGE'] = 'zh-CN'
                    elif selected_provider == 'glm':
                        set_standard_env('glm', settings.GLM_BASE_URL, settings.GLM_MODEL, ['GLM_API_KEY'])
                    elif selected_provider == 'deepseek':
                        set_standard_env('deepseek', settings.DEEPSEEK_BASE_URL, 'deepseek-chat', ['DEEPSEEK_API_KEY'])
                    elif selected_provider == 'uitars':
                        set_standard_env('uitars', settings.UI_TARS_BASE_URL, settings.UI_TARS_MODEL, ['UI_TARS_API_KEY'], 'MIDSCENE_USE_VLM_UI_TARS')
                    elif selected_provider == 'openai':
                        set_standard_env('openai', settings.OPENAI_BASE_URL, settings.OPENAI_MODEL, ['OPENAI_API_KEY'])
                    logger.info("🔧 已注入标准环境变量，Midscene将自动识别并使用")
                except Exception as _e:
                    logger.warning(f"注入 MIDSCENE_FORCE_* 失败（忽略）: {_e}")

            # 详细的环境变量调试日志
            logger.info("🔍 Playwright执行环境调试 - 环境变量检查:")
            env_keys_to_check = ['QWEN_VL_API_KEY', 'QWEN_API_KEY', 'GLM_API_KEY', 'DEEPSEEK_API_KEY', 'OPENAI_API_KEY']
            for key in env_keys_to_check:
                value = env.get(key)
                if value:
                    logger.info(f"  {key}: ✅ 存在 ({value[:10]}...)")
                else:
                    logger.info(f"  {key}: ❌ 未设置")
            
            logger.info(f"🔍 Playwright执行调试 - 环境变量总数: {len(env)}")

            # 使用增强执行器进行实时流式执行
            try:
                result = await self.enhancer.execute_with_enhanced_logging(command, execution_id, env)
                return_code = result["return_code"]
                stdout_lines = result["stdout"].splitlines() if result["stdout"] else []
                stderr_lines = result["stderr"].splitlines() if result["stderr"] else []
                
            except Exception as e:
                logger.error(f"增强执行器执行失败，回退到原方法: {e}")
                # 回退到原有的执行方式
                import platform
                if platform.system() == "Windows":
                    try:
                        command_str = ' '.join(command)
                        logger.info(f"Windows执行命令: {command_str}")

                        env_with_utf8 = env.copy()
                        env_with_utf8['PYTHONIOENCODING'] = 'utf-8'
                        env_with_utf8['CHCP'] = '65001'

                        # 在线程中执行以避免阻塞
                        result = await asyncio.to_thread(
                            subprocess.run,
                            command_str,
                            cwd=self.playwright_workspace,
                            capture_output=True,
                            text=True,
                            env=env_with_utf8,
                            timeout=300,
                            shell=True,
                            encoding='utf-8',
                            errors='replace'
                        )

                        return_code = result.returncode
                        stdout_lines = result.stdout.splitlines() if result.stdout else []
                        stderr_lines = result.stderr.splitlines() if result.stderr else []

                        for line in stdout_lines:
                            if line.strip():
                                record["logs"].append(f"[STDOUT] {line}")
                                await self.send_response(f"📝 {line}")
                                logger.info(f"[Playwright] {line}")

                        for line in stderr_lines:
                            if line.strip():
                                record["logs"].append(f"[STDERR] {line}")
                                await self.send_response(f"⚠️ {line}")
                                logger.warning(f"[Playwright Error] {line}")

                    except subprocess.TimeoutExpired:
                        logger.error("Playwright测试执行超时")
                        raise Exception("测试执行超时（5分钟）")
                    except UnicodeDecodeError as e:
                        logger.warning(f"编码错误，尝试使用字节模式: {str(e)}")
                        try:
                            result = await asyncio.to_thread(
                                subprocess.run,
                                command_str,
                                cwd=self.playwright_workspace,
                                capture_output=True,
                                text=False,
                                env=env_with_utf8,
                                timeout=300,
                                shell=True
                            )

                            return_code = result.returncode

                            def safe_decode(byte_data):
                                if not byte_data:
                                    return []
                                try:
                                    return byte_data.decode('utf-8').splitlines()
                                except UnicodeDecodeError:
                                    try:
                                        return byte_data.decode('gbk').splitlines()
                                    except UnicodeDecodeError:
                                        return byte_data.decode('utf-8', errors='replace').splitlines()

                            stdout_lines = safe_decode(result.stdout)
                            stderr_lines = safe_decode(result.stderr)

                        except Exception as inner_e:
                            logger.error(f"字节模式执行也失败: {str(inner_e)}")
                            raise Exception(f"执行失败: {str(inner_e)}")

                    except Exception as e:
                        logger.error(f"Playwright测试执行出错：{str(e)}")
                        raise

            else:
                # 非Windows系统使用异步subprocess
                process = await asyncio.create_subprocess_exec(
                    *command,
                    cwd=self.playwright_workspace,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    env=env
                )

                # 实时读取输出
                stdout_lines = []
                stderr_lines = []

                async def read_stdout():
                    async for line in process.stdout:
                        line_text = line.decode('utf-8').strip()
                        if line_text:
                            stdout_lines.append(line_text)
                            record["logs"].append(f"[STDOUT] {line_text}")
                            await self.send_response(f"📝 {line_text}")
                            logger.info(f"[Playwright] {line_text}")

                async def read_stderr():
                    async for line in process.stderr:
                        line_text = line.decode('utf-8').strip()
                        if line_text:
                            stderr_lines.append(line_text)
                            record["logs"].append(f"[STDERR] {line_text}")
                            await self.send_response(f"⚠️ {line_text}")
                            logger.warning(f"[Playwright Error] {line_text}")

                # 并发读取输出
                await asyncio.gather(read_stdout(), read_stderr())

                # 等待进程完成
                return_code = await process.wait()
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()

            return {
                "return_code": return_code,
                "stdout": stdout_lines,
                "stderr": stderr_lines,
                "duration": duration,
                "start_time": start_time.isoformat(),
                "end_time": end_time.isoformat()
            }

        except Exception as e:
            logger.error(f"运行Playwright测试失败: {str(e)}")
            raise

    async def _probe_and_select_provider(self, env: Dict[str, str]) -> Optional[str]:
        """依次预检通道(Qwen→GLM→DeepSeek→UI-TARS→OpenAI)，返回第一个可用的provider标识。

        返回值: 'qwen' | 'glm' | 'deepseek' | 'uitars' | 'openai' | None
        """
        try:
            candidates: List[Dict[str, str]] = []

            def add_candidate(name: str, key_name: str, base_url: str, model: str):
                api_key = env.get(key_name)
                if api_key and api_key.strip():
                    candidates.append({
                        'name': name,
                        'key_name': key_name,
                        'api_key': api_key,
                        'base_url': base_url.rstrip('/'),
                        'model': model
                    })

            # 构建候选列表（按优先级）
            # 统一为：Qwen-VL → GLM-4V → DeepSeek(chat) → UI-TARS → OpenAI
            add_candidate('qwen', 'QWEN_VL_API_KEY', settings.QWEN_VL_BASE_URL, settings.QWEN_VL_MODEL)
            add_candidate('glm', 'GLM_API_KEY', settings.GLM_BASE_URL, settings.GLM_MODEL)
            add_candidate('deepseek', 'DEEPSEEK_API_KEY', settings.DEEPSEEK_BASE_URL, 'deepseek-chat')
            add_candidate('uitars', 'UI_TARS_API_KEY', settings.UI_TARS_BASE_URL, settings.UI_TARS_MODEL)
            add_candidate('openai', 'OPENAI_API_KEY', settings.OPENAI_BASE_URL, settings.OPENAI_MODEL)

            if not candidates:
                logger.warning("通道预检: 未发现任何可用密钥，跳过预检")
                return None

            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as session:
                for c in candidates:
                    # 统一使用 chat/completions 测试
                    url = f"{c['base_url']}/chat/completions"
                    headers = {
                        'Authorization': f"Bearer {c['api_key']}",
                        'Content-Type': 'application/json'
                    }
                    # DashScope 兼容层可禁用SSE
                    if 'dashscope.aliyuncs.com' in c['base_url']:
                        headers['X-DashScope-SSE'] = 'disable'

                    payload = {
                        'model': c['model'],
                        'messages': [{ 'role': 'user', 'content': 'ping' }],
                        'max_tokens': 5
                    }
                    try:
                        async with session.post(url, headers=headers, json=payload) as resp:
                            text = await resp.text()
                            if resp.status == 200:
                                logger.info(f"通道预检: {c['name']} 可用 ({resp.status})")
                                return c['name']
                            else:
                                logger.warning(f"通道预检: {c['name']} 不可用 HTTP {resp.status}: {text[:120]}")
                    except Exception as e:
                        logger.warning(f"通道预检: {c['name']} 请求失败: {e}")

            return None
        except Exception as e:
            logger.warning(f"通道预检失败(忽略): {e}")
            return None

    def _extract_report_path(self, stdout_lines: List[str]) -> Optional[str]:
        """从stdout中提取报告文件路径"""
        try:
            for line in stdout_lines:
                # 查找 "Midscene - report file updated: ./current_cwd/midscene_run/report/some_id.html"
                if "Midscene - report file updated:" in line:
                    # 使用正则表达式提取路径
                    match = re.search(r'Midscene - report file updated:\s*(.+\.html)', line)
                    if match:
                        report_path = match.group(1).strip()
                        # 如果是相对路径，转换为绝对路径
                        if not os.path.isabs(report_path):
                            if report_path.startswith('./'):
                                report_path = report_path[2:]  # 移除 './'
                            report_path = self.playwright_workspace / report_path

                        logger.info(f"提取到报告路径: {report_path}")
                        return str(report_path)

            return None

        except Exception as e:
            logger.error(f"提取报告路径失败: {str(e)}")
            return None

    def _parse_playwright_result(self, execution_result: Dict[str, Any]) -> Dict[str, Any]:
        """解析Playwright执行结果"""
        try:
            # 基础结果信息
            parsed_result = {
                "status": execution_result.get("status", "failed"),
                "end_time": execution_result.get("end_time", datetime.now().isoformat()),
                "duration": execution_result.get("duration", 0.0),
                "return_code": execution_result.get("return_code", 1),
                "error_message": execution_result.get("error_message"),
                "stdout": execution_result.get("stdout", ""),
                "stderr": execution_result.get("stderr", "")
            }

            # 提取报告路径
            report_path = execution_result.get("report_path")
            if not report_path and execution_result.get("stdout"):
                stdout_data = execution_result["stdout"]
                # 确保传入的是列表格式
                if isinstance(stdout_data, str):
                    stdout_data = stdout_data.split('\n')
                elif not isinstance(stdout_data, list):
                    stdout_data = [str(stdout_data)]
                report_path = self._extract_report_path(stdout_data)

            if report_path:
                parsed_result["report_path"] = report_path
                logger.info(f"找到测试报告: {report_path}")
            else:
                logger.warning("未找到测试报告文件")

            # 解析测试统计信息
            stdout = execution_result.get("stdout", "")
            # 如果stdout是列表，转换为字符串
            if isinstance(stdout, list):
                stdout = "\n".join(str(line) for line in stdout)
            elif not isinstance(stdout, str):
                stdout = str(stdout)

            test_stats = self._extract_test_statistics(stdout)
            parsed_result.update(test_stats)

            return parsed_result

        except Exception as e:
            logger.error(f"解析Playwright结果失败: {str(e)}")
            return {
                "status": "error",
                "end_time": datetime.now().isoformat(),
                "duration": 0.0,
                "return_code": 1,
                "error_message": str(e)
            }

    def _extract_test_statistics(self, stdout: str) -> Dict[str, Any]:
        """从stdout中提取测试统计信息"""
        stats = {
            "total_tests": 0,
            "passed_tests": 0,
            "failed_tests": 0,
            "skipped_tests": 0
        }

        try:
            # 查找测试结果统计
            # 例如: "1 failed", "2 passed", "Running 1 test using 1 worker"
            import re

            # 提取运行的测试数量
            running_match = re.search(r'Running (\d+) test', stdout)
            if running_match:
                stats["total_tests"] = int(running_match.group(1))

            # 提取失败的测试数量
            failed_match = re.search(r'(\d+) failed', stdout)
            if failed_match:
                stats["failed_tests"] = int(failed_match.group(1))

            # 提取通过的测试数量
            passed_match = re.search(r'(\d+) passed', stdout)
            if passed_match:
                stats["passed_tests"] = int(passed_match.group(1))

            # 如果没有明确的通过数量，计算通过数量
            if stats["passed_tests"] == 0 and stats["total_tests"] > 0:
                stats["passed_tests"] = stats["total_tests"] - stats["failed_tests"] - stats["skipped_tests"]

        except Exception as e:
            logger.warning(f"提取测试统计信息失败: {str(e)}")

        return stats

    async def _open_report_in_browser(self, report_path: str) -> None:
        """在浏览器中打开报告"""
        try:
            if os.path.exists(report_path):
                # 转换为file:// URL
                file_url = f"file:///{report_path.replace(os.sep, '/')}"
                webbrowser.open(file_url)
                await self.send_response(f"📊 已在浏览器中打开测试报告: {report_path}")
                logger.info(f"已在浏览器中打开报告: {file_url}")
            else:
                await self.send_warning(f"报告文件不存在: {report_path}")

        except Exception as e:
            logger.error(f"打开报告失败: {str(e)}")
            await self.send_warning(f"无法打开报告: {str(e)}")

    async def _collect_playwright_reports(self) -> List[str]:
        """收集Playwright报告文件"""
        try:
            reports = []

            # 查找HTML报告
            report_dirs = [
                self.playwright_workspace / "playwright-report",
                self.playwright_workspace / "test-results",
                self.playwright_workspace / "midscene_run" / "report"
            ]

            for report_dir in report_dirs:
                if report_dir.exists():
                    for file_path in report_dir.rglob("*.html"):
                        reports.append(str(file_path))
                    for file_path in report_dir.rglob("*.json"):
                        reports.append(str(file_path))

            return reports

        except Exception as e:
            logger.error(f"收集Playwright报告失败: {str(e)}")
            return []

    async def _collect_test_artifacts(self) -> Dict[str, List[str]]:
        """收集测试产物（截图、视频等）"""
        try:
            artifacts = {
                "screenshots": [],
                "videos": []
            }

            # 查找测试结果目录
            test_results_dir = self.playwright_workspace / "test-results"
            if test_results_dir.exists():
                # 收集截图
                for file_path in test_results_dir.rglob("*.png"):
                    artifacts["screenshots"].append(str(file_path))

                # 收集视频
                for file_path in test_results_dir.rglob("*.webm"):
                    artifacts["videos"].append(str(file_path))

            return artifacts

        except Exception as e:
            logger.error(f"收集测试产物失败: {str(e)}")
            return {"screenshots": [], "videos": []}

    async def _parse_test_results(self, stdout_lines: List[str]) -> Dict[str, Any]:
        """解析测试结果"""
        try:
            results = {
                "total_tests": 0,
                "passed_tests": 0,
                "failed_tests": 0,
                "skipped_tests": 0,
                "success_rate": 0.0,
                "test_details": []
            }

            # 解析Playwright输出
            for line in stdout_lines:
                # 解析测试总数
                if "Running" in line and "test" in line:
                    import re
                    match = re.search(r'(\d+)\s+test', line)
                    if match:
                        results["total_tests"] = int(match.group(1))

                # 解析通过的测试
                if "passed" in line.lower():
                    import re
                    match = re.search(r'(\d+)\s+passed', line)
                    if match:
                        results["passed_tests"] = int(match.group(1))

                # 解析失败的测试
                if "failed" in line.lower():
                    import re
                    match = re.search(r'(\d+)\s+failed', line)
                    if match:
                        results["failed_tests"] = int(match.group(1))

                # 解析跳过的测试
                if "skipped" in line.lower():
                    import re
                    match = re.search(r'(\d+)\s+skipped', line)
                    if match:
                        results["skipped_tests"] = int(match.group(1))

            # 计算成功率
            if results["total_tests"] > 0:
                results["success_rate"] = results["passed_tests"] / results["total_tests"]

            return results

        except Exception as e:
            logger.error(f"解析测试结果失败: {str(e)}")
            return {
                "total_tests": 0,
                "passed_tests": 0,
                "failed_tests": 0,
                "skipped_tests": 0,
                "success_rate": 0.0,
                "test_details": []
            }

    async def _cleanup_test_file(self, test_file_path: Path):
        """清理测试文件"""
        try:
            if test_file_path.exists():
                test_file_path.unlink()
                logger.info(f"清理测试文件: {test_file_path}")
        except Exception as e:
            logger.warning(f"清理测试文件失败: {str(e)}")

    async def _find_default_report_path(self, execution_id: str) -> Optional[str]:
        """查找默认位置的报告文件"""
        try:
            # 可能的报告路径
            possible_paths = [
                self.playwright_workspace / "midscene_run" / "report" / f"{execution_id}.html",
                self.playwright_workspace / "midscene_run" / "report" / "index.html",
                self.playwright_workspace / "playwright-report" / "index.html",
                self.playwright_workspace / "test-results" / "index.html",
            ]

            for path in possible_paths:
                if path.exists():
                    logger.info(f"在默认位置找到报告文件: {path}")
                    return str(path)

            # 如果没有找到，尝试搜索最新的HTML文件
            report_dirs = [
                self.playwright_workspace / "midscene_run" / "report",
                self.playwright_workspace / "playwright-report",
                self.playwright_workspace / "test-results",
            ]

            for report_dir in report_dirs:
                if report_dir.exists():
                    html_files = list(report_dir.glob("*.html"))
                    if html_files:
                        # 按修改时间排序，取最新的
                        latest_file = max(html_files, key=lambda f: f.stat().st_mtime)
                        logger.info(f"找到最新的报告文件: {latest_file}")
                        return str(latest_file)

            logger.warning(f"未找到执行 {execution_id} 的报告文件")
            return None

        except Exception as e:
            logger.error(f"查找默认报告路径失败: {str(e)}")
            return None

    def _get_report_extraction_util(self) -> str:
        """获取报告路径提取的Python代码示例"""
        return '''
# 报告路径提取示例代码
import re
import os
from pathlib import Path

def extract_report_path_from_output(stdout_lines):
    """从Playwright输出中提取报告路径"""
    for line in stdout_lines:
        if "Midscene - report file updated:" in line:
            match = re.search(r'Midscene - report file updated:\\s*(.+\\.html)', line)
            if match:
                report_path = match.group(1).strip()
                if not os.path.isabs(report_path):
                    if report_path.startswith('./'):
                        report_path = report_path[2:]
                    # 转换为绝对路径
                    workspace = Path(r"C:\\Users\\86134\\Desktop\\workspace\\playwright-workspace")
                    report_path = workspace / report_path
                return str(report_path)
    return None

# 使用示例
# report_path = extract_report_path_from_output(stdout_lines)
# if report_path:
#     import webbrowser
#     webbrowser.open(f"file:///{report_path.replace(os.sep, '/')}")
'''

    async def process_message(self, message: Any, ctx: MessageContext) -> None:
        """处理消息的统一入口"""
        if isinstance(message, PlaywrightExecutionRequest):
            await self.handle_execution_request(message, ctx)
        else:
            logger.warning(f"Playwright执行智能体收到未知消息类型: {type(message)}")

    def get_execution_status(self, execution_id: str) -> Optional[Dict[str, Any]]:
        """获取执行状态"""
        return self.execution_records.get(execution_id)

    def list_executions(self) -> List[Dict[str, Any]]:
        """列出所有执行记录"""
        return list(self.execution_records.values())

    async def get_latest_report_path(self) -> Optional[str]:
        """获取最新的测试报告路径"""
        try:
            report_dir = self.playwright_workspace / "midscene_run" / "report"
            if not report_dir.exists():
                return None

            # 查找最新的HTML报告文件
            html_files = list(report_dir.glob("*.html"))
            if not html_files:
                return None

            # 按修改时间排序，获取最新的
            latest_file = max(html_files, key=lambda f: f.stat().st_mtime)
            return str(latest_file)

        except Exception as e:
            logger.error(f"获取最新报告路径失败: {str(e)}")
            return None

    async def open_latest_report(self) -> bool:
        """打开最新的测试报告"""
        try:
            report_path = await self.get_latest_report_path()
            if report_path:
                await self._open_report_in_browser(report_path)
                return True
            else:
                await self.send_warning("未找到测试报告文件")
                return False

        except Exception as e:
            logger.error(f"打开最新报告失败: {str(e)}")
            await self.send_error(f"打开报告失败: {str(e)}")
            return False

    def get_workspace_info(self) -> Dict[str, Any]:
        """获取工作空间信息"""
        try:
            workspace_info = {
                "workspace_path": str(self.playwright_workspace),
                "workspace_exists": self.playwright_workspace.exists(),
                "e2e_dir_exists": (self.playwright_workspace / "e2e").exists(),
                "package_json_exists": (self.playwright_workspace / "package.json").exists(),
                "recent_test_files": [],
                "recent_reports": []
            }

            # 获取最近的测试文件
            e2e_dir = self.playwright_workspace / "e2e"
            if e2e_dir.exists():
                test_files = list(e2e_dir.glob("*.spec.ts"))
                workspace_info["recent_test_files"] = [str(f) for f in test_files[-5:]]

            # 获取最近的报告
            report_dir = self.playwright_workspace / "midscene_run" / "report"
            if report_dir.exists():
                report_files = list(report_dir.glob("*.html"))
                workspace_info["recent_reports"] = [str(f) for f in report_files[-5:]]

            return workspace_info

        except Exception as e:
            logger.error(f"获取工作空间信息失败: {str(e)}")
            return {"error": str(e)}

    async def _save_execution_record_to_database(
        self,
        execution_id: str,
        message: PlaywrightExecutionRequest,
        execution_result: Dict[str, Any]
    ) -> None:
        """保存执行记录到数据库"""
        try:
            from app.database.connection import db_manager
            from app.database.models.executions import ScriptExecution
            from app.database.models.scripts import TestScript

            record = self.execution_records.get(execution_id, {})

            # 提取脚本信息
            script_id = getattr(message, 'script_id', None) or message.script_name or execution_id

            # 解析时间信息
            start_time = None
            end_time = None
            if record.get("start_time"):
                try:
                    start_time = datetime.fromisoformat(record["start_time"])
                except:
                    pass
            if execution_result.get("end_time"):
                try:
                    end_time = datetime.fromisoformat(execution_result["end_time"])
                except:
                    pass

            # 计算执行时长（秒）
            duration_seconds = None
            if start_time and end_time:
                duration_seconds = int((end_time - start_time).total_seconds())
            elif execution_result.get("duration"):
                duration_seconds = int(execution_result["duration"])

            # 确定执行状态 - 与TestReport保持一致的逻辑
            return_code = execution_result.get("return_code", 1)
            explicit_status = execution_result.get("status", "")

            logger.info(f"状态映射调试 - return_code: {return_code}, explicit_status: '{explicit_status}'")

            if return_code == 0:
                status = "completed"  # 成功执行
            else:
                status = "failed"     # 执行失败

            # 如果有明确的status字段，也考虑进去
            if explicit_status == "success":
                status = "completed"
            elif explicit_status in ["pending", "running", "cancelled"]:
                status = explicit_status

            logger.info(f"最终状态映射结果: {status}")

            # 安全序列化配置信息
            safe_execution_config = {}
            safe_environment_info = {}

            try:
                if record.get("config"):
                    config = record["config"]
                    # 如果是Pydantic模型，转换为字典
                    if hasattr(config, 'model_dump'):
                        safe_execution_config = config.model_dump()
                    elif hasattr(config, 'dict'):
                        safe_execution_config = config.dict()
                    elif isinstance(config, dict):
                        safe_execution_config = config
                    else:
                        safe_execution_config = {}

                # 添加脚本信息到配置中
                safe_execution_config["script_name"] = record.get("script_name", message.script_name)
                safe_execution_config["script_type"] = "playwright"  # 明确设置脚本类型

            except Exception as e:
                logger.warning(f"序列化执行配置失败: {str(e)}")

            try:
                if execution_result.get("environment"):
                    env = execution_result["environment"]
                    # 如果是Pydantic模型，转换为字典
                    if hasattr(env, 'model_dump'):
                        safe_environment_info = env.model_dump()
                    elif hasattr(env, 'dict'):
                        safe_environment_info = env.dict()
                    elif isinstance(env, dict):
                        safe_environment_info = env
                    else:
                        safe_environment_info = {}
            except Exception as e:
                logger.warning(f"序列化环境信息失败: {str(e)}")

            # 创建执行记录
            db_execution = ScriptExecution(
                script_id=script_id,
                execution_id=execution_id,
                status=status,
                execution_config=safe_execution_config,
                environment_info=safe_environment_info,
                start_time=start_time,
                end_time=end_time,
                duration_seconds=duration_seconds,
                error_message=execution_result.get("error_message") or record.get("error_message"),
                exit_code=execution_result.get("return_code", 0),
                performance_metrics={}
            )

            # 保存到MySQL数据库
            async with db_manager.get_session() as session:
                session.add(db_execution)
                await session.commit()
                await session.refresh(db_execution)
                logger.info(f"执行记录已保存到MySQL: {db_execution.id} - {script_id}")

        except Exception as e:
            logger.error(f"保存执行记录失败: {str(e)}")

    async def _save_test_report_to_database(self, execution_id: str, message: PlaywrightExecutionRequest, execution_result: Dict[str, Any]) -> None:
        """保存测试报告到数据库"""
        try:
            record = self.execution_records.get(execution_id, {})

            # 提取脚本信息
            script_id = getattr(message, 'script_id', None) or message.script_name or execution_id
            script_name = message.script_name or f"test-{execution_id}"
            session_id = getattr(message, 'session_id', execution_id)

            # 解析时间信息
            start_time = None
            end_time = None
            if record.get("start_time"):
                try:
                    start_time = datetime.fromisoformat(record["start_time"])
                except:
                    pass
            if execution_result.get("end_time"):
                try:
                    end_time = datetime.fromisoformat(execution_result["end_time"])
                except:
                    pass

            # 确定执行状态
            status = execution_result.get("status", "unknown")
            if execution_result.get("return_code") == 0:
                status = "passed"
            elif execution_result.get("return_code") != 0:
                status = "failed"

            # 提取报告路径和生成访问URL
            report_path = execution_result.get("report_path")
            report_url = None
            if report_path:
                # 生成报告访问URL
                report_url = f"/api/v1/web/reports/view/{execution_id}"
                logger.info(f"生成报告访问URL: {report_url} -> {report_path}")

            # 安全转换配置对象
            safe_execution_config = record.get("config", {})
            safe_environment_variables = {}

            # 安全提取环境变量
            if message.execution_config and hasattr(message.execution_config, 'environment_variables'):
                env_vars = message.execution_config.environment_variables
                if env_vars:
                    if isinstance(env_vars, dict):
                        safe_environment_variables = env_vars
                    elif hasattr(env_vars, 'dict'):
                        safe_environment_variables = env_vars.dict()
                    elif hasattr(env_vars, 'model_dump'):
                        safe_environment_variables = env_vars.model_dump()
                    else:
                        safe_environment_variables = {"raw_env_vars": str(env_vars)}

            # 保存报告
            saved_report = await test_report_service.save_test_report(
                script_id=script_id,
                script_name=script_name,
                session_id=session_id,
                execution_id=execution_id,
                status=status,
                return_code=execution_result.get("return_code", 0),
                start_time=start_time,
                end_time=end_time,
                duration=execution_result.get("duration", 0.0),
                logs=record.get("logs", []),
                execution_config=safe_execution_config,
                environment_variables=safe_environment_variables,
                # 传递报告路径和URL
                report_path=report_path,
                report_url=report_url
            )

            if saved_report:
                logger.info(f"测试报告已保存到数据库: {saved_report.id}")
                if report_url:
                    await self.send_response(f"📊 测试报告已保存: ID {saved_report.id}, 访问地址: {report_url}")
                else:
                    await self.send_response(f"📊 测试报告已保存: ID {saved_report.id}")
            else:
                logger.warning("保存测试报告到数据库失败")

        except Exception as e:
            logger.error(f"保存测试报告到数据库失败: {str(e)}")
            # 不抛出异常，避免影响主流程
