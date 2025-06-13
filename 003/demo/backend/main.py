import asyncio
import json
from typing import AsyncGenerator, Dict, Any, Optional

from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from starlette.responses import JSONResponse

from chat_service import ChatService
from document_service import DocumentService
# 反馈队列存储
feedback_queue: asyncio.Queue = asyncio.Queue()

app = FastAPI(title="AutoGen Chat API", version="1.0.0")

# 配置 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 在生产环境中应该设置具体的域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 初始化服务
chat_service = ChatService()
document_service = DocumentService()

class ChatRequest(BaseModel):
    message: str
    session_id: str = "default"
    use_uploaded_files: bool = True  # 是否使用已上传的文件

class ChatResponse(BaseModel):
    content: str
    type: str = "text"
    finished: bool = False

@app.get("/")
async def root():
    return {"message": "AutoGen Chat API is running"}

@app.post("/chat/stream")
async def chat_stream(request: ChatRequest):
    """流式聊天接口"""

    async def generate_response() -> AsyncGenerator[str, None]:
        try:
            # 发送开始事件
            yield f"data: {json.dumps({'type': 'start', 'content': '', 'finished': False})}\n\n"

            # 构建完整的消息内容
            full_message = request.message

            # 如果启用了文件使用，获取会话相关的文件内容
            if request.use_uploaded_files:
                print(f"💬 聊天请求: Session ID: {request.session_id}")
                print(f"📂 当前所有sessions: {list(document_service.session_files.keys())}")
                session_content = document_service.get_session_content(request.session_id)
                print(f"📄 获取到的内容长度: {len(session_content)}")
                if session_content:
                    full_message = f"基于以下文档内容回答问题：\n\n文档内容：\n{session_content}\n\n用户问题：{request.message}"
                    print(f"✅ 使用文档内容进行对话")
                else:
                    print(f"⚠️ 未找到session内容，使用原始问题")

            # 获取流式响应
            async for event in chat_service.chat_stream(full_message, request.session_id):
                # 直接传递事件数据，添加finished字段
                event["finished"] = False
                yield f"data: {json.dumps(event)}\n\n"


            # 发送结束事件
            yield f"data: {json.dumps({'type': 'end', 'content': '', 'finished': True})}\n\n"

        except Exception as e:
            error_data = {
                "type": "error",
                "content": f"Error: {str(e)}",
                "finished": True
            }
            yield f"data: {json.dumps(error_data)}\n\n"

    return StreamingResponse(
        generate_response(),
        media_type="text/plain",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Content-Type": "text/event-stream",
        }
    )

@app.post("/chat")
async def chat(request: ChatRequest):
    """非流式聊天接口"""
    try:
        # 构建完整的消息内容
        full_message = request.message

        # 如果启用了文件使用，获取会话相关的文件内容
        if request.use_uploaded_files:
            session_content = document_service.get_session_content(request.session_id)
            if session_content:
                full_message = f"基于以下文档内容回答问题：\n\n文档内容：\n{session_content}\n\n用户问题：{request.message}"

        response = await chat_service.chat(full_message, request.session_id)
        return ChatResponse(content=response, finished=True)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/chat/session/{session_id}")
async def clear_session(session_id: str):
    """清除会话历史"""
    chat_service.clear_session(session_id)
    return {"message": f"Session {session_id} cleared"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

@app.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    session_id: str = Form("default")
):
    """文件上传接口 - 使用marker进行高质量文档处理"""
    try:
        print(f"📁 文件上传: {file.filename}, Session ID: {session_id}")
        result = await document_service.save_and_extract_file(file, session_id)
        print(f"✅ 上传成功: 文件ID {result['file_id']} 已关联到 session {session_id}")
        return {
            "status": "success",
            "message": "文件上传成功",
            "data": result
        }
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"文件上传失败: {str(e)}")


