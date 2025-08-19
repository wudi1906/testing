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
from typing import Dict, List, Any, Optional
from datetime import datetime
from pathlib import Path
import aiohttp
import json as _json

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
        self.adsp_delete_on_exit = os.getenv("ADSP_DELETE_PROFILE_ON_EXIT", "false").lower() == "true"
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
            async with aiohttp.ClientSession(headers=headers, timeout=aiohttp.ClientTimeout(total=30)) as session:
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
                fp_cfg = {
                    "language": "zh-CN",
                    "timezone": "Asia/Shanghai",
                    "device_type": "desktop",
                    "ua_auto": True,
                    "ua_min_version": max(self.adsp_ua_min, 138),
                    "screen_resolution": "1920x1080",
                    "screen_width": 1920,
                    "screen_height": 1080,
                    "platform": "Win32",
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
                                    payload_base = {
                                        name_key: f"ui-auto-{batch_id}-{uuid.uuid4().hex[:6]}"
                                    }
                                    # v2常见要求 email 字段
                                    if cand['path'].startswith('/api/v2/user/create'):
                                        payload_base.setdefault('email', f"auto_{uuid.uuid4().hex[:8]}@example.com")
                                        payload_base.setdefault('password', uuid.uuid4().hex[:12])
                                    if group_id:
                                        for gk in cand["group_keys"]:
                                            payload_base[gk] = group_id

                                    # 生成多种代理形态
                                    proxy_variants = []
                                    # 如果提供了 proxyid，则优先走 proxyid 直连（更稳）
                                    if self.adsp_proxy_id is not None:
                                        proxy_variants.append({ 'proxyid': self.adsp_proxy_id })
                                    host = (proxy_conf or {}).get('proxy_host') if isinstance(proxy_conf, dict) else None
                                    port = (proxy_conf or {}).get('proxy_port') if isinstance(proxy_conf, dict) else None
                                    username = (proxy_conf or {}).get('proxy_username') if isinstance(proxy_conf, dict) else None
                                    password = (proxy_conf or {}).get('proxy_password') if isinstance(proxy_conf, dict) else None
                                    address = (proxy_conf or {}).get('proxy_address') if isinstance(proxy_conf, dict) else None
                                    proxy_url = None
                                    if host and port:
                                        proxy_url = f"http://{host}:{port}"
                                        if username and password:
                                            proxy_url = f"http://{username}:{password}@{host}:{port}"
                                    elif address:
                                        proxy_url = f"http://{address}"
                                        if username and password:
                                            proxy_url = f"http://{username}:{password}@{address}"

                                    # 优先：v1 常见格式（user_proxy_config 包含 proxy_soft/proxy_type/proxy）
                                    if proxy_key == 'user_proxy_config':
                                        # 无 scheme
                                        if host and port:
                                            addr_no_scheme = f"{host}:{port}"
                                            if username and password:
                                                addr_no_scheme = f"{username}:{password}@{host}:{port}"
                                            proxy_variants.append({
                                                proxy_key: {
                                                    "proxy_soft": "other",
                                                    "proxy_type": "http",
                                                    "proxy": addr_no_scheme
                                                }
                                            })
                                        # 有 scheme
                                        if proxy_url:
                                            proxy_variants.append({
                                                proxy_key: {
                                                    "proxy_soft": "other",
                                                    "proxy_type": "http",
                                                    "proxy": proxy_url
                                                }
                                            })

                                    # 次优先：对象结构（proxy_* 键）
                                    if proxy_conf and proxy_key != 'proxy':
                                        variant2 = {
                                            proxy_key: {
                                                "proxy_type": (proxy_conf or {}).get('proxy_type', 'http'),
                                                "proxy_host": host,
                                                "proxy_port": port,
                                                "proxy_username": username,
                                                "proxy_password": password,
                                            }
                                        }
                                        for rk in list(variant2[proxy_key].keys()):
                                            if variant2[proxy_key][rk] is None:
                                                del variant2[proxy_key][rk]
                                        if variant2[proxy_key]:
                                            proxy_variants.append(variant2)

                                        # 变体：使用 proxy_user 字段名（部分版本要求）
                                        variant2b = {
                                            proxy_key: {
                                                "proxy_type": (proxy_conf or {}).get('proxy_type', 'http'),
                                                "proxy_host": host,
                                                "proxy_port": port,
                                                "proxy_user": username,
                                                "proxy_password": password,
                                            }
                                        }
                                        for rk in list(variant2b[proxy_key].keys()):
                                            if variant2b[proxy_key][rk] is None:
                                                del variant2b[proxy_key][rk]
                                        if variant2b[proxy_key]:
                                            proxy_variants.append(variant2b)

                                        # 变体：在对象结构上附加 proxy_soft='other'（本地一些版本要求）
                                        variant2c = {
                                            proxy_key: {
                                                "proxy_soft": "other",
                                                "proxy_type": (proxy_conf or {}).get('proxy_type', 'http'),
                                                "proxy_host": host,
                                                "proxy_port": port,
                                                "proxy_user": username if username is not None else None,
                                                "proxy_password": password if password is not None else None,
                                            }
                                        }
                                        # 清理 None
                                        for rk in list(variant2c[proxy_key].keys()):
                                            if variant2c[proxy_key][rk] is None:
                                                del variant2c[proxy_key][rk]
                                        if variant2c[proxy_key]:
                                            proxy_variants.append(variant2c)

                                    # 备选：对象结构（通用键）
                                    if proxy_conf and proxy_key != 'proxy':
                                        variant1 = {
                                            proxy_key: {
                                                "type": (proxy_conf or {}).get('proxy_type', 'http'),
                                                "host": host,
                                                "port": port,
                                                "username": username,
                                                "password": password,
                                            }
                                        }
                                        for rk in list(variant1[proxy_key].keys()):
                                            if variant1[proxy_key][rk] is None:
                                                del variant1[proxy_key][rk]
                                        if variant1[proxy_key]:
                                            proxy_variants.append(variant1)

                                    # 备选：对象结构（内含 proxy 字符串）
                                    if proxy_url and proxy_key != 'proxy':
                                        proxy_variants.append({ proxy_key: { "proxy_type": "http", "proxy": proxy_url } })
                                        # 无 scheme 形式（host:port）
                                        no_scheme = None
                                        if host and port:
                                            no_scheme = f"{host}:{port}"
                                            if username and password:
                                                no_scheme = f"{username}:{password}@{host}:{port}"
                                        if no_scheme:
                                            proxy_variants.append({ proxy_key: { "proxy_type": "HTTP", "proxy": no_scheme } })

                                    # 备选：字符串（当 key 为 proxy）
                                    if proxy_key == 'proxy' and proxy_url:
                                        proxy_variants.append({ proxy_key: proxy_url })

                                    # 备选：v1 另一常见格式（user_proxy_config 使用 ip/port/user/password）
                                    if proxy_key == 'user_proxy_config' and host and port:
                                        proxy_variants.append({
                                            proxy_key: {
                                                "ip": host,
                                                "port": port,
                                                "user": username,
                                                "password": password
                                            }
                                        })

                                    # 指纹配置
                                    fp_variants = []
                                    if fp_cfg:
                                        fp_variants.append({ fp_key: fp_cfg })
                                    if not fp_variants:
                                        fp_variants.append({})
                                    if not proxy_variants:
                                        proxy_variants.append({})

                                    # 逐一尝试，并对429/限流退避
                                    for pv in proxy_variants:
                                        for fv in fp_variants:
                                            attempts = 0
                                            while attempts < 3:
                                                payload = { **payload_base, **pv, **fv }
                                                async with session.post(url, json=payload) as resp:
                                                    text = await resp.text()
                                                    if self.adsp_verbose:
                                                        logger.info(f"[ADSP user.create] url={url} name_key={name_key} group_keys={cand['group_keys']} proxy_key={proxy_key} fp_key={fp_key} status={resp.status} resp={self._snippet(text)} payload_keys={list(payload.keys())}")
                                                    # BEGIN: console prints for first/last lines
                                                    try:
                                                        _uc_line = f"[ADSP user.create] url={url} name_key={name_key} group_keys={cand['group_keys']} proxy_key={proxy_key} fp_key={fp_key} status={resp.status} resp={self._snippet(text)} payload_keys={list(payload.keys())}"
                                                        if '___FIRST_UC_PRINTED' not in locals():
                                                            print(_uc_line)
                                                            ___FIRST_UC_PRINTED = True
                                                        ___LAST_UC_LINE = _uc_line
                                                    except Exception:
                                                        pass
                                                    # END: console prints for first/last lines
                                                    if resp.status != 200 or not text:
                                                        attempts += 1
                                                        if resp.status == 429:
                                                            await asyncio.sleep(self.adsp_rate_delay_ms / 1000.0)
                                                            continue
                                                        break
                                                    try:
                                                        data = _json.loads(text)
                                                    except Exception:
                                                        break
                                                    code = data.get("code")
                                                    if code not in (0, 200):
                                                        msg_raw = data.get("msg") or text or ""
                                                        msg = msg_raw.lower()
                                                        if ("user_group_id is required" in msg or "group_id is required" in msg) and not group_id:
                                                            raise RuntimeError("创建 AdsPower profile 失败: 需要有效的分组ID")
                                                        if "too many request per second" in msg:
                                                            attempts += 1
                                                            await asyncio.sleep(self.adsp_rate_delay_ms / 1000.0)
                                                            if self.adsp_verbose:
                                                                logger.info(f"[ADSP user.create] rate-limit retry attempts={attempts} wait_ms={self.adsp_rate_delay_ms}")
                                                            continue
                                                        # 其它错误换下一个变体
                                                        break
                                                    self.adsp_profile_id = data.get("data", {}).get("user_id") or data.get("data", {}).get("id")
                                                    if self.adsp_profile_id:
                                                        if self.adsp_verbose:
                                                            logger.info(f"[ADSP user.create] success profile_id={self.adsp_profile_id}")
                                                        try:
                                                            print(f"[ADSP user.create] success profile_id={self.adsp_profile_id}")
                                                        except Exception:
                                                            pass
                                                        created = True
                                                        break
                                                if created:
                                                    break
                                            if created:
                                                break
                                        if created:
                                            break
                                if created:
                                    break
                            if created:
                                break
                    except Exception:
                        continue
                if not created or not self.adsp_profile_id:
                    try:
                        if '___LAST_UC_LINE' in locals() and ___LAST_UC_LINE:
                            print(f"[ADSP user.create LAST] {___LAST_UC_LINE}")
                            logger.warning(f"[ADSP user.create LAST] {___LAST_UC_LINE}")
                    except Exception:
                        pass
                    raise RuntimeError("创建 AdsPower profile 失败: 无法在多版本接口中成功创建")
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
                                data = _json.loads(text)
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
                # 简单重试验证
                for _ in range(3):
                    if ws:
                        return ws
                    await asyncio.sleep(1)
                return ws
        except Exception as e:
            logger.error(f"_prepare_adspower_with_proxy 失败: {e}")
            if self.force_adspower_only:
                raise
            return None

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
                await asyncio.sleep(0.5)
                # 2) delete_cache（可选，多版本兼容）
                cache_urls = [
                    f"{self.adsp_base_url}/api/v1/browser/delete_cache?user_id={self.adsp_profile_id}&{self.adsp_token_param}={self.adsp_token}",
                    f"{self.adsp_base_url}/api/v1/browser/clear_cache?user_id={self.adsp_profile_id}&{self.adsp_token_param}={self.adsp_token}",
                    f"{self.adsp_base_url}/api/v1/user/clear_cache?user_id={self.adsp_profile_id}&{self.adsp_token_param}={self.adsp_token}",
                ]
                for url in cache_urls:
                    try:
                        await session.get(url)
                    except Exception:
                        continue
                await asyncio.sleep(0.5)
                # 3) delete（按需）
                if self.adsp_delete_on_exit:
                    del_variants = [
                        f"{self.adsp_base_url}/api/v1/user/delete?user_id={self.adsp_profile_id}&{self.adsp_token_param}={self.adsp_token}",
                        f"{self.adsp_base_url}/api/v1/user/delete?id={self.adsp_profile_id}&{self.adsp_token_param}={self.adsp_token}",
                        f"{self.adsp_base_url}/api/v1/user/delete?ids={self.adsp_profile_id}&{self.adsp_token_param}={self.adsp_token}",
                    ]
                    for url in del_variants:
                        try:
                            await session.get(url)
                        except Exception:
                            continue
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
                cache = _json.loads(self.group_cache_file.read_text(encoding='utf-8') or '{}')
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
                        data = _json.loads(text)
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
                            data = _json.loads(text)
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
                            data = _json.loads(text)
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
                cache = _json.loads(self.group_cache_file.read_text(encoding='utf-8') or '{}')
            cache[batch_id] = group_id
            self.group_cache_file.write_text(_json.dumps(cache, ensure_ascii=False, indent=2), encoding='utf-8')
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

            # —— AdsPower + 青果代理：获取 wsEndpoint 并透传 ——
            try:
                ws_endpoint = await self._prepare_adspower_with_proxy()
                if not ws_endpoint and self.force_adspower_only:
                    raise RuntimeError("AdsPower wsEndpoint 获取失败，且已启用仅AdsPower模式")
                if ws_endpoint:
                    env["PW_TEST_CONNECT_WS_ENDPOINT"] = ws_endpoint
                    logger.info(f"🔌 使用AdsPower浏览器会话: wsEndpoint={ws_endpoint}")
            except Exception as e:
                logger.error(f"AdsPower 初始化失败: {e}")
                if self.force_adspower_only:
                    raise
            
            # 确保关键的AI API密钥被传递到子进程（优先环境变量，其次settings.* 配置）
            from app.core.config import settings as app_settings

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

            # 在启动前执行通道预检，强制选择一个连通的Provider，确保Midscene不会误选
            selected_provider = await self._probe_and_select_provider(env)
            if selected_provider:
                env['MIDSCENE_FORCE_PROVIDER'] = selected_provider
                logger.info(f"✅ 预检成功，强制选择Provider: {selected_provider}")

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
