"""
AdsPower + 青果代理 v1-only 烟雾测试

流程（严格按时间线）：
1) 分组：/api/v1/group/list → 无则 /api/v1/group/create
2) 创建环境：/api/v1/user/create
   - 优先 proxyid（环境变量 ADSP_PROXY_ID 或本地配置）
   - 否则 user_proxy_config（proxy_type/proxy_host/proxy_port/proxy_user/proxy_password）
3) 启动：/api/v1/browser/start → 取得 wsUrl
4) 连接 ws → 打开百度 → 等待 3s
5) 停止：/api/v1/browser/stop
6) 删除环境：/api/v1/user/delete（可由 ADSP_DELETE_PROFILE_ON_EXIT 控制）
关键日志仅打印到控制台。
"""

import asyncio
import os
from datetime import datetime
from typing import Any, Dict, Optional

import aiohttp


def _env(name: str, default: Optional[str] = None) -> Optional[str]:
    v = os.getenv(name)
    return v if v is not None and str(v).strip() != "" else default


async def _request_json(session: aiohttp.ClientSession, method: str, url: str, **kwargs) -> Dict[str, Any]:
    async with session.request(method, url, **kwargs) as resp:
        text = await resp.text()
        try:
            data = await resp.json()
        except Exception:
            data = {}
        print(f"[HTTP] {method} {url} -> {resp.status} {text[:200]}")
        return {"status": resp.status, "text": text, "data": data}


def _calc_tile_bounds(index: int, total: int, screen_w: int, screen_h: int,
                      cols: Optional[int] = None, rows: Optional[int] = None,
                      margin: int = 8) -> Dict[str, int]:
    """计算平铺窗口在屏幕上的位置与尺寸。index 从 0 开始。"""
    if total <= 0:
        total = 1
    if index < 0:
        index = 0
    if index >= total:
        index = total - 1
    import math
    if not cols or cols <= 0:
        cols = int(math.ceil(math.sqrt(total)))
    if not rows or rows <= 0:
        rows = int(math.ceil(total / cols))
    cell_w = max(200, int((screen_w - (cols + 1) * margin) / cols))
    cell_h = max(150, int((screen_h - (rows + 1) * margin) / rows))
    r = index // cols
    c = index % cols
    left = margin + c * (cell_w + margin)
    top = margin + r * (cell_h + margin)
    return {"left": left, "top": top, "width": cell_w, "height": cell_h}


def _get_screen_size() -> Dict[str, int]:
    """自动获取主显示器分辨率，失败则回退 1920x1080。"""
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

