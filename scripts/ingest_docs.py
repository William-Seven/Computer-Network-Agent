import os
import sys
import pickle
from langchain_community.retrievers import BM25Retriever
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from langchain_community.document_loaders import DirectoryLoader, TextLoader, Docx2txtLoader
from src.rag.ppt_loader import SimplePPTXLoader
from src.rag.pdf_loader import MultimodalPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma
from langchain_community.embeddings import FakeEmbeddings
from langchain_core.embeddings import Embeddings
from langchain_community.retrievers import BM25Retriever
import pickle

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
        """
        支持文本和图片的混合列表。
        如果是图片路径（以 image: 开头），则读取图片并进行 Base64 编码发送。
        """
        import base64

        embeddings = []
        total_texts = len(texts)
        for idx, t in enumerate(texts):
            # 简单的多模态协议：如果文本以 "image:" 开头，则视为图片路径
            if str(t).startswith("image:") and os.path.exists(str(t)[6:]):
                image_path = str(t)[6:].strip()
                try:
                    with open(image_path, "rb") as image_file:
                        encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
                    inputs = [{"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{encoded_string}"}}]
                    print(f"[{idx + 1}/{total_texts}] 🖼️ 正在向量化图片: {image_path}")
                except Exception as e:
                    print(f"[{idx + 1}/{total_texts}] ⚠️ 图片读取失败 {image_path}: {e}, 降级为纯文本处理")
                    inputs = [{"type": "text", "text": str(t)}]
            else:
                # 普通文本，并打印此时是第几个文本块
                print(f"[{idx + 1}/{total_texts}] 📝 正在向量化文本块... (长度: {len(str(t))})")
                inputs = [{"type": "text", "text": str(t)}]

            try:
                resp = self.client.multimodal_embeddings.create(
                    model=self.model,
                    input=inputs
                )
                # 兼容 resp.data 直接是对象的情况
                if hasattr(resp, "data") and hasattr(resp.data, "embedding"):
                    embeddings.append(resp.data.embedding)
                else:
                    raise ValueError(f"Unexpected response structure: {resp}")
            except Exception as e:
                print(f"❌ Embedding API Error for input '{str(t)[:50]}...': {e}")
                # 发生错误时填充零向量或跳过，这里选择抛出以便调试
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

import shutil

def ingest_docs():
    docs_path = "./data/docs"
    db_path = "./data/vector_store"

    # 0. 清理旧向量库 (确保全量重建)
    if os.path.exists(db_path):
        print(f"🧹 清理旧向量库: {db_path}")
        shutil.rmtree(db_path)
    
    print(f"🚀 开始构建知识库，源目录: {docs_path}")

    # 1. 加载文档
    loaders = [
        # Markdown
        DirectoryLoader(docs_path, glob="**/*.md", loader_cls=TextLoader),
        # PDF (多模态) - 禁用多线程以确保图片提取日志可见且不冲突
        DirectoryLoader(docs_path, glob="**/*.pdf", loader_cls=MultimodalPDFLoader, use_multithreading=False),
        # Word (.docx)
        DirectoryLoader(docs_path, glob="**/*.docx", loader_cls=Docx2txtLoader),
        # PPT (.pptx) - 使用自定义轻量级 Loader
        DirectoryLoader(docs_path, glob="**/*.pptx", loader_cls=SimplePPTXLoader),
    ]

    documents = []
    print(f"🔍 正在扫描文档 (md, pdf, docx, pptx)...")
    for loader in loaders:
        try:
            loaded_docs = loader.load()
            if loaded_docs:
                print(f"  - 发现 {len(loaded_docs)} 页内容来自 {loader.loader_cls.__name__}")
                documents.extend(loaded_docs)
        except Exception as e:
            print(f"⚠️ {loader.loader_cls.__name__} 加载失败或无匹配文件: {e}")

    if not documents:
        print("❌ 未找到有效文档，请检查 data/docs/ 目录")
        return

    print(f"📄 加载了 {len(documents)} 个文档")

    # 2. 文本切分
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=800, chunk_overlap=200)
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
        # 4. 构建并保存 BM25 检索器 (用于混合检索)
        print("🔍 正在构建 BM25 关键词索引...")
        from src.rag.bm25_utils import jieba_preprocess
        
        bm25_retriever = BM25Retriever.from_documents(splits, preprocess_func=jieba_preprocess)
        bm25_retriever.k = 4
        bm25_path = "./data/bm25_index.pkl"
        with open(bm25_path, "wb") as f:
            pickle.dump(bm25_retriever, f)
        print(f"✅ BM25 关键词索引保存成功！路径: {bm25_path}")
    except Exception as e:
        print(f"❌ 向量化失败: {e}")

if __name__ == "__main__":
    ingest_docs()
