import asyncio
import json
from typing import AsyncGenerator

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from chat_service import ChatService

app = FastAPI(title="AutoGen Chat API", version="1.0.0")

# 配置 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 在生产环境中应该设置具体的域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 初始化聊天服务
chat_service = ChatService()

class ChatRequest(BaseModel):
    message: str
    session_id: str = "default"

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

            # 获取流式响应
            async for chunk in chat_service.chat_stream(request.message, request.session_id):
                response_data = {
                    "type": "chunk",
                    "content": chunk,
                    "finished": False
                }
                yield f"data: {json.dumps(response_data)}\n\n"


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
        response = await chat_service.chat(request.message, request.session_id)
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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
