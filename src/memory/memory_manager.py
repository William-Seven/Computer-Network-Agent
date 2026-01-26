from typing import List, Dict, Any

class MemoryManager:
    """
    负责管理多轮交互的历史记录和上下文信息。
    对应需求 3.5：记忆机制与多轮交互实现方法。
    """
    
    def __init__(self, session_id: str):
        self.session_id = session_id
        # 这里可以使用 Redis 或数据库持久化，目前先用内存模拟
        self.chat_history: List[Dict[str, str]] = []
        self.experiment_progress: Dict[str, Any] = {} # 记录学生当前的实验状态

    def add_interaction(self, user_input: str, agent_response: str):
        """
        保存一轮对话
        """
        self.chat_history.append({"role": "user", "content": user_input})
        self.chat_history.append({"role": "assistant", "content": agent_response})

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

    def get_summary(self) -> str:
        """
        返回当前对话的摘要或实验状态描述，供 Agent 决策使用
        """
        progress_str = ", ".join([f"{k}: {v}" for k, v in self.experiment_progress.items()])
        return f"当前实验进度: {progress_str if progress_str else '无'}"