@app.get("/files/{session_id}")
async def get_session_files(session_id: str):
    """获取会话的所有文件"""
    try:
        files = document_service.get_session_files(session_id)
        return {
            "status": "success",
            "session_id": session_id,
            "files_count": len(files),
            "files": files
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取文件列表失败: {str(e)}")


@app.get("/files/info/{file_id}")
async def get_file_info(file_id: str):
    """获取文件详细信息"""
    try:
        file_info = document_service.get_file_info_by_id(file_id)
        if not file_info:
            raise HTTPException(status_code=404, detail="文件不存在")

        # 不返回完整内容
        response_info = file_info.copy()
        response_info.pop("content", None)

        return {
            "status": "success",
            "file_info": response_info
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取文件信息失败: {str(e)}")


@app.delete("/files/{file_id}")
async def delete_file(file_id: str, session_id: str = "default"):
    """删除文件"""
    try:
        success = document_service.remove_file(file_id, session_id)
        if not success:
            raise HTTPException(status_code=404, detail="文件不存在")

        return {
            "status": "success",
            "message": "文件删除成功",
            "file_id": file_id
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"删除文件失败: {str(e)}")


@app.delete("/files/session/{session_id}")
async def clear_session_files(session_id: str):
    """清除会话的所有文件"""
    try:
        removed_count = document_service.clear_session_files(session_id)
        return {
            "status": "success",
            "message": f"已清除 {removed_count} 个文件",
            "removed_count": removed_count,
            "session_id": session_id
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"清除文件失败: {str(e)}")


@app.get("/upload/formats")
async def get_supported_formats():
    """获取支持的文件格式"""
    try:
        formats_info = document_service.get_supported_formats()
        return {
            "status": "success",
            "data": formats_info
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取格式信息失败: {str(e)}")


@app.post("/upload/search")
async def search_in_document(
    file_path: str,
    query: str,
    case_sensitive: bool = False
):
    """在已上传的文档中搜索内容"""
    try:
        results = await document_service.search_in_document(file_path, query, case_sensitive)
        return {
            "status": "success",
            "query": query,
            "results_count": len(results),
            "results": results[:10]  # 限制返回前10个结果
        }
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"搜索失败: {str(e)}")


class ConfigUpdateRequest(BaseModel):
    use_llm: Optional[bool] = None
    format_lines: Optional[bool] = None
    force_ocr: Optional[bool] = None
    disable_image_extraction: Optional[bool] = None


@app.post("/upload/config")
async def update_processing_config(config: ConfigUpdateRequest):
    """更新文档处理配置"""
    try:
        # 过滤掉None值
        config_dict = {k: v for k, v in config.dict().items() if v is not None}

        if config_dict:
            document_service.update_config(**config_dict)

        current_config = document_service.get_processing_config()
        return {
            "status": "success",
            "message": "配置更新成功",
            "current_config": current_config
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"配置更新失败: {str(e)}")


@app.get("/upload/config")
async def get_processing_config():
    """获取当前文档处理配置"""
    try:
        config = document_service.get_processing_config()
        return {
            "status": "success",
            "config": config
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取配置失败: {str(e)}")


@app.get("/upload/cache/stats")
async def get_cache_stats():
    """获取文件解析缓存统计"""
    try:
        stats = document_service.get_cache_stats()
        return {
            "status": "success",
            "cache_stats": stats
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取缓存统计失败: {str(e)}")


@app.delete("/upload/cache")
async def clear_cache():
    """清除所有文件解析缓存"""
    try:
        cleared_count = document_service.clear_cache()
        return {
            "status": "success",
            "message": f"已清除 {cleared_count} 个缓存项",
            "cleared_count": cleared_count
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"清除缓存失败: {str(e)}")


@app.post("/upload/check-cache")
async def check_file_cache(file: UploadFile = File(...)):
    """检查文件是否已缓存"""
    try:
        file_content = await file.read()
        is_cached = document_service.is_file_cached(file_content)

        return {
            "status": "success",
            "filename": file.filename,
            "is_cached": is_cached,
            "message": "文件已缓存，上传时将直接使用解析结果" if is_cached else "文件未缓存，上传时将进行解析"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"检查缓存失败: {str(e)}")





class FeedbackRequest(BaseModel):
    content: str
    action: str = "send"  # "agree" 或 "send"

@app.post("/feedback/{session_id}")
async def send_feedback(
    session_id: str,
    feedback: FeedbackRequest
):
    # 放入反馈队列
    feedback_data = {
        "content": feedback.content,
        "action": feedback.action,
        "session_id": session_id
    }
    await chat_service.put_feedback(feedback_data)

    return JSONResponse({
        "status": "success",
        "message": "反馈已发送",
    })

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
