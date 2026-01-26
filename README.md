# 🎓 计算机网络实践辅导系统 (CN-Agent)

基于 **LangChain** 智能体架构的计算机网络实验辅导系统，采用 **前后端分离** 模式开发。

## 🏗️ 架构设计

### 1. 核心技术栈
- **环境管理**: Conda (Python 3.11)
- **Agent 框架**: LangChain (ReAct / OpenAI Functions)
- **后端服务**: FastAPI (Port 8111)
- **前端架构**: 原生 HTML/JS SPA (Port 8222)
- **向量数据库**: ChromaDB

### 2. 端口规划
| 服务     | 端口     | 说明                                    |
| -------- | -------- | --------------------------------------- |
| 后端 API | **8111** | 提供 `/chat` 等核心接口，支持 CORS      |
| 前端 UI  | **8222** | 静态页面服务，通过 Fetch 调用 8111 接口 |

## 🚀 快速开始

### 1. 环境准备
```bash
# 激活 Conda 环境
conda activate cn-agent

# 安装依赖
pip install -r requirements.txt
pip install --upgrade "volcengine-python-sdk[ark]"
# 或者
conda env create -f environment.yml
```

### 2. 配置环境变量
复制 `.env.example` 为 `.env` 并填入密钥：
```bash
cp .env.example .env
# 编辑 .env 文件，配置 OPENAI_API_KEY 等
```

### 3. 构建知识库
将实验指导书放入 `data/docs/` 目录，然后运行：
```bash
python3 scripts/ingest_docs.py
```

### 4. 启动服务
使用一键启动脚本（分别启动前后端）：
```bash
chmod +x start.sh
./start.sh
```
- 访问前端: `http://localhost:8222`
- 测试后端: `http://localhost:8111`

## 📁 目录结构
```
cn-agent/
├── src/
│   ├── core/           # Agent 逻辑
│   ├── rag/            # 知识库逻辑
│   ├── api/            # 后端 API (main.py)
│   └── ui/
│       └── static/     # 前端静态资源 (index.html)
├── data/docs/          # 原始实验文档
├── scripts/            # 数据处理脚本
├── requirements.txt    # 项目依赖
└── start.sh            # 启动脚本
```

# todo
- 测试大模型能力边界

- 辅导配置步骤+原理讲解，详细讲解，最后补充引申

- 实际案例，商业场景应用

- 用户管理、数据库

- 历史记录，对话记忆