async def _set_window_bounds_for_page(browser, context, page, bounds: Dict[str, int]):
    """尽可能稳地为当前 page 设置最外层窗口的像素大小与位置。
    1) 先以当前 page 的 targetId 调用 Browser.getWindowForTarget
    2) 失败则不带 targetId 调用，取默认窗口
    3) 再失败则枚举 Target.getTargets，找第一个 type=page 的 targetId 再尝试
    """
    # 尝试1：当前 page targetId
    try:
        cdp_page = await context.new_cdp_session(page)
        ti = await cdp_page.send('Target.getTargetInfo')
        target_id = (ti.get('targetInfo') or {}).get('targetId') or ti.get('targetId')
        cdp_browser = await browser.new_browser_cdp_session()
        info = await cdp_browser.send('Browser.getWindowForTarget', {'targetId': target_id})
        window_id = info.get('windowId')
        if window_id:
            try:
                cur = await cdp_browser.send('Browser.getWindowBounds', {'windowId': window_id})
                state = (cur.get('bounds') or {}).get('windowState') or cur.get('windowState')
                if state in ('maximized', 'fullscreen', 'minimized'):
                    await cdp_browser.send('Browser.setWindowBounds', {'windowId': window_id, 'bounds': {'windowState': 'normal'}})
                    await asyncio.sleep(0.05)
            except Exception:
                pass
            await cdp_browser.send('Browser.setWindowBounds', {
                'windowId': window_id,
                'bounds': {
                    'left': bounds['left'], 'top': bounds['top'],
                    'width': bounds['width'], 'height': bounds['height'],
                    'windowState': 'normal'
                }
            })
            return True
    except Exception:
        pass

    # 尝试2：不带 targetId
    try:
        cdp_browser = await browser.new_browser_cdp_session()
        info = await cdp_browser.send('Browser.getWindowForTarget')
        window_id = info.get('windowId')
        if window_id:
            await cdp_browser.send('Browser.setWindowBounds', {
                'windowId': window_id,
                'bounds': {
                    'left': bounds['left'], 'top': bounds['top'],
                    'width': bounds['width'], 'height': bounds['height'],
                    'windowState': 'normal'
                }
            })
            return True
    except Exception:
        pass

    # 尝试3：枚举 targets
    try:
        cdp_browser = await browser.new_browser_cdp_session()
        targets = await cdp_browser.send('Target.getTargets')
        for t in (targets.get('targetInfos') or []):
            if t.get('type') == 'page':
                tid = t.get('targetId')
                try:
                    info = await cdp_browser.send('Browser.getWindowForTarget', {'targetId': tid})
                    window_id = info.get('windowId')
                    if window_id:
                        await cdp_browser.send('Browser.setWindowBounds', {
                            'windowId': window_id,
                            'bounds': {
                                'left': bounds['left'], 'top': bounds['top'],
                                'width': bounds['width'], 'height': bounds['height'],
                                'windowState': 'normal'
                            }
                        })
                        return True
                except Exception:
                    continue
    except Exception:
        pass
    return False

