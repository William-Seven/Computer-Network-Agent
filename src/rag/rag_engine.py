from typing import List
from langchain_chroma import Chroma
from langchain_community.embeddings import FakeEmbeddings
from dotenv import load_dotenv
import os

# 加载环境变量
load_dotenv()

# 火山引擎多模态嵌入
try:
    from volcenginesdkarkruntime import Ark
    HAS_VOLCENGINE = True
except ImportError:
    HAS_VOLCENGINE = False

# 自定义 VolcArkEmbeddings 类
class VolcArkEmbeddings:
    def __init__(self, api_key: str, model: str):
        if not HAS_VOLCENGINE:
            raise ImportError("请先安装 volcengine-sdk-arkruntime: pip install volcengine-sdk-arkruntime")
        self.client = Ark(api_key=api_key)
        self.model = model

    def embed_documents(self, texts: list) -> list:
        embeddings = []
        for t in texts:
            inputs = [{"type": "text", "text": str(t)}]
            resp = self.client.multimodal_embeddings.create(
                model=self.model,
                input=inputs
            )
            if hasattr(resp, "data") and hasattr(resp.data, "embedding"):
                embeddings.append(resp.data.embedding)
            else:
                raise ValueError(f"Unexpected response structure: {resp}")
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

            self.vector_store = Chroma(persist_directory=db_path, embedding_function=self.embedding.embed_query)
            print(f"✅ RAG Engine 加载成功，路径: {db_path}")
        except Exception as e:
            print(f"⚠️ RAG Engine 初始化失败: {e}")
            self.vector_store = None

    def retrieve(self, query: str, top_k: int = 3) -> str:
        if not self.vector_store:
            return "【系统提示】知识库未初始化，无法检索。"
        try:
            # 对用户 Query 生成嵌入向量
            query_embedding = self.embedding.embed_query(query)

            # 在向量库中进行检索
            docs = self.vector_store.similarity_search_by_vector(query_embedding, k=top_k)

            if not docs:
                return "【系统提示】未检索到相关文档。"

            # 格式化检索结果
            context = "\n\n".join([f"[文档片段 {i+1}]: {doc.page_content}" for i, doc in enumerate(docs)])
            return context
        except Exception as e:
            print(f"检索出错: {e}")
            return f"【系统提示】检索出错：{e}"