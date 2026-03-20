from typing import List
from langchain_chroma import Chroma
from langchain_community.embeddings import FakeEmbeddings
from langchain_core.embeddings import Embeddings
from langchain_community.retrievers import BM25Retriever
from dotenv import load_dotenv
import os
import base64
import pickle
import sys
from sentence_transformers import CrossEncoder

# 显式导入自定义结巴分词模块，确保 pickle 反序列化时能找到命名空间
try:
    from src.rag.bm25_utils import jieba_preprocess
except ImportError:
    pass

# 加载环境变量
load_dotenv()

# 火山引擎多模态嵌入
try:
    from volcenginesdkarkruntime import Ark
    HAS_VOLCENGINE = True
except ImportError:
    HAS_VOLCENGINE = False

# 自定义 VolcArkEmbeddings 类
class VolcArkEmbeddings(Embeddings):
    """火山引擎自定义 Embeddings，支持多模态（文本、图片）"""
    def __init__(self, api_key: str, model: str):
        if not HAS_VOLCENGINE:
            raise ImportError("请先安装 volcengine-sdk-arkruntime: pip install volcengine-sdk-arkruntime")
        self.client = Ark(api_key=api_key)
        self.model = model

    def embed_documents(self, texts: list) -> list:
        """
        支持文本和图片的混合列表。
        如果是图片路径（以 image: 开头），则读取图片并进行 Base64 编码发送。
        """
        embeddings = []
        for t in texts:
            # 简单的多模态协议：如果文本以 "image:" 开头，则视为图片路径
            if str(t).startswith("image:") and os.path.exists(str(t)[6:]):
                image_path = str(t)[6:].strip()
                try:
                    with open(image_path, "rb") as image_file:
                        encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
                    inputs = [{"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{encoded_string}"}}]
                    print(f"🖼️ 正在向量化图片: {image_path}")
                except Exception as e:
                    print(f"⚠️ 图片读取失败 {image_path}: {e}, 降级为纯文本处理")
                    inputs = [{"type": "text", "text": str(t)}]
            else:
                # 普通文本
                inputs = [{"type": "text", "text": str(t)}]

            try:
                resp = self.client.multimodal_embeddings.create(
                    model=self.model,
                    input=inputs
                )
                if hasattr(resp, "data") and hasattr(resp.data, "embedding"):
                    embeddings.append(resp.data.embedding)
                else:
                    raise ValueError(f"Unexpected response structure: {resp}")
            except Exception as e:
                print(f"❌ Embedding API Error: {e}")
                # 出错时抛出，避免脏数据
                raise e
        return embeddings

    def embed_query(self, text: str) -> list:
        inputs = [{"type": "text", "text": str(text)}]
        resp = self.client.multimodal_embeddings.create(
            model=self.model,
            input=inputs
        )
        if hasattr(resp, "data") and hasattr(resp.data, "embedding"):
            return resp.data.embedding
        else:
            raise ValueError(f"Unexpected response structure: {resp}")

