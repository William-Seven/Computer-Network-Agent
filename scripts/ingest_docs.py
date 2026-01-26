import os
import sys
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from langchain_community.document_loaders import DirectoryLoader, TextLoader, PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma
from langchain_community.embeddings import FakeEmbeddings
from langchain_core.embeddings import Embeddings

# 火山引擎多模态嵌入
try:
    from volcenginesdkarkruntime import Ark
    HAS_VOLCENGINE = True
except ImportError:
    HAS_VOLCENGINE = False

class VolcArkEmbeddings(Embeddings):
    """火山引擎自定义 Embeddings，支持多模态（文本、图片）"""
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
            # 兼容 resp.data 直接是对象的情况
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

def ingest_docs():
    docs_path = "./data/docs"
    db_path = "./data/vector_store"

    print(f"🚀 开始构建知识库，源目录: {docs_path}")

    # 1. 加载文档
    loaders = [
        DirectoryLoader(docs_path, glob="**/*.md", loader_cls=TextLoader),
        # 如需支持 PDF，取消注释下一行
        # DirectoryLoader(docs_path, glob="**/*.pdf", loader_cls=PyPDFLoader),
    ]

    documents = []
    for loader in loaders:
        try:
            documents.extend(loader.load())
        except Exception as e:
            print(f"⚠️ 加载部分文档失败: {e}")

    if not documents:
        print("❌ 未找到有效文档，请检查 data/docs/ 目录")
        return

    print(f"📄 加载了 {len(documents)} 个文档")

    # 2. 文本切分
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=100)
    splits = text_splitter.split_documents(documents)
    print(f"✂️ 切分为 {len(splits)} 个文本块")

    # 3. 向量化并存储
    try:
        # 火山引擎配置
        api_key = os.getenv("ARK_API_KEY")
        model_name = os.getenv("EMBEDDING_MODEL")  # 推荐 "doubao-embedding-vision-250615"

        if api_key and model_name and HAS_VOLCENGINE:
            print(f"🔑 使用火山引擎 Embeddings: {model_name}")
            embedding = VolcArkEmbeddings(api_key=api_key, model=model_name)
        else:
            print("⚠️ 未配置 API Key/Model 或未安装 SDK，切换为【模拟模式】(FakeEmbeddings)...")
            embedding = FakeEmbeddings(size=1536)

        vectordb = Chroma.from_documents(documents=splits, embedding=embedding, persist_directory=db_path)

        print(f"✅ 向量库构建完成！存储路径: {db_path}")
    except Exception as e:
        print(f"❌ 向量化失败: {e}")

if __name__ == "__main__":
    ingest_docs()