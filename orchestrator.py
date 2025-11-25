# ==================== 工作流编排器模块 ====================
"""
WorkflowOrchestrator - 工作流编排器
负责按测试阶段组织任务执行、管理任务依赖关系、处理并发执行和错误恢复
"""

import logging
import time
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from concurrent.futures import ThreadPoolExecutor, as_completed

from planner import TestPlan, TestTask, TestPhase

logger = logging.getLogger(__name__)


# ==================== 枚举定义 ====================
class TaskStatus(Enum):
    """任务状态"""
    PENDING = "pending"  # 等待执行
    RUNNING = "running"  # 正在执行
    SUCCESS = "success"  # 执行成功
    FAILED = "failed"  # 执行失败
    SKIPPED = "skipped"  # 已跳过
    RETRY = "retry"  # 重试中


class RecoveryAction(Enum):
    """恢复操作"""
    RETRY = "retry"  # 重试
    SKIP = "skip"  # 跳过
    ABORT = "abort"  # 中止
    CONTINUE = "continue"  # 继续


# ==================== 数据模型 ====================
@dataclass
class TaskResult:
    """任务结果数据类"""
    task_id: str
    status: TaskStatus
    output: Any
    task_name: str = "N/A"  # 任务名称（有默认值，放在后面）
    error: Optional[str] = None
    duration: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)
    screenshots: List[str] = field(default_factory=list)
    performance_data: Optional[Dict] = None
    retry_count: int = 0


@dataclass
class PhaseResult:
    """阶段结果"""
    phase: TestPhase
    status: TaskStatus
    tasks_results: List[TaskResult] = field(default_factory=list)
    duration: float = 0.0
    success_count: int = 0
    failed_count: int = 0


@dataclass
class WorkflowResult:
    """工作流结果"""
    plan_id: str
    status: TaskStatus
    phase_results: List[PhaseResult] = field(default_factory=list)
    total_duration: float = 0.0
    total_tasks: int = 0
    success_tasks: int = 0
    failed_tasks: int = 0
    start_time: datetime = field(default_factory=datetime.now)
    end_time: Optional[datetime] = None


