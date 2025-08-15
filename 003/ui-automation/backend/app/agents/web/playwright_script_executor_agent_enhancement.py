"""
Playwright执行智能体增强模块
增强功能：
1. 实时流式日志输出
2. 详细的执行进度反馈  
3. 可视化浏览器执行
4. 用户友好的控制界面
"""
import os
import asyncio
import subprocess
import platform
from typing import Dict, Any
from datetime import datetime
from pathlib import Path
from loguru import logger


class PlaywrightExecutorEnhancement:
    """Playwright执行增强器"""
    
    def __init__(self, base_agent):
        self.agent = base_agent
        self.execution_stats = {}
    
    async def execute_with_enhanced_logging(self, command: list, execution_id: str, env: dict) -> Dict[str, Any]:
        """增强版的执行方法，提供实时流式日志和详细进度"""
        
        # 初始化执行记录
        record = {
            "execution_id": execution_id,
            "start_time": datetime.now(),
            "command": " ".join(command),
            "logs": [],
            "status": "running",
            "progress": {
                "current_step": 0,
                "total_steps": 5,  # 预估步骤数
                "description": "准备执行..."
            }
        }
        
        try:
            # 第1步：环境准备
            record["progress"]["current_step"] = 1
            record["progress"]["description"] = "准备执行环境..."
            await self._send_progress_update(record)
            
            command_str = ' '.join(command)
            logger.info(f"开始执行Playwright测试: {command_str}")
            
            # 环境变量设置
            env_with_utf8 = env.copy()
            env_with_utf8['PYTHONIOENCODING'] = 'utf-8'
            env_with_utf8['CHCP'] = '65001'
            
            # 第2步：启动浏览器
            record["progress"]["current_step"] = 2
            record["progress"]["description"] = "启动浏览器..."
            await self._send_progress_update(record)
            
            if platform.system() == "Windows":
                return await self._execute_windows_streaming(command_str, env_with_utf8, record)
            else:
                return await self._execute_unix_streaming(command, env_with_utf8, record)
                
        except Exception as e:
            record["status"] = "failed"
            record["error"] = str(e)
            logger.error(f"执行失败: {e}")
            await self._send_progress_update(record)
            raise
    
    async def _execute_windows_streaming(self, command_str: str, env: dict, record: dict) -> Dict[str, Any]:
        """Windows系统的实时流式执行"""
        
        # 使用 Popen 进行实时输出
        process = subprocess.Popen(
            command_str,
            cwd=self.agent.playwright_workspace,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=env,
            shell=True,
            encoding='utf-8',
            errors='replace',
            bufsize=1,
            universal_newlines=True
        )
        
        # 第3步：开始测试执行
        record["progress"]["current_step"] = 3
        record["progress"]["description"] = "执行测试脚本..."
        await self._send_progress_update(record)
        
        # 发送详细的执行信息
        await self.agent.send_response("🚀 Playwright测试开始执行!")
        await self.agent.send_response(f"📂 工作目录: {self.agent.playwright_workspace}")
        await self.agent.send_response(f"🔧 执行命令: {command_str}")
        await self.agent.send_response("🌟 浏览器窗口即将打开，请注意观察自动化过程...")
        
        # 实时读取输出
        stdout_lines = []
        stderr_lines = []
        
        # 读取stdout
        async def read_stdout():
            loop = asyncio.get_event_loop()
            while True:
                try:
                    # 在线程池中读取，避免阻塞
                    line = await loop.run_in_executor(None, process.stdout.readline)
                    if not line:
                        break
                    
                    line = line.strip()
                    if line:
                        stdout_lines.append(line)
                        record["logs"].append(f"[STDOUT] {line}")
                        
                        # 智能识别不同类型的输出
                        emoji_msg = self._format_log_message(line)
                        await self.agent.send_response(emoji_msg)
                        logger.info(f"[Playwright] {line}")
                        
                        # 更新进度
                        await self._update_progress_from_log(line, record)
                        
                except Exception as e:
                    logger.error(f"读取stdout时出错: {e}")
                    break
        
        # 读取stderr  
        async def read_stderr():
            loop = asyncio.get_event_loop()
            while True:
                try:
                    line = await loop.run_in_executor(None, process.stderr.readline)
                    if not line:
                        break
                    
                    line = line.strip()
                    if line:
                        stderr_lines.append(line)
                        record["logs"].append(f"[STDERR] {line}")
                        
                        emoji_msg = self._format_error_message(line)
                        await self.agent.send_response(emoji_msg)
                        logger.warning(f"[Playwright Error] {line}")
                        
                except Exception as e:
                    logger.error(f"读取stderr时出错: {e}")
                    break
        
        # 并发读取输出
        await asyncio.gather(read_stdout(), read_stderr())
        
        # 等待进程完成
        return_code = process.wait()
        
        # 第4步：处理结果
        record["progress"]["current_step"] = 4
        record["progress"]["description"] = "处理测试结果..."
        await self._send_progress_update(record)
        
        # 第5步：完成
        record["progress"]["current_step"] = 5
        record["progress"]["description"] = "执行完成!"
        record["status"] = "completed" if return_code == 0 else "failed"
        await self._send_progress_update(record)
        
        if return_code == 0:
            await self.agent.send_response("🎉 测试执行完成!")
        else:
            await self.agent.send_response("❌ 测试执行失败，请查看详细日志")
        
        return {
            "return_code": return_code,
            "stdout": "\n".join(stdout_lines),
            "stderr": "\n".join(stderr_lines),
            "record": record
        }
    
    async def _execute_unix_streaming(self, command: list, env: dict, record: dict) -> Dict[str, Any]:
        """Unix系统的实时流式执行"""
        
        process = await asyncio.create_subprocess_exec(
            *command,
            cwd=self.agent.playwright_workspace,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=env
        )
        
        record["progress"]["current_step"] = 3
        record["progress"]["description"] = "执行测试脚本..."
        await self._send_progress_update(record)
        
        stdout_lines = []
        stderr_lines = []
        
        async def read_stdout():
            async for line in process.stdout:
                line_text = line.decode('utf-8').strip()
                if line_text:
                    stdout_lines.append(line_text)
                    record["logs"].append(f"[STDOUT] {line_text}")
                    
                    emoji_msg = self._format_log_message(line_text)
                    await self.agent.send_response(emoji_msg)
                    logger.info(f"[Playwright] {line_text}")
                    
                    await self._update_progress_from_log(line_text, record)
        
        async def read_stderr():
            async for line in process.stderr:
                line_text = line.decode('utf-8').strip()
                if line_text:
                    stderr_lines.append(line_text)
                    record["logs"].append(f"[STDERR] {line_text}")
                    
                    emoji_msg = self._format_error_message(line_text)
                    await self.agent.send_response(emoji_msg)
                    logger.warning(f"[Playwright Error] {line_text}")
        
        await asyncio.gather(read_stdout(), read_stderr())
        return_code = await process.wait()
        
        record["progress"]["current_step"] = 5
        record["progress"]["description"] = "执行完成!"
        record["status"] = "completed" if return_code == 0 else "failed"
        await self._send_progress_update(record)
        
        return {
            "return_code": return_code,
            "stdout": "\n".join(stdout_lines),
            "stderr": "\n".join(stderr_lines),
            "record": record
        }
    
    def _format_log_message(self, line: str) -> str:
        """根据日志内容格式化消息"""
        line_lower = line.lower()
        
        if "running" in line_lower and "test" in line_lower:
            return f"🏃 {line}"
        elif "✓" in line or "passed" in line_lower:
            return f"✅ {line}"
        elif "✘" in line or "failed" in line_lower:
            return f"❌ {line}"
        elif "error" in line_lower:
            return f"🚨 {line}"
        elif "midscene" in line_lower:
            return f"🎯 {line}"
        elif "report" in line_lower:
            return f"📊 {line}"
        elif "browser" in line_lower or "chromium" in line_lower:
            return f"🌐 {line}"
        elif "test" in line_lower:
            return f"🧪 {line}"
        elif "page" in line_lower:
            return f"📄 {line}"
        elif "click" in line_lower or "tap" in line_lower:
            return f"👆 {line}"
        elif "fill" in line_lower or "type" in line_lower:
            return f"⌨️ {line}"
        else:
            return f"📝 {line}"
    
    def _format_error_message(self, line: str) -> str:
        """格式化错误消息"""
        if "api key" in line.lower():
            return f"🔑 API配置: {line}"
        elif "timeout" in line.lower():
            return f"⏰ 超时: {line}"
        elif "network" in line.lower() or "connection" in line.lower():
            return f"🌐 网络: {line}"
        else:
            return f"⚠️ {line}"
    
    async def _update_progress_from_log(self, line: str, record: dict):
        """从日志内容更新进度信息"""
        line_lower = line.lower()
        
        if "running" in line_lower:
            record["progress"]["description"] = "正在运行测试..."
        elif "browser" in line_lower or "chromium" in line_lower:
            record["progress"]["description"] = "浏览器操作中..."
        elif "page" in line_lower:
            record["progress"]["description"] = "页面交互中..."
        elif "click" in line_lower or "tap" in line_lower:
            record["progress"]["description"] = "执行点击操作..."
        elif "fill" in line_lower or "type" in line_lower:
            record["progress"]["description"] = "输入数据..."
        elif "report" in line_lower:
            record["progress"]["current_step"] = 4
            record["progress"]["description"] = "生成测试报告..."
        
        await self._send_progress_update(record)
    
    async def _send_progress_update(self, record: dict):
        """发送进度更新"""
        progress = record["progress"]
        percentage = (progress["current_step"] / progress["total_steps"]) * 100
        
        progress_msg = f"📊 进度: {progress['current_step']}/{progress['total_steps']} ({percentage:.0f}%) - {progress['description']}"
        await self.agent.send_response(progress_msg)
        
        # 更新执行统计
        self.execution_stats[record["execution_id"]] = record
