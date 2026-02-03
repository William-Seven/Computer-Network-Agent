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

    def chat(self, user_query: str) -> str:
        """
        处理用户交互（支持多模态）
        """
        # 1. 获取上下文
        history_msgs = self.memory.get_context() 
        chat_history_str = ""
        for msg in history_msgs:
            role = "学生" if msg["role"] == "user" else "助教"
            chat_history_str += f"{role}: {msg['content']}\n"

        # 2. RAG 检索
        print(f"🤖 Agent 思考中: {user_query}")
        context = self.rag.retrieve(user_query, 2) # 召回 Top 2
        print(f"【检索结果预览】：{context[:200]}...") # 仅打印前200字符避免刷屏
        
        # 3. 生成回答
        if self.llm:
            try:
                # --- 多模态处理逻辑 ---
                # 检查 context 中是否包含 "image:path" 格式的标记
                # 简单的正则匹配：image:(\S+)
                images = []
                
                def replace_image_tag(match):
                    path = match.group(1).strip()
                    if os.path.exists(path):
                        b64_img = self._encode_image(path)
                        if b64_img:
                            images.append(b64_img)
                            return f"[已加载图片: {os.path.basename(path)}]"
                    return "[图片加载失败]"

                # 替换文本中的图片路径标记，同时收集 Base64 图片
                clean_context = re.sub(r'image:(\S+)', replace_image_tag, context)

                # 构建 System Prompt
                system_text = f"""你是一个专业的计算机网络实验辅导助教。请根据以下参考资料和对话历史回答学生的问题。
如果参考资料中包含图片，请结合图片内容进行详细解答。
如果参考资料中没有答案，请基于你的专业知识回答，但要告知学生这不在实验手册中。

参考资料 (知识库):
{clean_context}

对话历史:
{chat_history_str}
"""
                
                # 构建 User Message (混合文本和图片)
                content_parts = [{"type": "text", "text": user_query}]
                
                for b64_img in images:
                    content_parts.append({
                        "type": "image_url",
                        "image_url": {"url": f"data:image/jpeg;base64,{b64_img}"}
                    })
                    print(f"🖼️ 向模型发送图片数据 ({len(b64_img)} chars)")

                messages = [
                    SystemMessage(content=system_text),
                    HumanMessage(content=content_parts)
                ]

                # 调用模型
                response_msg = self.llm.invoke(messages)
                response = response_msg.content
                
            except Exception as e:
                import traceback
                traceback.print_exc()
                response = f"❌ 模型调用失败: {str(e)}"
        else:
            # 降级模式 (无 Key 时)
            response = f"收到问题: {user_query}\n\n[系统提示] 未配置 OPENAI_API_KEY，仅显示检索结果:\n{context}"

        # 4. 更新记忆
        self.memory.add_interaction(user_query, response)
        
        return response