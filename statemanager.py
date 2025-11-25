# src/test_agent/state_manager.py

import json
import os
from typing import Any, Dict, Optional
from datetime import datetime
from pathlib import Path


class StateManager:
    """
    【核心组件】状态管理器

    作用: 保存和恢复测试执行状态

    使用场景:
    1. 测试执行中断 → 可以从断点继续
    2. 查看历史执行记录
    3. 对比多次执行结果
    4. 生成报告时读取完整数据
    """

    def __init__(self, storage_dir: str = "./test_states"):
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(exist_ok=True)

        # 当前会话状态
        self.current_session = self._create_session()
        self.session_file = self.storage_dir / f"session_{self.current_session['id']}.json"

    def _create_session(self) -> Dict:
        """创建新会话"""
        return {
            "id": datetime.now().strftime("%Y%m%d_%H%M%S"),
            "start_time": datetime.now().isoformat(),
            "status": "running",
            "plan": None,
            "tasks": {},
            "summary": {}
        }

    def save_plan(self, plan: Dict):
        """保存测试计划"""
        self.current_session["plan"] = plan
        self._persist()
        print(f"💾 [状态] 已保存测试计划")

    def save_task_result(self, task_id: str, result: Dict):
        """保存单个任务结果"""
        self.current_session["tasks"][task_id] = {
            "result": result,
            "timestamp": datetime.now().isoformat()
        }
        self._persist()
        print(f"💾 [状态] 已保存任务结果: {task_id}")

    def save_summary(self, summary: Dict):
        """保存执行摘要"""
        self.current_session["summary"] = summary
        self.current_session["end_time"] = datetime.now().isoformat()
        self.current_session["status"] = "completed"
        self._persist()
        print(f"💾 [状态] 已保存执行摘要")

    def _persist(self):
        """持久化到文件"""
        with open(self.session_file, 'w', encoding='utf-8') as f:
            json.dump(self.current_session, f, indent=2, ensure_ascii=False)

    def load_session(self, session_id: str) -> Optional[Dict]:
        """加载指定会话"""
        session_file = self.storage_dir / f"session_{session_id}.json"

        if not session_file.exists():
            print(f"❌ 会话不存在: {session_id}")
            return None

        with open(session_file, 'r', encoding='utf-8') as f:
            return json.load(f)

    def list_sessions(self) -> list:
        """列出所有会话"""
        sessions = []
        for file in self.storage_dir.glob("session_*.json"):
            with open(file, 'r') as f:
                session = json.load(f)
                sessions.append({
                    "id": session["id"],
                    "start_time": session["start_time"],
                    "status": session["status"],
                    "tasks_count": len(session.get("tasks", {}))
                })

        return sorted(sessions, key=lambda x: x["start_time"], reverse=True)

    def resume_session(self, session_id: str):
        """恢复未完成的会话"""
        session = self.load_session(session_id)

        if not session:
            return None

        if session["status"] == "completed":
            print(f"⚠️  会话已完成，无需恢复: {session_id}")
            return None

        # 找出已完成和未完成的任务
        completed_tasks = list(session.get("tasks", {}).keys())

        print(f"🔄 [状态] 恢复会话: {session_id}")
        print(f"   已完成任务: {len(completed_tasks)}")

        return {
            "session": session,
            "completed_tasks": completed_tasks
        }

    def get_current_state(self) -> Dict:
        """获取当前状态"""
        return self.current_session


# ============= 使用示例 =============

if __name__ == "__main__":

    # 创建状态管理器
    state = StateManager()

    # 保存测试计划
    state.save_plan({
        "requirement": "用户登录功能",
        "total_tasks": 10
    })

    # 模拟执行任务
    state.save_task_result("smoke_1", {
        "status": "success",
        "output": "页面加载成功"
    })

    state.save_task_result("func_1", {
        "status": "success",
        "output": "登录成功"
    })

    # 保存摘要
    state.save_summary({
        "total": 10,
        "success": 8,
        "failed": 2
    })

    # 查看所有会话
    print("\n📚 历史会话:")
    sessions = state.list_sessions()
    for s in sessions:
        print(f"   {s['id']} - {s['status']} - {s['tasks_count']} 任务")
