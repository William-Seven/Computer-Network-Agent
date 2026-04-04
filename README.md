# 🎓 计算机网络实践辅导系统 (CN-Agent)

基于 **LangChain** 智能体架构的计算机网络实验辅导系统，采用 **前后端分离** 模式开发。

## ✨ 核心特性

- **📚 多格式 RAG 问答**：支持 Markdown、PDF、Word、PPT 多种格式文档的解析与智能切分，让知识库构建更加灵活无缝。
- **🔍 混合检索 (Hybrid Search)**：引入 **结巴(Jieba)分词** 配合 **BM25 精细词频** 引擎，与大模型的高维 Vector 检索引擎相辅相成。通过 RRF (Reciprocal Rank Fusion) 倒数排序融合算法，大幅提升双路召回机制在中文长短语境下的匹配准确率。
- **🎯 二阶段精排 (Cross-Encoder Rerank)**：在 RRF 粗排之后截流 Top-N 候选集，本地挂载部署 `BAAI/bge-reranker-v2-m3` 交叉编码器进行深度字级语义注意力打分，最终提纯出极高相关度的 Top-4 交由 LLM，根治专有名词的“知识幻觉”与“中间遗忘”。
- **👁️ 多模态视觉感知**：自动从 PDF 中提取图片并进行向量化，Agent 能够结合图片内容（如网络拓扑图、实验结果截图）回答问题。同时支持**前端直接上传图片**，用户可发送实验报错截图或网络拓扑图，系统将通过 Vision 大模型直接解析上传图片并结合当前上下文给出解答。
- **🌐 智能联网搜索**：内置 Tool Calling 工具调用机制并实现容错解析以应对裸 JSON 输出异常。当本地实验指导书知识库无法命中或涉及前沿资讯时，Agent 会自动调用搜索引擎获取最新网络数据补充解答。
- **🌊 流式输出与极速响应**：全面支持基于 Server-Sent Events (SSE) 的流式响应，重构底层的 Agent 调度机制，极大地降低了 TTFB (首字节时间)。前端实时显示 Agent "正在思考"、等内部状态，最终以打字机效果流畅呈现，彻底消除长耗时的等待体验。
- **📈 跨实验全局学情总结**：突破局部对话限制，系统能自动聚合学生在所有不同实验中的交互与求助历史。通过后台 LLM 进行深度跨会话（Cross-Session）学情分析，能够一键生成专属的“个人问题总结”诊断报告，精准定位知识薄弱点，提供定制化学习建议。前端采用无缝内联视图，并实现了完备的状态锁保护。
- **🧠 持久化记忆**：支持多轮对话，对话记录自动保存至本地 JSON 文件，服务重启不丢失。
- **🔐 用户身份认证**：内置轻量级账号系统，支持学生注册/登录，保障学习数据的私密性与安全性。
- **🔄 智能会话隔离**：基于`学号 + 实验ID`的双重维度隔离对话历史，支持跨设备同步学习进度。
- **🎨 交互体验升级**：前端支持 Markdown/代码高亮，全屏登录遮罩，以及一键注销功能。

## 🏗️ 架构设计

### 1. 核心技术栈
- **环境管理**: Conda (Python 3.11)
- **Agent 框架**: LangChain (ReAct / OpenAI Functions)
- **后端服务**: FastAPI
- **认证模块**: AuthManager (SHA256 加密)
- **前端架构**: 原生 HTML/JS SPA
- **检索数据库**: ChromaDB (Vector) + rank_bm25 (Inverted Index) + bge-reranker-v2-m3
- **数据存储**: 
  - `data/sessions/`: 对话历史 (*.json)
  - `data/summaries/`: 学情与问题诊断评估文档存档 (*.md)
  - `data/users.json`: 用户账户信息
  - `data/assets/`: 提取的图片资源

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
使用一键启动脚本：
```bash
chmod +x start.sh
./start.sh
```
- 直接访问及测试: `http://localhost:8111`

