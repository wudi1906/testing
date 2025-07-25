"""
独立的文件上传接口 - 绕过中间件问题
"""
from fastapi import APIRouter, File, UploadFile, Form, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from loguru import logger
import uuid
import os
import tempfile
import json
from pathlib import Path
from typing import Optional

router = APIRouter()


@router.post("/standalone-upload")
async def standalone_upload(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    doc_format: str = Form("auto"),
    config: str = Form("{}")
):
    """
    独立的文件上传接口
    完全绕过中间件，直接处理文件上传
    """
    try:
        logger.info(f"=== 独立上传接口被调用 ===")
        logger.info(f"文件名: {file.filename}")
        logger.info(f"内容类型: {file.content_type}")
        logger.info(f"文档格式: {doc_format}")
        logger.info(f"配置: {config}")

        # 验证文件
        if not file or not file.filename:
            raise HTTPException(status_code=400, detail="未选择文件")

        # 读取文件内容
        content = await file.read()
        file_size = len(content)
        logger.info(f"文件大小: {file_size} 字节")

        # 生成会话ID
        session_id = str(uuid.uuid4())
        
        # 保存文件到临时目录
        temp_dir = Path(tempfile.gettempdir()) / "api_automation_uploads"
        temp_dir.mkdir(exist_ok=True)
        
        file_path = temp_dir / f"{session_id}_{file.filename}"
        
        with open(file_path, 'wb') as f:
            f.write(content)
        
        logger.info(f"文件已保存到: {file_path}")

        # 解析配置
        try:
            parse_config = json.loads(config)
        except json.JSONDecodeError:
            parse_config = {}

        # 启动后台处理任务
        background_tasks.add_task(
            process_uploaded_file,
            session_id,
            str(file_path),
            file.filename,
            doc_format,
            parse_config
        )

        # 立即返回成功响应
        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "data": {
                    "docId": session_id,
                    "sessionId": session_id,
                    "fileName": file.filename,
                    "fileSize": file_size,
                    "filePath": str(file_path)
                },
                "message": "文件上传成功，正在后台处理"
            }
        )

    except Exception as e:
        logger.error(f"独立上传失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"文件上传失败: {str(e)}")


async def process_uploaded_file(
    session_id: str,
    file_path: str,
    filename: str,
    doc_format: str,
    config: dict
):
    """
    后台处理上传的文件
    """
    try:
        logger.info(f"开始后台处理文件: {filename}")
        
        # 这里可以添加实际的文档解析逻辑
        # 目前只是模拟处理
        
        # 读取文件内容
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        logger.info(f"文件内容长度: {len(content)} 字符")
        
        # 模拟解析过程
        import asyncio
        await asyncio.sleep(2)  # 模拟处理时间
        
        # 解析完成后可以删除临时文件
        try:
            os.unlink(file_path)
            logger.info(f"临时文件已删除: {file_path}")
        except:
            pass
        
        logger.info(f"文件处理完成: {filename}")
        
    except Exception as e:
        logger.error(f"后台处理文件失败: {str(e)}")


@router.get("/upload-status/{session_id}")
async def get_upload_status(session_id: str):
    """
    查询上传处理状态
    """
    try:
        # 这里可以添加实际的状态查询逻辑
        # 目前返回模拟状态
        
        return {
            "success": True,
            "data": {
                "sessionId": session_id,
                "status": "completed",
                "progress": 100,
                "message": "处理完成"
            }
        }
        
    except Exception as e:
        logger.error(f"查询状态失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"查询状态失败: {str(e)}")


@router.post("/simple-test")
async def simple_test(file: UploadFile = File(...)):
    """
    最简单的测试接口
    """
    logger.info(f"=== 简单测试接口 ===")
    logger.info(f"文件名: {file.filename}")
    
    try:
        content = await file.read()
        logger.info(f"文件大小: {len(content)} 字节")
        
        return {
            "success": True,
            "filename": file.filename,
            "size": len(content),
            "message": "简单测试成功"
        }
    except Exception as e:
        logger.error(f"简单测试失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
