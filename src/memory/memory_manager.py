import os
import json
from typing import List, Dict, Any

class MemoryManager:
    """
    负责管理多轮交互的历史记录和上下文信息。
    数据将持久化存储在 data/sessions/{session_id}.json 中。
    """
    
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.storage_dir = os.path.join(os.getcwd(), "data", "sessions")
        self.file_path = os.path.join(self.storage_dir, f"{session_id}.json")
        
        # 确保存储目录存在
        os.makedirs(self.storage_dir, exist_ok=True)
        
        # 初始化数据
        self.chat_history: List[Dict[str, str]] = []
        self.experiment_progress: Dict[str, Any] = {} 
        
        # 尝试加载现有记忆
        self._load()

    def _load(self):
        """从文件加载记忆"""
        if os.path.exists(self.file_path):
            try:
                with open(self.file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.chat_history = data.get("chat_history", [])
                    self.experiment_progress = data.get("experiment_progress", {})
            except Exception as e:
                print(f"⚠️ 加载 Session {self.session_id} 失败: {e}")

    def _save(self):
        """保存记忆到文件"""
        data = {
            "chat_history": self.chat_history,
            "experiment_progress": self.experiment_progress
        }
        try:
            with open(self.file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"❌ 保存 Session {self.session_id} 失败: {e}")

    def clear(self):
        """清空内存并删除物理文件"""
        self.chat_history = []
        self.experiment_progress = []
        if os.path.exists(self.file_path):
            try:
                os.remove(self.file_path)
            except Exception as e:
                print(f"❌ 删除记忆文件失败: {e}")

    def add_interaction(self, user_input: str, agent_response: str):
        """
        保存一轮对话
        """
        self.chat_history.append({"role": "user", "content": user_input})
        self.chat_history.append({"role": "assistant", "content": agent_response})
        self._save()

    def get_context(self, window_size: int = 5) -> List[Dict[str, str]]:
        """
        获取最近的对话上下文，用于构建 Prompt
        """
        return self.chat_history[-window_size * 2:]

    def update_progress(self, experiment_id: str, status: str):
        """
        更新实验进度，例如 'lab_01': 'completed'
        """
        self.experiment_progress[experiment_id] = status
        self._save()

    def get_summary(self) -> str:
        """
        返回当前对话的摘要或实验状态描述，供 Agent 决策使用
        """
        progress_str = ", ".join([f"{k}: {v}" for k, v in self.experiment_progress.items()])
        return f"当前实验进度: {progress_str if progress_str else '无'}"