# RAG 引擎
class RAGEngine:
    def __init__(self, db_path: str = "./data/vector_store"):
        try:
            api_key = os.getenv("ARK_API_KEY")
            model_name = os.getenv("EMBEDDING_MODEL")

            if api_key and model_name and HAS_VOLCENGINE:
                print(f"🔑 使用火山引擎 Embeddings: {model_name}")
                self.embedding = VolcArkEmbeddings(api_key=api_key, model=model_name)
            else:
                print("⚠️ 未配置 Key 或 Model，运行在模拟模式 (FakeEmbeddings)")
                self.embedding = FakeEmbeddings(size=1536)

            self.vector_store = Chroma(persist_directory=db_path, embedding_function=self.embedding)
            print(f"✅ RAG Engine 加载成功，路径: {db_path}")
            
            # 加载 BM25 检索器
            bm25_path = "./data/bm25_index.pkl"
            if os.path.exists(bm25_path):
                with open(bm25_path, "rb") as f:
                    self.bm25_retriever = pickle.load(f)
                print("✅ BM25 关键词检索器加载成功！")
            else:
                print("⚠️ 未找到 BM25 索引文件，将退化为纯向量检索。")
                self.bm25_retriever = None


            try:
                print("🚀 正在加载 BGE-Reranker 模型到显存...")
                model_path = "/root/autodl-tmp/cn-agent/models/bge-reranker-v2-m3"
                if os.path.exists(model_path):
                    self.reranker = CrossEncoder(model_path, max_length=2048, device="cuda")
                    print("✅ BGE-Reranker 加载成功！")
                else:
                    self.reranker = None
                    print("⚠️ BGE-Reranker 模型目录不存在，已跳过精排阶段。")
            except Exception as e:
                self.reranker = None
                print(f"⚠️ BGE-Reranker 加载失败: {e}")

        except Exception as e:
            print(f"⚠️ RAG Engine 初始化失败: {e}")
            self.vector_store = None
            self.bm25_retriever = None

    def retrieve(self, query: str, top_k1: int = 20, top_k2: int = 4) -> str:
        if not self.vector_store:
            return "【系统提示】知识库未初始化，无法检索。"
        try:
            print(f"🔍 收到检索请求: {query}")
            
            # 如果加载了 BM25，则使用 Hybrid Search
            if self.bm25_retriever:
                # 1. 向量检索召回
                print("🧪 正在执行混合检索(Vector + BM25)...")
                query_embedding = self.embedding.embed_query(query)
                vector_docs = self.vector_store.similarity_search_by_vector(query_embedding, k=top_k1)
                
                # 2. BM25 关键词检索召回
                self.bm25_retriever.k = top_k1
                bm25_docs = self.bm25_retriever.invoke(query)
                
                # 3. RRF (Reciprocal Rank Fusion) 倒数排序融合算法
                k = 60
                rrf_scores = {}
                doc_map = {}
                source_tracker = {} # 记录片段来源：'Vector', 'BM25', 或 'Both'
                
                print(f"📊 Vector召回数量: {len(vector_docs)} | BM25召回数量: {len(bm25_docs)}")
                
                for rank, doc in enumerate(vector_docs):
                    text = doc.page_content
                    # 向量检索得分
                    rrf_scores[text] = rrf_scores.get(text, 0) + 1.0 / (k + rank + 1)
                    doc_map[text] = doc
                    source_tracker[text] = "Vector"
                    
                for rank, doc in enumerate(bm25_docs):
                    text = doc.page_content
                    # BM25 检索得分
                    rrf_scores[text] = rrf_scores.get(text, 0) + 1.0 / (k + rank + 1)
                    doc_map[text] = doc
                    if text in source_tracker:
                        source_tracker[text] = "Both (Vector+BM25)"
                    else:
                        source_tracker[text] = "BM25"
                    
                # 根据 RRF 得分降序排序
                sorted_docs_rrf = sorted(doc_map.values(), key=lambda doc: rrf_scores[doc.page_content], reverse=True)
                # ------ 引入 BGE 重排 ------
                if getattr(self, "reranker", None) is not None:
                    print("📉 正在执行 BGE-Reranker 二阶段重排...")
                    # 扩大初筛数量交由 Reranker 排序 (取 RRF 的 Top-15)
                    candidate_docs = sorted_docs_rrf[:15]
                    # 构造交叉编码 (Cross-Encoding) 必须的数据对： [[问题, 文档1], [问题, 文档2]...]
                    pairs = [[query, doc.page_content] for doc in candidate_docs]
                    # 这就是该模型的核心能力：打分！(范围通常在极低的负数到几十以内的正数之间，分越高代表越完美匹配)
                    scores = self.reranker.predict(pairs)
                    # 捆绑分数和文档
                    scored_docs = list(zip(candidate_docs, scores))
                    scored_docs.sort(key=lambda x: x[1], reverse=True)
                    # 最后我们只需要最开始要求的 top_k (一般是4个)
                    docs = [doc for doc, _ in scored_docs[:top_k2]]
                    
                    print("--- 🏆 重排 (Reranker) 最终得分详情 ---")
                    for i, (doc, score) in enumerate(scored_docs[:top_k2]):
                        source = source_tracker[doc.page_content]
                        snip = doc.page_content.replace("\n", " ")[:50]
                        print(f"TOP {i+1} | Source: {source: <18} | Cross-Score: {score:.5f} | Snippet: {snip}...")
                    print("----------------------------------------")
                else:
                    docs = sorted_docs_rrf[:top_k2]
                
                    print("--- 🏆 混合检索 (RRF) 最终得分详情 ---")
                    for i, doc in enumerate(docs):
                        score = rrf_scores[doc.page_content]
                        source = source_tracker[doc.page_content]
                        snip = doc.page_content.replace('\n', ' ')[:50]
                        print(f"TOP {i+1} | Source: {source: <18} | Score: {score:.5f} | Snippet: {snip}...")
                    print("----------------------------------------")
                
            else:
                # 降级：仅使用纯向量检索
                print("🧪 正在执行纯向量检索...")
                query_embedding = self.embedding.embed_query(query)
                docs = self.vector_store.similarity_search_by_vector(query_embedding, k=top_k2)

            if not docs:
                return "【系统提示】未检索到相关文档。"

            # 格式化检索结果
            context = "\n\n".join([f"[文档片段 {i+1}]: {doc.page_content}" for i, doc in enumerate(docs)])
            return context
        except Exception as e:
            print(f"检索出错: {e}")
            return f"【系统提示】检索出错：{e}"