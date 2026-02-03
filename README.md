# 🎓 计算机网络实践辅导系统 (CN-Agent)

基于 **LangChain** 智能体架构的计算机网络实验辅导系统，采用 **前后端分离** 模式开发。

## ✨ 核心特性

- **📚 多格式 RAG 问答**：支持 **Markdown、PDF、Word、PPT** 多种格式文档的解析与检索，知识库构建更加灵活。
- **👁️ 多模态视觉感知**：自动从 PDF 中提取图片并进行向量化，Agent 能够结合图片内容（如网络拓扑图、实验结果截图）回答问题。
- **🧠 持久化记忆**：支持多轮对话，对话记录自动保存至本地 JSON 文件，服务重启不丢失。
- **🔐 用户身份认证**：内置轻量级账号系统，支持学生注册/登录，保障学习数据的私密性与安全性。
- **🔄 智能会话隔离**：基于`学号 + 实验ID`的双重维度隔离对话历史，支持跨设备同步学习进度。
- **🎨 交互体验升级**：前端支持 Markdown/代码高亮，全屏登录遮罩，以及一键注销功能。
- **⚡️ 高性能架构**：前后端分离，历史记录读取接口经过专门优化，毫秒级响应。

## 🏗️ 架构设计

### 1. 核心技术栈
- **环境管理**: Conda (Python 3.11)
- **Agent 框架**: LangChain (ReAct / OpenAI Functions)
- **后端服务**: FastAPI (Port 8111)
- **认证模块**: AuthManager (SHA256 加密)
- **前端架构**: 原生 HTML/JS SPA (Port 8222) + Marked.js
- **向量数据库**: ChromaDB
- **数据存储**: 
  - `data/sessions/`: 对话历史 (*.json)
  - `data/users.json`: 用户账户信息
  - `data/assets/`: 提取的图片资源

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
将实验指导书（支持 .md, .pdf, .docx, .pptx）放入 `data/docs/` 目录，然后运行：
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
│   ├── core/           
│   │   ├── agent.py    # Agent 核心逻辑
│   │   └── auth.py     # [NEW] 用户认证管理
│   ├── rag/            # 知识库引擎 (RAGEngine + Loaders)
│   │   ├── pdf_loader.py  # [NEW] 多模态 PDF 加载器
│   │   └── rag_engine.py  # 核心检索逻辑
│   ├── memory/         # 记忆管理 (MemoryManager)
│   ├── api/            # 后端 API (main.py)
│   └── ui/
│       └── static/     # 前端静态资源 (index.html + marked.js)
├── data/
│   ├── docs/           # 原始实验文档 (Markdown/PDF/PPT/Word)
│   ├── assets/         # [NEW] 从文档提取的图片
│   ├── vector_store/   # ChromaDB 向量数据库
│   ├── sessions/       # 对话历史存档 (*.json)
│   └── users.json      # 用户账户数据
├── scripts/            # 数据处理脚本
├── requirements.txt    # 项目依赖
└── start.sh            # 启动脚本
```

## 🔌 API 接口说明

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| POST | `/auth/register` | 学生注册 (学号+密码) |
| POST | `/auth/login` | 学生登录 |
| POST | `/chat` | 发送对话请求，返回智能回复 |
| GET | `/chat/history` | 获取指定 Session 的历史记录 (高性能优化) |
| DELETE | `/chat/history` | 清空指定 Session 的内存及文件存档 |

# ✅ 已完成功能
- [x] 基础 RAG 问答流程 (支持 MD/PDF/DOCX/PPTX)
- [x] 历史记录与对话记忆 (基于文件持久化)
- [x] 用户注册与登录系统 (文件版 Auth)
- [x] 多实验上下文隔离 (基于学号+实验ID)
- [x] 前端 Markdown 渲染与代码高亮
- [x] 后端性能优化 (MemoryManager 解耦)
- [x] **多模态支持** (自动提取并理解文档插图)

# 📝 TODO
- 测试大模型能力边界
- 辅导配置步骤+原理讲解，详细讲解，最后补充引申
- 实际案例，商业场景应用
- 迁移至关系型数据库 (mysql)

