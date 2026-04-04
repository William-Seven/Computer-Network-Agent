from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from src.core.agent import CoreAgent
from src.memory.memory_manager import MemoryManager
from src.core.auth import AuthManager

app = FastAPI(title="CN-Agent API", description="计算机网络实践辅导系统后端接口")
auth_manager = AuthManager()

# 配置 CORS，允许前端(8222)跨域访问
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 允许所有来源，生产环境建议改为 ["http://localhost:8222"]
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# @app.get("/")
# def read_root():
#    return {"status": "running", "message": "CN-Agent Backend API (Port 6006)"}

# 模拟一个全局的 session 存储，实际生产中应管理多个 session 实例
# 这里简单起见，每次请求都新建或获取同一个 agent 实例
# 真实场景可以使用依赖注入或缓存来管理 Agent 实例池
agents = {}

class ChatRequest(BaseModel):
    session_id: str
    query: str
    image_data: str = None

class AuthRequest(BaseModel):
    student_id: str
    password: str


@app.post("/auth/register")
def register(request: AuthRequest):
    """
    用户注册接口
    """
    result = auth_manager.register(request.student_id, request.password)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])
    return result

@app.post("/auth/login")
def login(request: AuthRequest):
    """
    用户登录接口
    """
    result = auth_manager.login(request.student_id, request.password)
    if not result["success"]:
        raise HTTPException(status_code=401, detail=result["message"])
    return result



@app.post("/chat/stream")
def chat_stream_endpoint(request: ChatRequest):
    """
    智能答疑接口 (流式返回)
    """
    session_id = request.session_id
    
    if session_id not in agents:
        agents[session_id] = CoreAgent(session_id)
        
    agent = agents[session_id]
    
    # 返回类型设置为 text/event-stream 或 application/x-ndjson
    return StreamingResponse(
        agent.chat_stream(request.query, image_data=request.image_data),
        media_type="application/x-ndjson"
    )

@app.get("/chat/history")
def get_history(session_id: str):
    """
    获取指定 Session 的历史记录
    优化：直接使用 MemoryManager 读取文件，避免加载重量级的 CoreAgent/RAG
    """
    # 1. 如果 Agent 在内存中，直接从内存读取（最新状态）
    if session_id in agents:
        return {"history": agents[session_id].memory.chat_history}
    
    # 2. 如果不在内存中，仅实例化轻量级的 MemoryManager 读取文件
    try:
        memory = MemoryManager(session_id)
        return {"history": memory.chat_history}
    except Exception as e:
        # 如果文件损坏或读取失败，返回空列表
        return {"history": []}

@app.delete("/chat/history")
def clear_history(session_id: str):
    """
    清空指定 Session 的历史记录（包括物理文件）
    """
    # 1. 尝试从活动实例中清理
    if session_id in agents:
        agents[session_id].memory.clear()
        del agents[session_id]
        return {"status": "success", "message": f"Session {session_id} history cleared and file deleted."}
    
    # 2. 如果不在内存中，创建一个临时 MemoryManager 来执行清理
    try:
        memory = MemoryManager(session_id)
        memory.clear()
        return {"status": "success", "message": f"Session {session_id} history file deleted (agent was not active)."}
    except Exception as e:
        return {"status": "error", "message": f"Failed to clear history: {str(e)}"}

from fastapi.staticfiles import StaticFiles

import os

static_path = os.path.join(os.path.dirname(__file__), "..", "ui", "static")

app.mount("/", StaticFiles(directory=static_path, html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    # 明确绑定端口 6006
    uvicorn.run(app, host="0.0.0.0", port=6006)