async def _open_once(session: aiohttp.ClientSession,
                     base_url: str,
                     token: str,
                     gid: str,
                     proxyid: Optional[int],
                     qg_endpoint: str,
                     qg_authkey: str,
                     qg_authpwd: str,
                     rate_delay_ms: int,
                     variant: Dict[str, Any]) -> None:
    """按给定 variant（viewport/window 参数）启动一次并展示页面。"""
    # 复制 env读取逻辑（局部覆盖 variant）
    user_create_url = f"{base_url}/api/v1/user/create?token={token}"
    user_name = variant.get("user_name") or f"demo-{datetime.now().strftime('%H%M%S')}"

    # viewport
    try:
        vp_w = int(str(variant.get("viewport_w") or 1366))
        vp_h = int(str(variant.get("viewport_h") or 768))
    except Exception:
        vp_w, vp_h = 1366, 768

    # fingerprint
    desktop_ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36"
    fp_cfg = {
        "device_type": "desktop",           # 明确桌面端
        "os": "win",
        "os_type": "windows",
        "system": "windows",
        "platform": "Win32",
        "is_mobile": False,
        "mobile": False,
        "ua_auto": True,
        "ua_min_version": 138,
        # 强制桌面UA（多版本兼容：ua/user_agent 都给）
        "ua": desktop_ua,
        "user_agent": desktop_ua,
        # 其他
        "timezone": "Asia/Shanghai",
        "screen_resolution": f"{vp_w}_{vp_h}",
        "screen_width": vp_w,
        "screen_height": vp_h,
    }

    # proxy
    host, port_str = qg_endpoint, None
    if ":" in qg_endpoint:
        host, port_str = qg_endpoint.split(":", 1)
    try:
        port = int(port_str) if port_str else 0
    except Exception:
        port = 0
    proxy_payload = {"user_proxy_config": {"proxy_type": "http", "proxy_host": host, "proxy_port": port, "proxy_user": qg_authkey, "proxy_password": qg_authpwd}}
    if proxyid is not None:
        proxy_payload = {"proxyid": proxyid}

    # 兼容多版本 user_proxy_config & group 字段，带限流重试
    user_id = None
    # 准备多种 proxy 变体
    username = qg_authkey
    password = qg_authpwd
    no_scheme = f"{host}:{port}" if host and port else None
    with_scheme = f"http://{host}:{port}" if host and port else None
    no_scheme_auth = f"{username}:{password}@{host}:{port}" if username and password and host and port else None
    with_scheme_auth = f"http://{username}:{password}@{host}:{port}" if username and password and host and port else None
    proxy_variants = []
    if proxyid is not None:
        proxy_variants.append({"proxyid": proxyid})
    # 优先放置：此前在你环境中验证成功的形态（proxy_soft + host/port + proxy_user/password）
    proxy_variants.append({"user_proxy_config": {"proxy_soft": "other", "proxy_type": "http", "proxy_host": host, "proxy_port": port, "proxy_user": username, "proxy_password": password}})
    proxy_variants.append({"user_proxy_config": {"proxy_soft": "other", "proxy_type": "http", "proxy_host": host, "proxy_port": str(port), "proxy_user": username, "proxy_password": password}})
    proxy_variants.append({"user_proxy_config": {"proxy_soft": "other", "proxy_type": "http", "proxy_host": host, "proxy_port": port, "proxy_username": username, "proxy_password": password}})
    # 对象结构
    proxy_variants.append({"user_proxy_config": {"proxy_type": "http", "proxy_host": host, "proxy_port": port, "proxy_user": username, "proxy_password": password}})
    proxy_variants.append({"user_proxy_config": {"proxy_type": "HTTP", "proxy_host": host, "proxy_port": port, "proxy_user": username, "proxy_password": password}})
    proxy_variants.append({"user_proxy_config": {"proxy_type": "http", "proxy_host": host, "proxy_port": str(port), "proxy_user": username, "proxy_password": password}})
    proxy_variants.append({"user_proxy_config": {"proxy_type": "http", "proxy_host": host, "proxy_port": port, "proxy_username": username, "proxy_password": password}})
    proxy_variants.append({"user_proxy_config": {"ip": host, "port": port, "user": username, "password": password, "type": "http"}})
    # proxy 字符串
    if no_scheme:
        proxy_variants.append({"user_proxy_config": {"proxy_type": "http", "proxy": no_scheme}})
    if with_scheme:
        proxy_variants.append({"user_proxy_config": {"proxy": with_scheme}})
    if no_scheme_auth:
        proxy_variants.append({"user_proxy_config": {"proxy_type": "http", "proxy": no_scheme_auth}})
    if with_scheme_auth:
        proxy_variants.append({"user_proxy_config": {"proxy": with_scheme_auth}})
    # proxy_soft
    if no_scheme:
        proxy_variants.append({"user_proxy_config": {"proxy_soft": "other", "proxy_type": "http", "proxy": no_scheme}})
    if no_scheme_auth:
        proxy_variants.append({"user_proxy_config": {"proxy_soft": "other", "proxy_type": "http", "proxy": no_scheme_auth}})

    # 尝试 group_id / user_group_id
    for gk in ["group_id", "user_group_id"]:
        for pv in proxy_variants:
            for fp_key in ["fingerprint", "fingerprint_config"]:
                payload = {"user_name": user_name, gk: gid, **pv, fp_key: fp_cfg}
                # 限流重试
                for _ in range(3):
                    r = await _request_json(session, "POST", user_create_url, json=payload)
                    code = (r.get("data") or {}).get("code")
                    msg = (r.get("data") or {}).get("msg") or ""
                    if code in (0, 200):
                        user_id = (r.get("data") or {}).get("data", {}).get("user_id") or (r.get("data") or {}).get("data", {}).get("id")
                        if user_id:
                            break
                    if isinstance(msg, str) and ("Too many" in msg or "request per second" in msg or "429" in msg):
                        await asyncio.sleep(rate_delay_ms / 1000)
                        continue
                    break
                if user_id:
                    break
            if user_id:
                break
        if user_id:
            break
    if not user_id:
        print("[VARIANT] create failed (all proxy variants)")
        return
    print(f"[VARIANT] user_id={user_id} vp={vp_w}x{vp_h}")

    # 启动
    start_url = f"{base_url}/api/v1/browser/start?user_id={user_id}&token={token}"
    r = await _request_json(session, "GET", start_url)
    inner = (r.get("data") or {}).get("data") or {}
    ws = inner.get("wsUrl") or inner.get("ws_url") or inner.get("wsEndpoint")
    if not ws:
        ws_field = inner.get("ws")
        if isinstance(ws_field, dict):
            ws = ws_field.get("puppeteer") or ws_field.get("playwright") or ws_field.get("cdp") or ws_field.get("ws")
    if not ws:
        print("[VARIANT] no ws")
        return

    # 连接并设置窗口和页面
    from playwright.async_api import async_playwright
    async with async_playwright() as p:
        browser = await p.chromium.connect_over_cdp(ws)
        context = browser.contexts[0] if browser.contexts else await browser.new_context()
        page = context.pages[0] if context.pages else await context.new_page()
        # 窗口外层（更稳的三段式）
        try:
            left = int(str(variant.get('left') or 0))
            top = int(str(variant.get('top') or 0))
            ww = int(str(variant.get('win_w') or 960))
            wh = int(str(variant.get('win_h') or 540))
            await _set_window_bounds_for_page(browser, context, page, {'left': left, 'top': top, 'width': ww, 'height': wh})
        except Exception as e:
            print(f"[VARIANT] setWindowBounds err: {e}")

        # 页面分辨率（mobile=false，强制桌面 UA 宽度）
        try:
            cdp_page = await context.new_cdp_session(page)
            await cdp_page.send('Emulation.setDeviceMetricsOverride', {
                'width': vp_w,
                'height': max(vp_h, 800),
                'deviceScaleFactor': 1,
                'mobile': False
            })
        except Exception as e:
            print(f"[VARIANT] set metrics err: {e}")

        await page.goto("https://www.baidu.com")
        await asyncio.sleep(1.5)
        await browser.close()

    # 资源清理（stop→delete）
    try:
        await _request_json(session, "GET", f"{base_url}/api/v1/browser/stop?user_id={user_id}&token={token}")
        await asyncio.sleep(0.2)
        await _request_json(session, "GET", f"{base_url}/api/v1/user/delete?ids={user_id}&token={token}")
    except Exception:
        pass