# ==================== 编排器类 ====================
class WorkflowOrchestrator:
    """工作流编排器"""
    
    def __init__(self, tool_executor=None, max_workers: int = 3):
        """
        初始化编排器
        
        参数:
            tool_executor: 工具执行器（可选）
            max_workers: 最大并发工作线程数
        """
        self.tool_executor = tool_executor
        self.max_workers = max_workers
        self.execution_history = []
        logger.info("WorkflowOrchestrator 已初始化")
    
    def execute_workflow(self, test_plan: TestPlan, is_regression: bool = False) -> WorkflowResult:
        """
        执行完整的工作流
        
        参数:
            test_plan: 测试计划
            is_regression: 是否为回归测试
        
        返回:
            WorkflowResult: 工作流执行结果
        """
        try:
            logger.info(f"开始执行工作流: {test_plan.id} (类型: {'回归测试' if is_regression else '初始测试'})")
            
            workflow_result = WorkflowResult(
                plan_id=test_plan.id,
                status=TaskStatus.RUNNING
            )
            
            if is_regression:
                # 回归测试流程：只执行冒烟测试和回归测试
                phase_order = [
                    TestPhase.SMOKE,
                    TestPhase.REGRESSION
                ]
            else:
                # 初始测试流程：执行所有测试阶段（除了回归测试）
                phase_order = [
                    TestPhase.SMOKE,
                    TestPhase.FUNCTIONAL,
                    TestPhase.PERFORMANCE,
                    TestPhase.SECURITY
                ]
            
            for phase in phase_order:
                if phase not in test_plan.tasks:
                    continue
                
                tasks = test_plan.tasks[phase]
                if not tasks:
                    continue
                
                logger.info(f"执行阶段: {phase.value}, 任务数: {len(tasks)}")
                
                # 执行阶段
                phase_result = self._execute_phase(phase, tasks)
                workflow_result.phase_results.append(phase_result)
                
                # 更新统计
                workflow_result.total_tasks += len(tasks)
                workflow_result.success_tasks += phase_result.success_count
                workflow_result.failed_tasks += phase_result.failed_count
                workflow_result.total_duration += phase_result.duration
                
                # 如果冒烟测试失败，中止后续测试
                if phase == TestPhase.SMOKE and phase_result.status == TaskStatus.FAILED:
                    logger.error("冒烟测试失败，中止后续测试")
                    workflow_result.status = TaskStatus.FAILED
                    break
            
            # 最终状态判定
            if workflow_result.status != TaskStatus.FAILED:
                if workflow_result.failed_tasks == 0:
                    workflow_result.status = TaskStatus.SUCCESS
                else:
                    workflow_result.status = TaskStatus.FAILED
            
            workflow_result.end_time = datetime.now()
            logger.info(f"工作流执行完成: {workflow_result.status.value}")
            
            return workflow_result
            
        except Exception as e:
            logger.error(f"执行工作流失败: {str(e)}")
            raise
    
    def _execute_phase(self, phase: TestPhase, tasks: List[TestTask]) -> PhaseResult:
        """
        执行特定测试阶段
        
        参数:
            phase: 测试阶段
            tasks: 任务列表
        
        返回:
            PhaseResult: 阶段执行结果
        """
        start_time = time.time()
        phase_result = PhaseResult(phase=phase, status=TaskStatus.RUNNING)
        
        try:
            # 串行执行任务（可根据需要改为并行）
            for task in tasks:
                task_result = self._execute_task(task)
                phase_result.tasks_results.append(task_result)
                
                if task_result.status == TaskStatus.SUCCESS:
                    phase_result.success_count += 1
                elif task_result.status == TaskStatus.FAILED:
                    phase_result.failed_count += 1
            
            # 判断阶段状态
            if phase_result.failed_count == 0:
                phase_result.status = TaskStatus.SUCCESS
            else:
                phase_result.status = TaskStatus.FAILED
            
        except Exception as e:
            logger.error(f"执行阶段 {phase.value} 失败: {str(e)}")
            phase_result.status = TaskStatus.FAILED
        
        phase_result.duration = time.time() - start_time
        return phase_result
    
    def _execute_task(self, task: TestTask, retry_count: int = 0) -> TaskResult:
        """
        执行单个测试任务
        
        参数:
            task: 测试任务
            retry_count: 重试次数
        
        返回:
            TaskResult: 任务执行结果
        """
        logger.info(f"执行任务: {task.id} - {task.name}")
        start_time = time.time()
        
        try:
            # 检查是否有工具执行器
            if hasattr(self, 'tool_executor') and self.tool_executor:
                # 使用工具执行器执行任务
                output = self.tool_executor(task.tool_name, task.parameters)
                status = TaskStatus.SUCCESS
            else:
                # 执行Appium测试任务（模拟模式）
                output = self._execute_real_appium_task(task)
                # 模拟执行时标记为SKIPPED（跳过）状态
                status = TaskStatus.SKIPPED
            
            duration = time.time() - start_time
            
            # 创建结果
            return TaskResult(
                task_id=task.id,
                task_name=task.name,  # 添加任务名称
                status=status,
                output=output,
                error=None,
                duration=duration,
                retry_count=retry_count
            )
            
        except Exception as e:
            duration = time.time() - start_time
            logger.error(f"任务执行失败: {task.id} - {task.name}, 错误: {str(e)}")
            
            # 创建失败结果
            return TaskResult(
                task_id=task.id,
                task_name=task.name,  # 添加任务名称
                status=TaskStatus.FAILED,
                output=None,
                error=str(e),
                duration=duration,
                retry_count=retry_count
            )
    
    def _execute_real_appium_task(self, task: TestTask) -> str:
        """
        执行Appium测试任务（模拟或真实执行）
        
        参数:
            task: 测试任务
        
        返回:
            str: 执行结果
        """
        import time
        
        # 检查是否有真实的Appium工具执行器
        if hasattr(self, 'tool_executor') and self.tool_executor:
            # 尝试真实执行
            try:
                return self.tool_executor(task.tool_name, task.parameters)
            except Exception as e:
                return f"真实执行失败: {str(e)}"
        
        # 模拟执行模式（用于演示和测试）
        logger.warning(f"⚠️  模拟执行模式: {task.id} - {task.name}")
        
        # 根据任务类型模拟不同的执行时间和结果
        if task.tool_name == "connect_devices":
            # 设备连接测试
            time.sleep(2.5)
            return "⚠️ 模拟执行: 设备连接测试（需要真实设备）"
            
        elif task.tool_name == "launch_app":
            # 应用启动测试
            package_name = task.parameters.get("package_name", "com.bluex.picflow")
            time.sleep(3.2)
            return f"⚠️ 模拟执行: 应用启动测试（需要真实设备）"
            
        elif task.tool_name == "navigate_ui":
            # UI导航测试
            screens = task.parameters.get("target_screens", [])
            time.sleep(1.5 * len(screens))
            return f"⚠️ 模拟执行: UI导航测试（需要真实设备）"
            
        elif task.tool_name == "test_interactions":
            # 交互测试
            interactions = task.parameters.get("interactions", [])
            time.sleep(2.0)
            return f"⚠️ 模拟执行: 交互测试（需要真实设备）"
            
        elif task.tool_name == "analyze_ad":
            # 广告分析测试
            ad_types = task.parameters.get("ad_types", [])
            time.sleep(4.0)
            return f"⚠️ 模拟执行: 广告分析测试（需要真实设备）"
            
        elif task.tool_name == "performance_test":
            # 性能测试
            metrics = task.parameters.get("metrics", [])
            time.sleep(5.0)
            return f"⚠️ 模拟执行: 性能测试（需要真实设备）"
            
        elif task.tool_name == "check_permissions":
            # 权限检查
            permissions = task.parameters.get("permissions", [])
            time.sleep(1.0)
            return f"⚠️ 模拟执行: 权限检查（需要真实设备）"
            
        else:
            # 默认模拟执行
            time.sleep(1.0)
            return f"⚠️ 模拟执行: {task.name}（需要真实设备）"
    
    def _handle_task_failure(self, task: TestTask, error: Exception) -> RecoveryAction:
        """
        处理任务失败
        
        参数:
            task: 失败的任务
            error: 错误信息
        
        返回:
            RecoveryAction: 恢复操作
        """
        logger.error(f"任务 {task.id} 失败: {str(error)}")
        
        # 根据任务优先级决定恢复策略
        if task.priority.value <= 2:  # CRITICAL 或 HIGH
            return RecoveryAction.RETRY
        else:
            return RecoveryAction.SKIP


if __name__ == "__main__":
    # 测试代码
    from planner import TestPlanner
    
    logging.basicConfig(level=logging.INFO)
    
    # 创建规划器和编排器
    planner = TestPlanner()
    orchestrator = WorkflowOrchestrator()
    
    # 创建测试计划
    plan = planner.create_test_plan("测试应用启动功能")
    
    # 执行工作流
    result = orchestrator.execute_workflow(plan)
    
    print(f"\n工作流执行结果:")
    print(f"状态: {result.status.value}")
    print(f"总任务数: {result.total_tasks}")
    print(f"成功: {result.success_tasks}")
    print(f"失败: {result.failed_tasks}")
    print(f"总耗时: {result.total_duration:.2f}秒")
