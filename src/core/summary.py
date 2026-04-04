import os
import json
from datetime import datetime
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage

class SummaryManager:
    def __init__(self):
        self.sessions_dir = os.path.join(os.getcwd(), "data", "sessions")
        self.summary_dir = os.path.join(os.getcwd(), "data", "summaries")
        os.makedirs(self.summary_dir, exist_ok=True)
        
        load_dotenv()
        api_key = os.getenv("OPENAI_API_KEY")
        base_url = os.getenv("MODEL_API_BASE")
        model_name = os.getenv("MODEL_NAME")
        if api_key:
            self.llm = ChatOpenAI(
                model=model_name,
                temperature=0.3,
                openai_api_base=base_url,
                openai_api_key=api_key
            )
        else:
            self.llm = None

    def get_summaries(self, student_id: str):
        file_path = os.path.join(self.summary_dir, f"{student_id}.json")
        if not os.path.exists(file_path):
            return []
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []

    def generate_summary(self, student_id: str) -> dict:
        if not self.llm:
            raise Exception("LLM is not configured properly.")

        # 1. 收集所有对话记录
        all_histories = []
        prefix = f"sess_{student_id}_"
        if os.path.exists(self.sessions_dir):
            for file_name in os.listdir(self.sessions_dir):
                if file_name.startswith(prefix) and file_name.endswith(".json"):
                    lab_id = file_name[len(prefix):-5]
                    with open(os.path.join(self.sessions_dir, file_name), "r", encoding="utf-8") as f:
                        data = json.load(f)
                        if "chat_history" in data and len(data["chat_history"]) > 0:
                            all_histories.append({
                                "lab": lab_id,
                                "history": data["chat_history"]
                            })
        
        if not all_histories:
            raise Exception("暂无任何实验对话记录，无法生成总结！")

        # 2. 组装给大模型的提词
        history_text = "【学生各实验问答记录】\n"
        for item in all_histories:
            history_text += f"--- 实验：{item['lab']} ---\n"
            for msg in item['history']:
                role = "学生" if msg["role"] == "user" else "助教"
                content = msg["content"]
                # 截断过长的助教回答以节省token
                if role == "助教" and len(content) > 300:
                    content = content[:300] + "...(已省略)"
                history_text += f"{role}: {content}\n"
            history_text += "\n"

        prompt = f"""
你是一个专业的计算机网络教授，现在你需要根据一个学生在这几个实验中的提问和系统的解答记录，给出一个个性化的「个人问题总结与学习建议」。
请务必涵盖以下几点：
1. 学生主要在哪些知识点或操作上有疑问（如：网络协议、配置命令、排错思路等）。
2. 需要加强哪些方面的学习（指出薄弱环节）。
3. 给出后续如何更好地学习计算机网络的建议。
4. 使用 Markdown 格式进行美观的排版输出（包括列表和加粗等）。

{history_text}
"""

        messages = [
            SystemMessage(content="你是资深的计算机网络专家和教师。"),
            HumanMessage(content=prompt)
        ]

        response = self.llm.invoke(messages)
        summary_content = response.content

        # 3. 保存记录
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        new_record = {
            "date": now_str,
            "content": summary_content
        }
        
        records = self.get_summaries(student_id)
        records.insert(0, new_record) # 最新的放前面

        file_path = os.path.join(self.summary_dir, f"{student_id}.json")
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(records, f, ensure_ascii=False, indent=2)

        return new_record
