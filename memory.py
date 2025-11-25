# src/test_agent/memory.py

from typing import List, Dict, Any
from collections import deque
from datetime import datetime


class ConversationMemory:
    """
    【增强组件】短期记忆

    作用: 记住上下文，实现多轮对话

    场景:
    用户: "帮我测试登录功能"
    Agent: "已生成 10 个测试用例"

    用户: "第 3 个用例失败了，帮我分析原因"  👈 需要记住之前的上下文
    Agent: "分析 func_3 失败原因..."

    用户: "帮我修改这个用例"  👈 知道"这个"指的是 func_3
    Agent: "已修改 func_3..."
    """

    def __init__(self, max_turns: int = 10):
        self.max_turns = max_turns
        self.messages: deque = deque(maxlen=max_turns * 2)  # user + assistant

        # 上下文变量 (类似 session 变量)
        self.context_vars: Dict[str, Any] = {}

    def add_user_message(self, content: str):
        """添加用户消息"""
        self.messages.append({
            "role": "user",
            "content": content,
            "timestamp": datetime.now().isoformat()
        })

    def add_assistant_message(self, content: str):
        """添加助手消息"""
        self.messages.append({
            "role": "assistant",
            "content": content,
            "timestamp": datetime.now().isoformat()
        })

    def set_context(self, key: str, value: Any):
        """设置上下文变量"""
        self.context_vars[key] = value
        print(f"💭 [记忆] 保存上下文: {key} = {value}")

    def get_context(self, key: str) -> Any:
        """获取上下文变量"""
        return self.context_vars.get(key)

    def get_conversation_history(self) -> List[Dict]:
        """获取对话历史"""
        return list(self.messages)

    def format_for_llm(self) -> List[Dict]:
        """
        格式化为 LLM 可用的格式

        返回:
        [
            {"role": "user", "content": "..."},
            {"role": "assistant", "content": "..."},
            ...
        ]
        """
        return [
            {"role": msg["role"], "content": msg["content"]}
            for msg in self.messages
        ]

    def get_summary(self) -> str:
        """生成对话摘要（用于长对话压缩）"""

        if not self.messages:
            return "无对话历史"

        # 简单摘要：提取关键信息
        summary_parts = []

        for msg in self.messages:
            if msg["role"] == "user":
                # 提取用户意图关键词
                content = msg["content"][:100]
                summary_parts.append(f"用户: {content}")

        return "\n".join(summary_parts[-5:])  # 最近 5 条

    def clear(self):
        """清空记忆"""
        self.messages.clear()
        self.context_vars.clear()
        print("🧹 [记忆] 已清空")


# ============= 使用示例 =============

if __name__ == "__main__":

    memory = ConversationMemory()

    # 第 1 轮对话
    memory.add_user_message("帮我测试登录功能")
    memory.add_assistant_message("已生成 10 个测试用例")
    memory.set_context("current_task", "login_test")
    memory.set_context("test_count", 10)

    # 第 2 轮对话
    memory.add_user_message("第 3 个用例失败了，帮我分析原因")

    # Agent 可以从上下文获取信息
    current_task = memory.get_context("current_task")
    print(f"当前任务: {current_task}")

    # 获取完整对话历史传给 LLM
    history = memory.format_for_llm()
    print(f"\n对话历史 ({len(history)} 条):")
    for msg in history:
        print(f"  {msg['role']}: {msg['content']}")
