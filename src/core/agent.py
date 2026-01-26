from src.memory.memory_manager import MemoryManager
from src.rag.rag_engine import RAGEngine
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
import os
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

    def chat(self, user_query: str) -> str:
        """
        处理用户交互
        """
        # 1. 获取上下文
        # history = self.memory.get_context() # 暂未直接传给 LLM，可视需求格式化为 history string
        
        # 2. RAG 检索
        print(f"🤖 Agent 思考中: {user_query}")
        context = self.rag.retrieve(user_query, 2)
        print(f"【检索结果】：{context}")
        
        # 3. 生成回答
        if self.llm:
            try:
                # 定义 Prompt
                prompt = ChatPromptTemplate.from_template("""
                你是一个专业的计算机网络实验辅导助教。请根据以下参考资料回答学生的问题。
                如果参考资料中没有答案，请基于你的专业知识回答，但要告知学生这不在实验手册中。
                
                参考资料 (知识库):
                {context}
                
                学生问题: {query}
                """)
                
                # LCEL 链
                chain = prompt | self.llm | StrOutputParser()
                response = chain.invoke({"context": context, "query": user_query})
                
            except Exception as e:
                response = f"❌ 模型调用失败: {str(e)}"
        else:
            # 降级模式 (无 Key 时)
            response = f"收到问题: {user_query}\n\n[系统提示] 未配置 OPENAI_API_KEY，仅显示检索结果:\n{context}"

        # 4. 更新记忆
        self.memory.add_interaction(user_query, response)
        
        return response