## 📁 目录结构
```
cn-agent/
├── src/
│   ├── core/           
│   │   ├── agent.py    # Agent 核心逻辑 (流式状态反馈、工具解析修正)
│   │   ├── auth.py     # 用户认证管理
│   │   └── summary.py  # 全局跨系统交互历史学情评价与分析管理器
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
|
├── data/
│   ├── docs/           # 原始实验文档 (Markdown/PDF/PPT/Word)
│   ├── assets/         # 从文档提取的图片
│   ├── vector_store/   # ChromaDB 向量数据库
│   ├── bm25_index.pkl  # 全局 BM25 中英文倒排语料库
│   ├── sessions/       # 对话历史存档 (*.json)
│   ├── summaries/      # LLM 批量生成的 Markdown 格式学情跨域总结报告存档 
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
| POST | `/chat/stream` | 发送对话请求，支持流式输出、图片上传（Base64解析），并返回 Agent 实时的中间打分 及混合检索状态 |
| GET | `/chat/history` | 获取指定 Session 的历史记录 (高性能优化) |
| DELETE | `/chat/history` | 清空指定 Session 的内存及文件存档 |
| POST | `/summary/generate` | 跨所有会话分析，调用 LLM 全局评估学生存在的技能缺陷或薄弱项，并生成报告 |
| GET | `/summary/{student_id}` | 获取指定学生的全部已生成评估诊断总结卡片 |

# ✅ 已完成功能
- [x] 基础 RAG 问答流程 (支持 MD/PDF/DOCX/PPTX)
- [x] 历史记录与对话记忆 (基于文件持久化)
- [x] 用户注册与登录系统 (文件版 Auth)
- [x] 多实验上下文隔离 (基于学号+实验ID)
- [x] 前端 Markdown 渲染与代码高亮
- [x] 后端性能优化 (MemoryManager 解耦)
- [x] 彻底解决前后端分离导致的异域跨域端口痛点，集成 StaticFiles 静态代理
- [x] 修复长后端守护进程使用 `nohup` 时的日志缓存卡死问题 (`-u` Unbuffered IO)
- [x] **多模态支持** (自动提取并理解文档插图)
- [x] **智能联网搜索整合** (Agent Tool Calling 动态调用 DuckDuckGo 获取最新知识)
- [x] **流式输出体验升级** (实时状态提示与打字机回复呈现，大幅降低请求超时假死等待时长)
- [x] **双路混合检索召回** (引入结巴分词 `Jieba` 与 `BM25` 精准词频检索，结合超高维纯语义 Vector 向量，采用 RRF 倒数融合算法大幅提升中文复杂混淆语境下长短本召回率)
- [x] **二阶段深度神经网络精排架构** (加载国内环境加速优化后的 `BAAI/bge-reranker-v2-m3`。以“扩大粗排池Top-15 -> 深度注意打分 -> 提纯压至最终Top-4”黄金配比解决语言模型常见 Lost in the Middle 记忆遗忘问题)
- [x] **前端多模态交互(图片直接上传)** (在聊天界面新增“+”号按钮，支持将用户挑选的图片进行 Base64 编码，联动后台大模型 `HumanMessage` 提供真实的图文并茂问答诊断)
- [x] **Time to First Byte(TTFB) 极速流式重构** (抛弃以往 Langchain 阻塞的 `invoke` 串行机制，改为从实时抓取 `AIMessageChunk` 工具执行中间态，几乎消除了“思考中”网络超时的长时等待黑窗感)
- [x] **全局个人问题学情诊断体系** (后台开发 `SummaryManager` 实时聚合并提纯跨实验、跨知识域的 `sess_{id}_x.json` 文件资源；前台中内联展示无缝的实验界面切换，完美解决了生成状态重置丢失等 UX 的核心痛点)

# 📝 TODO
- 辅导配置步骤+原理讲解，详细讲解，最后补充引申
- 各功能 功能栏
- 配置计算机网络实践平台