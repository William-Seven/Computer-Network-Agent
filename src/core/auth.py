import json
import os
import hashlib
from typing import Dict, Any

class AuthManager:
    """
    基于文件的简易用户认证系统
    """
    def __init__(self, data_path="data/users.json"):
        self.data_path = data_path
        self.users = self._load_users()

    def _load_users(self) -> Dict[str, Any]:
        """加载用户数据"""
        if not os.path.exists(self.data_path):
            return {}
        try:
            with open(self.data_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"⚠️ 加载用户数据失败: {e}")
            return {}

    def _save_users(self):
        """保存用户数据"""
        try:
            os.makedirs(os.path.dirname(self.data_path), exist_ok=True)
            with open(self.data_path, 'w', encoding='utf-8') as f:
                json.dump(self.users, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"❌ 保存用户数据失败: {e}")

    def _hash_password(self, password: str) -> str:
        """简单的 SHA256 哈希"""
        return hashlib.sha256(password.encode()).hexdigest()

    def register(self, student_id: str, password: str) -> dict:
        """
        注册用户
        :return: {"success": bool, "message": str}
        """
        if len(student_id) != 10:
            return {"success": False, "message": "学号必须为 10 位"}
        
        if student_id in self.users:
            return {"success": False, "message": "该学号已注册"}
            
        self.users[student_id] = {
            "password": self._hash_password(password),
            # 后续可扩展更多字段，如姓名、班级
        }
        self._save_users()
        return {"success": True, "message": "注册成功"}

    def login(self, student_id: str, password: str) -> dict:
        """
        用户登录
        :return: {"success": bool, "message": str}
        """
        user = self.users.get(student_id)
        if not user:
            return {"success": False, "message": "用户不存在"}
        
        if user["password"] != self._hash_password(password):
            return {"success": False, "message": "密码错误"}
            
        return {"success": True, "message": "登录成功"}