async def run_smoke() -> None:
    base_url = _env("ADSP_BASE_URL", "http://local.adspower.net:50325").rstrip("/")
    token = _env("ADSP_TOKEN", "").strip()
    if not token:
        print("[ERR] 请设置 ADSP_TOKEN")
        return

    # 青果代理
    qg_endpoint = _env("QG_TUNNEL_ENDPOINT", "tun-szbhry.qg.net:17790")
    qg_authkey = _env("QG_AUTHKEY", "")
    qg_authpwd = _env("QG_AUTHPWD", "")

    # 代理池 proxyid（可选）
    proxyid: Optional[int] = None
    proxyid_env = _env("ADSP_PROXY_ID") or _env("ADSP_PROXYID")
    if proxyid_env:
        try:
            proxyid = int(proxyid_env)
        except Exception:
            proxyid = None

    delete_on_exit = _env("ADSP_DELETE_PROFILE_ON_EXIT", "true").lower() == "true"

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}",
        "X-API-KEY": token,
    }

    timeout = aiohttp.ClientTimeout(total=30)
    rate_delay_ms = 0
    try:
        rate_delay_ms = int(_env("ADSP_RATE_LIMIT_DELAY_MS", "1500") or "1500")
    except Exception:
        rate_delay_ms = 1500
    async with aiohttp.ClientSession(headers=headers, timeout=timeout) as session:
        # 1) 分组
        batch_id = f"smoke_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        print(f"[GROUP] batch={batch_id}")
        gid = None
        # list
        list_url = f"{base_url}/api/v1/group/list?token={token}"
        r = await _request_json(session, "GET", list_url)
        # 兼容 v1 响应结构：{"code":0,"data":{"list":[...],...}}
        root = r.get("data") or {}
        inner = root.get("data") if isinstance(root.get("data"), dict) else None
        groups = []
        if inner and isinstance(inner.get("list"), list):
            groups = inner.get("list")
        elif isinstance(root.get("list"), list):
            groups = root.get("list")
        for g in groups:
            name = g.get("name") or g.get("group_name")
            if name == batch_id:
                gid = g.get("group_id") or g.get("id")
                break
        if not gid:
            create_url = f"{base_url}/api/v1/group/create?token={token}"
            payload = {"group_name": batch_id}
            r = await _request_json(session, "POST", create_url, json=payload)
            gid = (r.get("data") or {}).get("data", {}).get("group_id") or (r.get("data") or {}).get("data", {}).get("id")
        if not gid:
            print("[ERR] 获取/创建分组失败")
            return
        print(f"[GROUP] group_id={gid}")

        # 2) 创建环境（固定竖长条尺寸：窗口 600x900，页面 1366x900）
        user_name = f"smoke-{datetime.now().strftime('%H%M%S')}"
        user_create_url = f"{base_url}/api/v1/user/create?token={token}"

        # 先尝试 proxyid；否则依次尝试多种 user_proxy_config 版本
        user_id: Optional[str] = None
        if proxyid is not None:
            payload = {"user_name": user_name, "group_id": gid, "proxyid": proxyid}
            r = await _request_json(session, "POST", user_create_url, json=payload)
            code = (r.get("data") or {}).get("code")
            if code in (0, 200):
                user_id = (r.get("data") or {}).get("data", {}).get("user_id") or (r.get("data") or {}).get("data", {}).get("id")
            else:
                print(f"[WARN] 使用 proxyid 创建失败，code={code}，将尝试 user_proxy_config 方案")

        if user_id is None:
            host, port_str = qg_endpoint, None
            if ":" in qg_endpoint:
                host, port_str = qg_endpoint.split(":", 1)
            try:
                port = int(port_str) if port_str else 0
            except Exception:
                port = 0

            proxy_uri = f"http://{qg_authkey}:{qg_authpwd}@{host}:{port}" if qg_authkey and qg_authpwd and host and port else None

            # 强制桌面端 + 新内核UA配置（多版本字段名兼容）
            vp_w, vp_h = 1366, 900
            desktop_ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36"
            fp_cfg = {
                "device_type": "desktop",
                "os": "win",
                "os_type": "windows",
                "system": "windows",
                "platform": "Win32",
                "is_mobile": False,
                "mobile": False,
                "ua_auto": True,
                "ua_min_version": 138,
                "ua": desktop_ua,
                "user_agent": desktop_ua,
                "timezone": "Asia/Shanghai",
                # 按官方提示：width_height
                "screen_resolution": f"{vp_w}_{vp_h}",
                "screen_width": vp_w,
                "screen_height": vp_h,
            }

            import json as _json
            proxy_obj = {"proxy_type": "http", "proxy_host": host, "proxy_port": port, "proxy_user": qg_authkey, "proxy_password": qg_authpwd}
            proxy_obj_upper = {"proxy_type": "HTTP", "proxy_host": host, "proxy_port": port, "proxy_user": qg_authkey, "proxy_password": qg_authpwd}
            proxy_json_str = _json.dumps(proxy_obj, ensure_ascii=False)

            # 准备多版本候选
            candidates = [
                # 1) 常见对象写法（小写 http）
                {"user_proxy_config": proxy_obj},
                # 2) 常见对象写法（大写 HTTP）
                {"user_proxy_config": proxy_obj_upper},
                # 3) 端口字符串
                {"user_proxy_config": {**proxy_obj, "proxy_port": str(port)}},
                # 3a) proxy_soft='other' + host/port（proxy_user）
                {"user_proxy_config": {"proxy_soft": "other", "proxy_type": "http", "proxy_host": host, "proxy_port": port, "proxy_user": qg_authkey, "proxy_password": qg_authpwd}},
                # 3a-1) proxy_soft='other' + host/port（proxy_user，端口字符串）
                {"user_proxy_config": {"proxy_soft": "other", "proxy_type": "http", "proxy_host": host, "proxy_port": str(port), "proxy_user": qg_authkey, "proxy_password": qg_authpwd}},
                # 3a-2) proxy_soft='other' + host/port（proxy_username）
                {"user_proxy_config": {"proxy_soft": "other", "proxy_type": "http", "proxy_host": host, "proxy_port": port, "proxy_username": qg_authkey, "proxy_password": qg_authpwd}},
                # 3b) 对象写法 + proxy_soft='other' + 无 scheme
                ({"user_proxy_config": {"proxy_soft": "other", "proxy_type": "http", "proxy": f"{host}:{port}"}} if host and port else None),
                # 3c) 对象写法 + proxy_soft='other' + 带用户名密码 + 无 scheme
                ({"user_proxy_config": {"proxy_soft": "other", "proxy_type": "http", "proxy": f"{qg_authkey}:{qg_authpwd}@{host}:{port}"}} if qg_authkey and qg_authpwd and host and port else None),
                # 3d) 对象写法 + proxy_soft='other' + 带 scheme
                ({"user_proxy_config": {"proxy_soft": "other", "proxy_type": "http", "proxy": proxy_uri}} if proxy_uri else None),
                # 4) 仅使用 proxy 字符串 + 类型（不带 scheme）
                ({"user_proxy_config": {"proxy_type": "http", "proxy": f"{qg_authkey}:{qg_authpwd}@{host}:{port}"}} if qg_authkey and qg_authpwd else None),
                # 5) 仅使用 proxy 字符串（带 scheme）
                ({"user_proxy_config": {"proxy": proxy_uri}} if proxy_uri else None),
                # 6) 仅使用 proxy 字符串（不带 scheme，无类型）
                ({"user_proxy_config": {"proxy": f"{qg_authkey}:{qg_authpwd}@{host}:{port}"}} if qg_authkey and qg_authpwd else None),
                # 7) ip/port/user/password 写法
                {"user_proxy_config": {"ip": host, "port": port, "user": qg_authkey, "password": qg_authpwd, "type": "http"}},
                # 8) 增加 proxy_soft 提示
                {"user_proxy_config": {**proxy_obj, "proxy_soft": 1}},
                # 9) JSON 字符串形式
                {"user_proxy_config": proxy_json_str},
                # 9b) JSON 字符串（包含 proxy_soft='other'）
                ( {"user_proxy_config": _json.dumps({"proxy_soft": "other", "proxy_type": "http", "proxy": f"{qg_authkey}:{qg_authpwd}@{host}:{port}" if (qg_authkey and qg_authpwd and host and port) else f"{host}:{port}"}, ensure_ascii=False) } if host and port else None),
                # 10) host:port + 独立用户名密码
                ({"user_proxy_config": {"proxy_type": "http", "proxy": f"{host}:{port}", "proxy_user": qg_authkey, "proxy_password": qg_authpwd}} if host and port else None),
                # 11) host/port/username/password 另一套命名
                {"user_proxy_config": {"proxy_type": "http", "proxy_ip": host, "proxy_port": port, "username": qg_authkey, "password": qg_authpwd}},
                # 12) 大写键名风格
                {"user_proxy_config": {"proxy_type": "http", "proxy_host": host, "proxy_port": port, "proxy_username": qg_authkey, "proxy_password": qg_authpwd}},
                # 13) 简写字段名
                {"user_proxy_config": {"type": "http", "host": host, "port": port, "user": qg_authkey, "password": qg_authpwd}},
            ]
            # 过滤 None
            candidates = [c for c in candidates if c is not None]

            group_keys = ["group_id", "user_group_id"]
            fp_keys = ["fingerprint_config", "fingerprint"]
            for gk in group_keys:
                if user_id:
                    break
                for idx, proxy_payload in enumerate(candidates, start=1):
                    for fk in fp_keys:
                        payload = {"user_name": user_name, gk: gid, **proxy_payload, fk: fp_cfg}
                        key_list = list(proxy_payload.get('user_proxy_config', {}).keys()) if isinstance(proxy_payload.get('user_proxy_config'), dict) else ["<string>"]
                        print(f"[TRY] user.create 方案#{idx} groupKey={gk} fpKey={fk} keys={key_list}")
                        r = await _request_json(session, "POST", user_create_url, json=payload)
                        code = (r.get("data") or {}).get("code")
                        msg = (r.get("data") or {}).get("msg") or ""
                        if code in (0, 200):
                            user_id = (r.get("data") or {}).get("data", {}).get("user_id") or (r.get("data") or {}).get("data", {}).get("id")
                            if user_id:
                                break
                        else:
                            if isinstance(msg, str) and ("Too many" in msg or "request per second" in msg or "429" in msg):
                                await asyncio.sleep(rate_delay_ms / 1000)
                                continue
                    if user_id:
                        break

        if not user_id:
            print("[ERR] 创建环境失败，请检查 proxy 配置或套餐限制")
            return
        print(f"[CREATE] user_id={user_id}")
        if not user_id:
            print("[ERR] 未获得 user_id")
            return
        # 3) 启动（无预热，单次启动）
        start_url = f"{base_url}/api/v1/browser/start?user_id={user_id}&token={token}"
        r = await _request_json(session, "GET", start_url)
        data = r.get("data") or {}
        inner = data.get("data") or {}
        ws = inner.get("wsUrl") or inner.get("ws_url") or inner.get("wsEndpoint")
        if not ws:
            ws_field = inner.get("ws")
            if isinstance(ws_field, dict):
                # 常见返回里包含 puppeteer/ws cdp 地址
                ws = ws_field.get("puppeteer") or ws_field.get("playwright") or ws_field.get("cdp") or ws_field.get("ws")
        if not ws:
            print("[ERR] 未获得 wsUrl")
            return
        print(f"[START] ws={ws}")

        # 4) 连接并打开百度（改为 async API，避免在 asyncio loop 中使用 sync API 报错）
        try:
            from playwright.async_api import async_playwright
        except Exception:
            print("[ERR] Python Playwright 未安装：pip install playwright && playwright install chromium")
            return
        try:
            async with async_playwright() as p:
                browser = await p.chromium.connect_over_cdp(ws)
                context = browser.contexts[0] if browser.contexts else await browser.new_context()
                # 使用现有唯一标签页，不新开；为避免闪烁，不主动 bring_to_front
                page = context.pages[0] if context.pages else await context.new_page()
                # 平铺小竖条（默认按单屏10窗：5列×2行）并绑定当前page窗口
                try:
                    scr = _get_screen_size()
                    bounds = _calc_tile_bounds(0, 10, scr['w'], scr['h'], 5, 2, 8)
                    # 绑定当前 page 的 targetId，确保定位的是“最外层真实窗口”
                    cdp_page = await context.new_cdp_session(page)
                    ti = await cdp_page.send('Target.getTargetInfo')
                    target_id = (ti.get('targetInfo') or {}).get('targetId') or ti.get('targetId')
                    cdp = await browser.new_browser_cdp_session()
                    info = await cdp.send('Browser.getWindowForTarget', {'targetId': target_id})
                    window_id = info.get('windowId')
                    if window_id:
                        # 先最小化，尽量避免默认大窗可见
                        try:
                            await cdp.send('Browser.setWindowBounds', { 'windowId': window_id, 'bounds': { 'windowState': 'minimized' } })
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
                                'left': bounds['left'],
                                'top': bounds['top'],
                                'width': bounds['width'],
                                'height': bounds['height'],
                                'windowState': 'normal'
                            }
                        })
                        # 关键：让 viewport 与窗口可视区域一致
                        await page.wait_for_timeout(250)
                        inner = await page.evaluate("()=>({w: window.innerWidth, h: window.innerHeight})")
                        w = max(1, int(inner.get('w') if isinstance(inner, dict) else inner['w']))
                        h = max(1, int(inner.get('h') if isinstance(inner, dict) else inner['h']))
                        # 先用 Playwright 设定 viewport，再用 CDP 覆盖，确保在导航前生效
                        try:
                            await page.set_viewport_size({'width': w, 'height': h})
                        except Exception:
                            pass
                        cdp_page2 = await context.new_cdp_session(page)
                        await cdp_page2.send('Emulation.setDeviceMetricsOverride', {
                            'width': w,
                            'height': h,
                            'deviceScaleFactor': 1,
                            'mobile': False
                        })
                except Exception:
                    pass
                try:
                    await page.goto("https://www.baidu.com", timeout=30000)
                    print("[NAV] 打开百度成功，等待3秒...")
                    await asyncio.sleep(3)
                except Exception:
                    # 网络不可达或代理异常时，不影响窗口尺寸验证
                    print("[NAV] 外网不可达，跳过页面加载，仅验证窗口/viewport")
                    await asyncio.sleep(1.5)
                # 仅断开CDP连接（不关闭远端窗口），由 stop 接口负责关闭
                await browser.close()
        except Exception as e:
            print(f"[ERR] Playwright 连接/导航失败: {e}")
        
        # 5) 停止
        stop_url = f"{base_url}/api/v1/browser/stop?user_id={user_id}&token={token}"
        await _request_json(session, "GET", stop_url)
        await asyncio.sleep(1)

        # 5.1) 清理缓存（按官方文档可能不存在，若404则跳过；仅少量尝试，避免噪音）
        try:
            r = await _request_json(session, "GET", f"{base_url}/api/v1/browser/clear_cache?user_id={user_id}&token={token}")
            if ((r.get("status") or 0) == 404):
                pass
        except Exception:
            pass
        await asyncio.sleep(0.3)
        
        # 6) 删除
        if delete_on_exit:
            # 精简删除：先 GET ids=，若限流等退避重试；再 POST {user_ids:[...]}/{ids:[...]}
            deleted = False
            # GET ids
            for _ in range(3):
                r = await _request_json(session, "GET", f"{base_url}/api/v1/user/delete?ids={user_id}&token={token}")
                code = (r.get("data") or {}).get("code")
                msg = (r.get("data") or {}).get("msg") or ""
                if code in (0, 200):
                    deleted = True
                    break
                if isinstance(msg, str) and ("Too many" in msg or "request per second" in msg or "429" in msg):
                    await asyncio.sleep(rate_delay_ms / 1000)
                    continue
                break
            if not deleted:
                # POST user_ids
                for _ in range(3):
                    r = await _request_json(session, "POST", f"{base_url}/api/v1/user/delete?token={token}", json={"user_ids": [user_id]})
                    code = (r.get("data") or {}).get("code")
                    msg = (r.get("data") or {}).get("msg") or ""
                    if code in (0, 200):
                        deleted = True
                        break
                    if isinstance(msg, str) and ("Too many" in msg or "request per second" in msg or "429" in msg):
                        await asyncio.sleep(rate_delay_ms / 1000)
                        continue
                    break
            if not deleted:
                # POST ids（有些版本使用 ids 键）
                for _ in range(3):
                    r = await _request_json(session, "POST", f"{base_url}/api/v1/user/delete?token={token}", json={"ids": [user_id]})
                    code = (r.get("data") or {}).get("code")
                    msg = (r.get("data") or {}).get("msg") or ""
                    if code in (0, 200):
                        deleted = True
                        break
                    if isinstance(msg, str) and ("Too many" in msg or "request per second" in msg or "429" in msg):
                        await asyncio.sleep(rate_delay_ms / 1000)
                        continue
                    break
            if not deleted:
                print("[WARN] 删除环境未确认成功（可能接口差异），已确保窗口已关闭")
        print("[DONE] 烟雾测试完成")


if __name__ == "__main__":
    asyncio.run(run_smoke())


