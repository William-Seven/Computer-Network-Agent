from src.memory.memory_manager import MemoryManager
from src.rag.rag_engine import RAGEngine
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage
from src.tools.search_tool import internet_search
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
            
            # --- 初始化工具 ---
            self.tools = [internet_search]
            self.llm_with_tools = self.llm.bind_tools(self.tools)
        else:
            print("⚠️ 未检测到 OPENAI_API_KEY，Agent 将运行在仅检索/模拟模式")
            self.llm = None
            self.llm_with_tools = None

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
        context = self.rag.retrieve(user_query, 4) # 召回 Top 4
        print(f"【检索结果预览】：{context[:500]}...") # 仅打印前500字符避免刷屏
        
        # 3. 生成回答
        if self.llm_with_tools:
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
1. 优先使用以下【参考资料】中提供的内容回答。
2. 如果参考资料不足以回答，或学生问题涉及最新前沿知识、外部工具的使用，请你调用工具进行联网搜索。
3. 如果都没有答案，请坦诚告知学生。

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

                # ==========================
                # Agent 执行与 工具调用逻辑循环
                # ==========================
                response_msg = self.llm_with_tools.invoke(messages)
                
                # 判断大模型是否打算使用工具
                if response_msg.tool_calls:
                    # ==========================
                    # 兼容性修复: 火山引擎豆包等国内大模型，在第二轮工具回调时
                    # 对标准的 ToolMessage Message Tree 兼容性不好，容易返回空字符。
                    # 我们需要将工具调用结果扁平化为纯文本，重新用一轮普通对话组装！
                    # ==========================
                    search_results_text = ""
                    for tool_call in response_msg.tool_calls:
                        tool_name = tool_call["name"]
                        tool_args = tool_call["args"]
                        
                        print(f"🛠️ Agent 决定调用工具: {tool_name}, 参数: {tool_args}")
                        
                        # 真正执行搜索
                        if tool_name == "internet_search":
                            tool_result = internet_search.invoke(tool_args)
                            print(f"🔍 工具返回结果: {str(tool_result)[:200]}...")
                            search_results_text += f"\n【{tool_name} 检索结果】:\n{tool_result}\n"
                        else:
                            search_results_text += f"\n【{tool_name}】未找到此工具。\n"
                    
                    # 重新构造用户的提示词，将搜索内容强行塞进去，避开 Message 树状黑洞
                    new_knowledge_prompt = f"""由于本地资料不满足要求，我为你执行了外部工具调用。
以下是外部工具调用的返回结果：
{search_results_text}

请基于上述【外部工具返回结果】以及之前的对话内容，回答我的问题。
【我的问题是】: {user_query}
"""
                    # 注意我们不修改 content_parts 的图片结构，只把新的 prompt 追加为最后一条 HumanMessage
                    content_parts_new = [{"type": "text", "text": new_knowledge_prompt}]
                    for b64_img in images:
                        content_parts_new.append({
                            "type": "image_url",
                            "image_url": {"url": f"data:image/jpeg;base64,{b64_img}"}
                        })
                        
                    flat_messages = [
                        SystemMessage(content=system_text),
                        HumanMessage(content=content_parts_new) 
                    ]

                    # 终极请求：使用没有绑定 Tool 的原始 LLM 强制归纳
                    final_response_msg = self.llm.invoke(flat_messages)
                    response = final_response_msg.content
                    
                    if not response:
                        response = "我查找到了一些信息，但由于大模型内容过滤或截断，暂时无法显示最终结果。请您尝试更换搜索问题或直接参考相关技术博客。"
                else:
                    # 如果一开始没打算调用，说明 RAG 已经够了，直接输出文本内容
                    # 检查是否返回了特定占位插槽如 <｜tool calls begin｜>... 但没被框架解析！
                    if "<|tool" in response_msg.content or "<|plugin" in response_msg.content or "[{" in response_msg.content:
                        # 拦截并提示这种未经正确解析的裸字符串
                         response = f"我尝试去搜索相关的最新资讯，但遇到了调用解析问题。请重新提问或提供更准确的方向。"
                    else:
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