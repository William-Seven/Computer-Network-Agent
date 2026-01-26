from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from src.core.agent import CoreAgent

app = FastAPI(title="CN-Agent API", description="计算机网络实践辅导系统后端接口")

# 配置 CORS，允许前端(8222)跨域访问
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 允许所有来源，生产环境建议改为 ["http://localhost:8222"]
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"status": "running", "message": "CN-Agent Backend API (Port 8111)"}

# 模拟一个全局的 session 存储，实际生产中应管理多个 session 实例
# 这里简单起见，每次请求都新建或获取同一个 agent 实例
# 真实场景可以使用依赖注入或缓存来管理 Agent 实例池
agents = {}

class ChatRequest(BaseModel):
    session_id: str
    query: str

class ChatResponse(BaseModel):
    reply: str
    session_id: str


@app.post("/chat", response_model=ChatResponse)
def chat_endpoint(request: ChatRequest):
    """
    智能答疑接口
    """
    session_id = request.session_id
    
    # 获取或创建 Agent 实例
    if session_id not in agents:
        agents[session_id] = CoreAgent(session_id)
    
    agent = agents[session_id]
    
    try:
        reply = agent.chat(request.query)
        return ChatResponse(session_id=session_id, reply=reply)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    # 明确绑定端口 8111
    uvicorn.run(app, host="0.0.0.0", port=8111)