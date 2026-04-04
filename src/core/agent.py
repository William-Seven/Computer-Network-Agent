from src.memory.memory_manager import MemoryManager
from src.rag.rag_engine import RAGEngine
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.messages import HumanMessage, SystemMessage
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
        api_key = os.getenv("OPENAI_API_KEY")
        base_url = os.getenv("MODEL_API_BASE")
        model_name = os.getenv("MODEL_NAME")

        if api_key:
            print(f"🧠 Core Agent 使用模型: {model_name}")
            self.llm = ChatOpenAI(
                model=model_name,
                temperature=0.7,
                openai_api_base=base_url,
                openai_api_key=api_key
            )
            # 引入联网搜索工具
            self.tools = [internet_search]
            self.llm_with_tools = self.llm.bind_tools(self.tools)
        else:
            print("⚠️ 未检测到 OPENAI_API_KEY，Agent 将运行在仅检索/模拟模式")
            self.llm = None
            self.llm_with_tools = None

    def _encode_image(self, image_path: str) -> str:
        try:
            with open(image_path, "rb") as image_file:
                return base64.b64encode(image_file.read()).decode('utf-8')
        except Exception as e:
            print(f"⚠️ 图片读取失败 {image_path}: {e}")
            return None

    def chat_stream(self, user_query: str, image_data: str = None):
        import json
        
        def _yield_data(type_str, content):
            return json.dumps({"type": type_str, "content": content}, ensure_ascii=False) + "\n"

        yield _yield_data("status", "正在加载历史对话...")
        history_msgs = self.memory.get_context() 
        chat_history_str = ""
        for msg in history_msgs:
            role = "学生" if msg["role"] == "user" else "助教"
            chat_history_str += f"{role}: {msg['content']}\n"

        yield _yield_data("status", "正在执行混合检索(Vector + BM25)...")
        print(f"🤖 Agent 思考中: {user_query}")
        
        context = self.rag.retrieve(user_query, 20, 4)
        print(f"【检索结果预览】：{context[:500]}...") 
        
        yield _yield_data("status", f"混合检索完成，已获取 {context.count('[文档片段')} 条相关上下文片段。")
        
        full_response = ""
        if self.llm_with_tools:
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
2. 如果参考资料不足以回答，或学生问题涉及最新前沿知识、外部工具的使用，请你调用工具进行联网搜索。
3. 如果都没有答案，请坦诚告知学生。

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
                
                # Append user uploaded image if any
                if image_data:
                    url = image_data if image_data.startswith("data:image/") else f"data:image/jpeg;base64,{image_data}"
                    content_parts.append({
                        "type": "image_url",
                        "image_url": {"url": url}
                    })

                messages = [
                    SystemMessage(content=system_text),
                    HumanMessage(content=content_parts)
                ]

                yield _yield_data("status", "模型思考中...")
                response_msg = self.llm_with_tools.invoke(messages)

                parsed_tool_calls = []
                content_text = response_msg.content or ""
                
                if hasattr(response_msg, "tool_calls") and response_msg.tool_calls:
                    parsed_tool_calls = response_msg.tool_calls
                elif '"name":' in content_text and 'internet_search' in content_text:
                    try:
                        match = re.search(r'(\{.*"name".*internet_search.*?\})', content_text, re.DOTALL)
                        if match:
                            tool_data = json.loads(match.group(1))
                            if "parameters" in tool_data:
                                args = tool_data["parameters"]
                            elif "args" in tool_data:
                                args = tool_data["args"]
                            else:
                                args = tool_data
                                
                            parsed_tool_calls.append({
                                "name": "internet_search",
                                "args": args
                            })
                    except Exception as e:
                        pass

                if parsed_tool_calls:
                    search_results_text = ""
                    for tool_call in parsed_tool_calls:
                        tool_name = tool_call["name"]
                        tool_args = tool_call["args"]
                        yield _yield_data("status", f"正在调用外部工具: {tool_name}...")
                        print(f"🛠️ Agent 决定调用工具: {tool_name}, 参数: {tool_args}")
                        
                        if tool_name == "internet_search":
                            tool_result = internet_search.invoke(tool_args)
                            print(f"🔍 工具返回结果: {str(tool_result)[:200]}...")
                            search_results_text += f"\n【{tool_name} 检索结果】:\n{tool_result}\n"
                        else:
                            search_results_text += f"\n【{tool_name}】未找到此工具。\n"
                    
                    yield _yield_data("status", "综合搜索结果，生成回答...")
                    new_knowledge_prompt = f"""由于本地资料不满足要求，我为你执行了外部工具调用。
以下是外部工具调用的返回结果：
{search_results_text}

请基于上述【外部工具返回结果】以及之前的对话内容，回答我的问题。
【我的问题是】: {user_query}
"""
                    content_parts_new = [{"type": "text", "text": new_knowledge_prompt}]
                    for b64_img in images:
                        content_parts_new.append({
                            "type": "image_url",
                            "image_url": {"url": f"data:image/jpeg;base64,{b64_img}"}
                        })
                        
                    # Append user uploaded image if any
                    if image_data:
                        url = image_data if image_data.startswith("data:image/") else f"data:image/jpeg;base64,{image_data}"
                        content_parts_new.append({
                            "type": "image_url",
                            "image_url": {"url": url}
                        })
                        
                    flat_messages = [
                        SystemMessage(content=system_text),
                        HumanMessage(content=content_parts_new) 
                    ]

                    for chunk in self.llm.stream(flat_messages):
                        if chunk.content:
                            full_response += chunk.content
                            yield _yield_data("chunk", chunk.content)
                            
                else:
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
            full_response = f"收到问题: {user_query}\n\n[系统提示] 未配置 OPENAI_API_KEY..."
            yield _yield_data("chunk", full_response)

        yield _yield_data("status", "保存对话记录...")
        self.memory.add_interaction(user_query, full_response)
        yield _yield_data("done", "")
