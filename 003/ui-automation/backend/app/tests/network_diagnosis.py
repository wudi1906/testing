"""
网络环境诊断工具
专门用于排查API调用失败的网络原因
"""
import asyncio
import aiohttp
import socket
import ssl
import time
from typing import Dict, List, Tuple
from loguru import logger
import json


class NetworkDiagnostic:
    """网络诊断工具"""
    
    def __init__(self):
        self.api_endpoints = {
            "qwen": "https://dashscope.aliyuncs.com",
            "glm": "https://open.bigmodel.cn", 
            "deepseek": "https://api.deepseek.com",
            "uitars": "https://ark.cn-beijing.volces.com",
            "openai": "https://api.openai.com",
            "google": "https://generativelanguage.googleapis.com"
        }
        
    async def test_basic_connectivity(self) -> Dict[str, bool]:
        """测试基础网络连通性"""
        logger.info("🌐 测试基础网络连通性...")
        
        results = {}
        for name, url in self.api_endpoints.items():
            try:
                # 提取域名
                domain = url.replace("https://", "").replace("http://", "")
                
                # DNS解析测试
                start_time = time.time()
                ip = socket.gethostbyname(domain)
                dns_time = time.time() - start_time
                
                logger.info(f"  📍 {name}: {domain} -> {ip} ({dns_time:.2f}s)")
                results[name] = True
                
            except socket.gaierror as e:
                logger.error(f"  ❌ {name}: DNS解析失败 - {e}")
                results[name] = False
            except Exception as e:
                logger.error(f"  ❌ {name}: 连接测试失败 - {e}")
                results[name] = False
                
        return results
    
    async def test_ssl_certificates(self) -> Dict[str, Dict]:
        """测试SSL证书"""
        logger.info("🔒 测试SSL证书...")
        
        results = {}
        for name, url in self.api_endpoints.items():
            try:
                domain = url.replace("https://", "").replace("http://", "")
                
                # 创建SSL上下文
                context = ssl.create_default_context()
                
                # 连接并获取证书信息
                with socket.create_connection((domain, 443), timeout=10) as sock:
                    with context.wrap_socket(sock, server_hostname=domain) as ssock:
                        cert = ssock.getpeercert()
                        
                results[name] = {
                    "valid": True,
                    "subject": dict(x[0] for x in cert['subject']),
                    "issuer": dict(x[0] for x in cert['issuer']),
                    "version": cert['version'],
                    "not_after": cert['notAfter']
                }
                
                logger.info(f"  ✅ {name}: SSL证书有效")
                
            except Exception as e:
                logger.error(f"  ❌ {name}: SSL证书问题 - {e}")
                results[name] = {"valid": False, "error": str(e)}
                
        return results
    
    async def test_proxy_settings(self) -> Dict[str, any]:
        """检测代理设置"""
        logger.info("🔄 检测代理设置...")
        
        import os
        proxy_info = {
            "http_proxy": os.getenv("HTTP_PROXY") or os.getenv("http_proxy"),
            "https_proxy": os.getenv("HTTPS_PROXY") or os.getenv("https_proxy"),
            "no_proxy": os.getenv("NO_PROXY") or os.getenv("no_proxy"),
            "all_proxy": os.getenv("ALL_PROXY") or os.getenv("all_proxy")
        }
        
        # 检查Windows代理设置
        try:
            import winreg
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, 
                              r"Software\Microsoft\Windows\CurrentVersion\Internet Settings") as key:
                try:
                    proxy_enable = winreg.QueryValueEx(key, "ProxyEnable")[0]
                    proxy_server = winreg.QueryValueEx(key, "ProxyServer")[0] if proxy_enable else None
                    proxy_info["windows_proxy_enabled"] = bool(proxy_enable)
                    proxy_info["windows_proxy_server"] = proxy_server
                except FileNotFoundError:
                    proxy_info["windows_proxy_enabled"] = False
        except ImportError:
            pass
        except Exception as e:
            logger.warning(f"无法读取Windows代理设置: {e}")
            
        for key, value in proxy_info.items():
            if value:
                logger.info(f"  🔍 {key}: {value}")
            else:
                logger.info(f"  📍 {key}: 未设置")
                
        return proxy_info
    
    async def test_passwall_impact(self) -> Dict[str, any]:
        """测试Passwall代理的影响"""
        logger.info("🛡️ 测试Passwall代理影响...")
        
        # 检测可能的Passwall端口
        passwall_ports = [1080, 1081, 7890, 7891, 8080, 8118, 10809, 10810]
        active_proxies = []
        
        for port in passwall_ports:
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(1)
                result = sock.connect_ex(('127.0.0.1', port))
                sock.close()
                
                if result == 0:
                    active_proxies.append(port)
                    logger.info(f"  🔍 检测到活动代理端口: {port}")
            except:
                pass
                
        # 测试通过代理的连接
        proxy_test_results = {}
        if active_proxies:
            for port in active_proxies[:2]:  # 只测试前两个
                try:
                    proxy_url = f"http://127.0.0.1:{port}"
                    connector = aiohttp.ProxyConnector.from_url(proxy_url)
                    
                    async with aiohttp.ClientSession(connector=connector, timeout=aiohttp.ClientTimeout(total=10)) as session:
                        async with session.get("https://httpbin.org/ip") as response:
                            if response.status == 200:
                                result = await response.json()
                                proxy_test_results[port] = {
                                    "working": True,
                                    "ip": result.get("origin", "unknown")
                                }
                                logger.info(f"  ✅ 代理端口 {port} 工作正常，出口IP: {result.get('origin')}")
                            else:
                                proxy_test_results[port] = {"working": False, "status": response.status}
                except Exception as e:
                    proxy_test_results[port] = {"working": False, "error": str(e)}
                    logger.error(f"  ❌ 代理端口 {port} 测试失败: {e}")
        
        return {
            "active_proxies": active_proxies,
            "proxy_test_results": proxy_test_results
        }
    
    async def test_api_with_different_methods(self, api_name: str, base_url: str, api_key: str) -> Dict[str, any]:
        """使用不同方法测试API调用"""
        logger.info(f"🧪 测试 {api_name} API的不同调用方法...")
        
        test_results = {}
        
        # 方法1: 直接连接（无代理）
        try:
            connector = aiohttp.TCPConnector(use_dns_cache=False)
            async with aiohttp.ClientSession(connector=connector, timeout=aiohttp.ClientTimeout(total=15)) as session:
                headers = {
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                }
                
                test_data = {
                    "model": "qwen-plus" if "dashscope" in base_url else "gpt-3.5-turbo",
                    "messages": [{"role": "user", "content": "Hi"}],
                    "max_tokens": 5
                }
                
                url = f"{base_url}/v1/chat/completions"
                if "dashscope" in base_url:
                    url = f"{base_url}/compatible-mode/v1/chat/completions"
                elif "bigmodel" in base_url:
                    url = f"{base_url}/api/paas/v4/chat/completions"
                elif "volces" in base_url:
                    url = f"{base_url}/api/v3/chat/completions"
                    
                async with session.post(url, headers=headers, json=test_data) as response:
                    response_text = await response.text()
                    test_results["direct"] = {
                        "status": response.status,
                        "response": response_text[:200],
                        "headers": dict(response.headers)
                    }
                    logger.info(f"  📡 直接连接: {response.status}")
                    
        except Exception as e:
            test_results["direct"] = {"error": str(e)}
            logger.error(f"  ❌ 直接连接失败: {e}")
        
        # 方法2: 尝试通过系统代理
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=15)) as session:
                headers = {
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json"
                }
                
                url = f"{base_url}/v1/chat/completions"
                if "dashscope" in base_url:
                    url = f"{base_url}/compatible-mode/v1/chat/completions"
                elif "bigmodel" in base_url:
                    url = f"{base_url}/api/paas/v4/chat/completions"
                elif "volces" in base_url:
                    url = f"{base_url}/api/v3/chat/completions"
                    
                async with session.post(url, headers=headers, json=test_data) as response:
                    response_text = await response.text()
                    test_results["system_proxy"] = {
                        "status": response.status,
                        "response": response_text[:200]
                    }
                    logger.info(f"  📡 系统代理: {response.status}")
                    
        except Exception as e:
            test_results["system_proxy"] = {"error": str(e)}
            logger.error(f"  ❌ 系统代理失败: {e}")
            
        return test_results
    
    async def comprehensive_diagnosis(self) -> Dict[str, any]:
        """综合诊断"""
        logger.info("🔍 开始综合网络诊断...")
        
        diagnosis = {
            "connectivity": await self.test_basic_connectivity(),
            "ssl_certificates": await self.test_ssl_certificates(),
            "proxy_settings": await self.test_proxy_settings(),
            "passwall_impact": await self.test_passwall_impact(),
        }
        
        # 针对性测试主要API（密钥仅从环境变量读取）
        import os
        main_apis = {
            "qwen": ("https://dashscope.aliyuncs.com", os.getenv("QWEN_API_KEY", "")),
            "deepseek": ("https://api.deepseek.com", os.getenv("DEEPSEEK_API_KEY", ""))
        }
        
        diagnosis["api_tests"] = {}
        for name, (url, key) in main_apis.items():
            diagnosis["api_tests"][name] = await self.test_api_with_different_methods(name, url, key)
        
        return diagnosis
    
    def generate_diagnosis_report(self, diagnosis: Dict) -> None:
        """生成诊断报告"""
        logger.info("\n" + "="*80)
        logger.info("🎯 网络诊断报告")
        logger.info("="*80)
        
        # 连通性报告
        connectivity = diagnosis["connectivity"]
        working_connections = sum(1 for v in connectivity.values() if v)
        logger.info(f"📡 基础连通性: {working_connections}/{len(connectivity)} 个服务可达")
        
        # SSL证书报告
        ssl_results = diagnosis["ssl_certificates"]
        working_ssl = sum(1 for v in ssl_results.values() if v.get("valid", False))
        logger.info(f"🔒 SSL证书: {working_ssl}/{len(ssl_results)} 个服务证书有效")
        
        # 代理设置报告
        proxy_settings = diagnosis["proxy_settings"]
        has_proxy = any(v for v in proxy_settings.values() if v)
        logger.info(f"🔄 代理设置: {'检测到代理配置' if has_proxy else '无代理设置'}")
        
        # Passwall影响报告
        passwall = diagnosis["passwall_impact"]
        active_proxies = passwall["active_proxies"]
        logger.info(f"🛡️ Passwall代理: {'检测到' + str(len(active_proxies)) + '个活动代理端口' if active_proxies else '未检测到活动代理'}")
        
        # 问题诊断
        logger.info(f"\n🔍 可能的问题原因:")
        
        if not working_connections:
            logger.error("  ❌ 网络连接问题 - 无法解析DNS或连接API服务器")
        elif not working_ssl:
            logger.error("  ❌ SSL证书问题 - 可能是代理或防火墙干扰")
        elif active_proxies and has_proxy:
            logger.warning("  ⚠️ 代理冲突 - Passwall代理可能与系统代理冲突")
        elif active_proxies:
            logger.warning("  ⚠️ Passwall代理影响 - 可能需要配置代理白名单")
        else:
            logger.info("  ✅ 网络环境正常，问题可能在API密钥或请求格式")
        
        # 建议解决方案
        logger.info(f"\n💡 建议解决方案:")
        
        if active_proxies:
            logger.info("  1. 尝试将AI API域名加入Passwall代理白名单（直连）")
            logger.info("  2. 或者临时关闭Passwall测试")
            logger.info("  3. 检查Passwall的分流规则")
        
        if has_proxy:
            logger.info("  4. 检查系统代理设置是否与API服务冲突")
            logger.info("  5. 尝试在无代理环境下测试")
        
        logger.info("  6. 检查防火墙设置")
        logger.info("  7. 尝试使用不同的网络环境")
        
        logger.info("="*80)


async def run_network_diagnosis():
    """运行网络诊断"""
    diagnostic = NetworkDiagnostic()
    diagnosis = await diagnostic.comprehensive_diagnosis()
    diagnostic.generate_diagnosis_report(diagnosis)
    return diagnosis


if __name__ == "__main__":
    asyncio.run(run_network_diagnosis())
