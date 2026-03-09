# 🎓 计算机网络实践辅导系统 (CN-Agent)

基于 **LangChain** 智能体架构的计算机网络实验辅导系统，采用 **前后端分离** 模式开发。

## ✨ 核心特性

- **📚 多格式 RAG 问答**：支持 Markdown、PDF、Word、PPT 多种格式文档的解析与智能切分，让知识库构建更加灵活无缝。
- **🔍 混合检索 (Hybrid Search)**：引入 **结巴(Jieba)分词** 配合 **BM25 精细词频** 引擎，与大模型的高维 Vector 检索引擎相辅相成。通过 RRF (Reciprocal Rank Fusion) 倒数排序融合算法，大幅提升双路召回机制在中文长短语境下的匹配准确率。
- **👁️ 多模态视觉感知**：自动从 PDF 中提取图片并进行向量化，Agent 能够结合图片内容（如网络拓扑图、实验结果截图）回答问题。
- **🌐 智能联网搜索**：内置 Tool Calling 工具调用机制并实现容错解析以应对裸 JSON 输出异常。当本地实验指导书知识库无法命中或涉及前沿资讯时，Agent 会自动调用 DuckDuckGo 搜索引擎获取最新网络数据补充解答。
- **🌊 流式输出与状态感知**：全面支持基于 Server-Sent Events (SSE) 的流式响应。前端实时显示 Agent "正在加载历史"、"执行混合检索(Vector + BM25)"、"正在调用外部工具: internet_search" 等思考内部状态，最终以打字机效果流畅呈现，消除首字节焦虑等待体验。
- **🧠 持久化记忆**：支持多轮对话，对话记录自动保存至本地 JSON 文件，服务重启不丢失。
- **🔐 用户身份认证**：内置轻量级账号系统，支持学生注册/登录，保障学习数据的私密性与安全性。
- **🔄 智能会话隔离**：基于`学号 + 实验ID`的双重维度隔离对话历史，支持跨设备同步学习进度。
- **🎨 交互体验升级**：前端支持 Markdown/代码高亮，全屏登录遮罩，以及一键注销功能。

## 🏗️ 架构设计

### 1. 核心技术栈
- **环境管理**: Conda (Python 3.11)
- **Agent 框架**: LangChain (ReAct / OpenAI Functions)
- **后端服务**: FastAPI (Port 8111)
- **认证模块**: AuthManager (SHA256 加密)
- **前端架构**: 原生 HTML/JS SPA (Port 8222)
- **检索数据库**: ChromaDB (Vector) + rank_bm25 (Inverted Index)
- **数据存储**: 
  - `data/sessions/`: 对话历史 (*.json)
  - `data/users.json`: 用户账户信息
  - `data/assets/`: 提取的图片资源

### 2. 端口规划
| 服务     | 端口     | 说明                                    |
| -------- | -------- | --------------------------------------- |
| 后端 API | **8111** | 提供 `/chat/stream` 等核心接口，支持 CORS |
| 前端 UI  | **8222** | 静态页面服务，通过 Fetch 调用 8111 接口 |

## 🚀 快速开始

### 1. 环境准备
```bash
# 创建 Conda 环境
conda create -n cn-agent python=3.11

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

### 3. 构建知识库与混合检索引擎
将实验指导书（支持 .md, .pdf, .docx, .pptx）放入 `data/docs/` 目录，然后运行：
```bash
python3 scripts/ingest_docs.py
```
*此操作将在 `data/` 目录下同时生成 Chroma 结构化向量库及 `bm25_index.pkl` 中英文切词索引倒排词库。*

### 4. 启动服务
使用一键启动脚本（分别轮询启动前后端）：
```bash
chmod +x start.sh
./start.sh start
# 如果需要热更新可执行: ./start.sh restart
```
- 测试后端: `http://localhost:8111`
- 访问前端: `http://localhost:8222`

## 📁 目录结构
```
cn-agent/
├── src/
│   ├── core/           
│   │   ├── agent.py    # Agent 核心逻辑 (流式状态反馈、工具解析修正)
│   │   └── auth.py     # 用户认证管理
│   ├── rag/            # 知识库引擎
│   │   ├── pdf_loader.py  # 多模态 PDF 加载器
│   │   ├── bm25_utils.py  # 全局中英文分词拦截器
│   │   └── rag_engine.py  # 核心 RRF 融合检索逻辑
│   ├── memory/         # 记忆管理 (MemoryManager)
|   |   └── memory_manager.py
│   ├── tools/          # 工具链封装
│   │   └── search_tool.py # 联网搜索引擎工具 (DuckDuckGo封装)
│   ├── api/            # 后端 API
|   |   └── main.py
│   └── ui/
│       └── static/     # 前端静态资源 (index.html)
├── data/
│   ├── docs/           # 原始实验文档 (Markdown/PDF/PPT/Word)
│   ├── assets/         # 从文档提取的图片
│   ├── vector_store/   # ChromaDB 向量数据库
│   ├── bm25_index.pkl  # 全局 BM25 中英文倒排语料库
│   ├── sessions/       # 对话历史存档 (*.json)
│   └── users.json      # 用户账户数据
|
├── scripts/            # 数据处理与向量化脚本
├── requirements.txt    # 项目依赖
└── start.sh            # 启动脚本
```

## 🔌 API 接口说明

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| POST | `/auth/register` | 学生注册 (学号+密码) |
| POST | `/auth/login` | 学生登录 |
| POST | `/chat/stream` | 发送对话请求，支持流式输出并返回 Agent 实时的中间打分及混合检索打分状态 |
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
- [x] **智能联网搜索整合** (Agent Tool Calling 动态调用 DuckDuckGo 获取最新知识)
- [x] **流式输出体验升级** (实时状态提示与打字机回复呈现，大幅降低请求超时假死等待时长)
- [x] **双语 Hybrid 混合检索** (引入结巴分词 `jieba` 与 `BM25` 精准词频检索，结合纯语义 Vector 向量，基于 RRF 倒数融合算法提升中文语境多路长短本文的命中准确率)

# 📝 TODO
- 测试大模型能力边界
- 辅导配置步骤+原理讲解，详细讲解，最后补充引申
- 迁移至关系型数据库 (mysql)
