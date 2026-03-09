from src.memory.memory_manager import MemoryManager
from src.rag.rag_engine import RAGEngine
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.messages import HumanMessage, SystemMessage
import os
import base64
import re
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

class CoreAgent:
    """
    基于 LangChain 的核心智能体
    """

    def __init__(self, session_id: str):
        self.session_id = session_id
        self.memory = MemoryManager(session_id)
        self.rag = RAGEngine()
        
        # 初始化 LLM
        # 尝试从环境变量获取 Key，如果没有则回退到模拟模式或报错
        api_key = os.getenv("OPENAI_API_KEY")
        base_url = os.getenv("MODEL_API_BASE")
        model_name = os.getenv("MODEL_NAME") # 读取 .env 中的模型名称

        if api_key:
            print(f"🧠 Core Agent 使用模型: {model_name}")
            self.llm = ChatOpenAI(
                model=model_name,
                temperature=0.7,
                openai_api_base=base_url, # 适配火山引擎 Base URL
                openai_api_key=api_key
            )
        else:
            print("⚠️ 未检测到 OPENAI_API_KEY，Agent 将运行在仅检索/模拟模式")
            self.llm = None

    def _encode_image(self, image_path: str) -> str:
        """读取图片并转换为 Base64 字符串"""
        try:
            with open(image_path, "rb") as image_file:
                return base64.b64encode(image_file.read()).decode('utf-8')
        except Exception as e:
            print(f"⚠️ 图片读取失败 {image_path}: {e}")
            return None


    def chat_stream(self, user_query: str):
        """
        处理用户交互（支持多模态），返回生成器形式的流式输出
        yield 数据格式: JSON字符串 + 换行符
        """
        import json
        
        def _yield_data(type_str, content):
            return json.dumps({"type": type_str, "content": content}, ensure_ascii=False) + "\n"

        # 1. 获取上下文
        yield _yield_data("status", "正在加载历史对话...")
        history_msgs = self.memory.get_context() 
        chat_history_str = ""
        for msg in history_msgs:
            role = "学生" if msg["role"] == "user" else "助教"
            chat_history_str += f"{role}: {msg['content']}\n"

        # 2. RAG 检索
        yield _yield_data("status", "正在执行混合检索(Vector + BM25)...")
        print(f"🤖 Agent 思考中: {user_query}")
        
        # 捕获日志或直接从 retrieve 获取，这里我们为了简单直接在前端把 RAG 片段数量打印
        context = self.rag.retrieve(user_query, 4)
        print(f"【检索结果预览】：{context[:500]}...") # 仅打印前500字符避免刷屏
        
        yield _yield_data("status", f"混合检索完成，已获取 {context.count('[文档片段')} 条相关上下文片段。")
        
        # 3. 生成回答
        full_response = ""
        if self.llm:
            try:
                images = []
                def replace_image_tag(match):
                    path = match.group(1).strip()
                    if os.path.exists(path):
                        b64_img = self._encode_image(path)
                        if b64_img:
                            images.append(b64_img)
                            return f"[已加载图片: {os.path.basename(path)}]"
                    return "[图片加载失败]"

                clean_context = re.sub(r'image:(\S+)', replace_image_tag, context)

                system_text = f"""你是一个专业的计算机网络实验辅导助教。请根据以下参考资料和对话历史回答学生的问题。
如果参考资料中包含图片，请结合图片内容进行详细解答。
1. 优先使用以下【参考资料】中提供的内容回答。
2. 如果都没有答案，请坦诚告知学生。

参考资料 (知识库):
{clean_context}

对话历史:
{chat_history_str}
"""
                content_parts = [{"type": "text", "text": user_query}]
                for b64_img in images:
                    content_parts.append({
                        "type": "image_url",
                        "image_url": {"url": f"data:image/jpeg;base64,{b64_img}"}
                    })
                    print(f"向模型发送图片数据 ({len(b64_img)} chars)")

                messages = [
                    SystemMessage(content=system_text),
                    HumanMessage(content=content_parts)
                ]

                yield _yield_data("status", "模型思考中...")
                
                # 终极请求流式输出
                for chunk in self.llm.stream(messages):
                    if chunk.content:
                        full_response += chunk.content
                        yield _yield_data("chunk", chunk.content)

            except Exception as e:
                import traceback
                traceback.print_exc()
                full_response = f"❌ 模型调用失败: {str(e)}"
                yield _yield_data("chunk", full_response)
        else:
            full_response = f"收到问题: {user_query}\n\n[系统提示] 未配置 OPENAI_API_KEY，仅显示检索结果:\n{context}"
            yield _yield_data("chunk", full_response)

        # 4. 更新记忆
        yield _yield_data("status", "保存对话记录...")
        self.memory.add_interaction(user_query, full_response)
        yield _yield_data("done", "")
