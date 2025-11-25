# ==================== 报告生成器模块 ====================
"""
ReportGenerator - 报告生成器
负责生成多种格式的测试报告，提供测试数据可视化
"""

import logging
import json
from typing import List, Dict, Any
from datetime import datetime
from pathlib import Path

from orchestrator import WorkflowResult, PhaseResult, TaskResult, TaskStatus
from validator import ValidationResult
from planner import TestPlan

logger = logging.getLogger(__name__)


# ==================== 报告生成器类 ====================
class ReportGenerator:
    """报告生成器"""
    
    def __init__(self, output_dir: str = "test_reports"):
        """
        初始化报告生成器
        
        参数:
            output_dir: 报告输出目录
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True, parents=True)
        logger.info(f"ReportGenerator 已初始化，输出目录: {output_dir}")
    
    def generate_html_report(self, workflow_result: WorkflowResult, test_plan: TestPlan = None) -> str:
        """
        生成HTML报告
        
        参数:
            workflow_result: 工作流执行结果
            test_plan: 测试计划（可选）
        
        返回:
            报告文件路径
        """
        try:
            logger.info("生成HTML报告")
            
            # 生成报告内容
            html_content = self._generate_html_content(workflow_result, test_plan)
            
            # 保存到文件
            report_file = self.output_dir / f"report_{workflow_result.plan_id}.html"
            with open(report_file, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            logger.info(f"HTML报告已生成: {report_file}")
            return str(report_file)
            
        except Exception as e:
            logger.error(f"生成HTML报告失败: {str(e)}")
            raise
    
    def generate_markdown_report(self, workflow_result: WorkflowResult, test_plan: TestPlan = None) -> str:
        """
        生成Markdown报告
        
        参数:
            workflow_result: 工作流执行结果
            test_plan: 测试计划（可选）
        
        返回:
            报告文件路径
        """
        try:
            logger.info("生成Markdown报告")
            
            # 生成报告内容
            md_content = self._generate_markdown_content(workflow_result, test_plan)
            
            # 保存到文件
            report_file = self.output_dir / f"report_{workflow_result.plan_id}.md"
            with open(report_file, 'w', encoding='utf-8') as f:
                f.write(md_content)
            
            logger.info(f"Markdown报告已生成: {report_file}")
            return str(report_file)
            
        except Exception as e:
            logger.error(f"生成Markdown报告失败: {str(e)}")
            raise
    
    def generate_json_report(self, workflow_result: WorkflowResult) -> str:
        """
        生成JSON报告
        
        参数:
            workflow_result: 工作流执行结果
        
        返回:
            报告文件路径
        """
        try:
            logger.info("生成JSON报告")
            
            # 转换为字典
            report_data = {
                "plan_id": workflow_result.plan_id,
                "status": workflow_result.status.value,
                "start_time": workflow_result.start_time.isoformat(),
                "end_time": workflow_result.end_time.isoformat() if workflow_result.end_time else None,
                "total_duration": workflow_result.total_duration,
                "total_tasks": workflow_result.total_tasks,
                "success_tasks": workflow_result.success_tasks,
                "failed_tasks": workflow_result.failed_tasks,
                "phases": [
                    {
                        "phase": pr.phase.value,
                        "status": pr.status.value,
                        "duration": pr.duration,
                        "success_count": pr.success_count,
                        "failed_count": pr.failed_count,
                        "tasks": [
                    {
                        "task_id": tr.task_id,
                        "task_name": tr.task_name,  # 添加任务名称
                        "status": tr.status.value,
                        "duration": tr.duration,
                        "error": tr.error,
                        "retry_count": tr.retry_count
                    }
                    for tr in pr.tasks_results
                ]
                    }
                    for pr in workflow_result.phase_results
                ]
            }
            
            # 保存到文件
            report_file = self.output_dir / f"report_{workflow_result.plan_id}.json"
            with open(report_file, 'w', encoding='utf-8') as f:
                json.dump(report_data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"JSON报告已生成: {report_file}")
            return str(report_file)
            
        except Exception as e:
            logger.error(f"生成JSON报告失败: {str(e)}")
            raise
    
    def _generate_html_content(self, workflow_result: WorkflowResult, test_plan: TestPlan = None) -> str:
        """生成HTML内容"""
        pass_rate = (workflow_result.success_tasks / workflow_result.total_tasks * 100) if workflow_result.total_tasks > 0 else 0
        
        html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>测试报告 - {workflow_result.plan_id}</title>
    <style>
            body {{ font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }}
            .container {{ max-width: 1200px; margin: 0 auto; background: white; padding: 30px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
            h1 {{ color: #333; border-bottom: 3px solid #4CAF50; padding-bottom: 10px; }}
            h2 {{ color: #555; margin-top: 30px; }}
            .summary {{ background: #e8f5e9; padding: 20px; border-radius: 5px; margin: 20px 0; }}
            .stats {{ display: flex; justify-content: space-around; margin: 20px 0; }}
            .stat-box {{ text-align: center; padding: 15px; background: white; border-radius: 5px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); min-width: 150px; }}
            .stat-value {{ font-size: 32px; font-weight: bold; color: #4CAF50; }}
            .stat-label {{ color: #777; margin-top: 5px; }}
            .phase {{ margin: 20px 0; padding: 15px; background: #f9f9f9; border-left: 4px solid #2196F3; }}
            .task {{ margin: 10px 0; padding: 10px; background: white; border-radius: 3px; }}
            .success {{ color: #4CAF50; font-weight: bold; }}
            .failed {{ color: #f44336; font-weight: bold; }}
            .skipped {{ color: #FF9800; font-weight: bold; }}
            .pending {{ color: #2196F3; font-weight: bold; }}
            .duration {{ color: #666; font-size: 0.9em; }}
            table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
            th, td {{ padding: 12px; text-align: left; border-bottom: 1px solid #ddd; }}
            th {{ background-color: #4CAF50; color: white; }}
            tr:hover {{ background-color: #f5f5f5; }}
            .task-details {{ background: #f8f9fa; padding: 15px; border-radius: 5px; margin: 10px 0; }}
            .task-output {{ font-family: monospace; white-space: pre-wrap; background: #f1f3f4; padding: 10px; border-radius: 3px; margin: 5px 0; }}
        </style>
</head>
<body>
    <div class="container">
        <h1>📊 测试执行报告</h1>
        
        <div class="summary">
            <h2>测试概要</h2>
            <p><strong>计划ID:</strong> {workflow_result.plan_id}</p>
            <p><strong>开始时间:</strong> {workflow_result.start_time.strftime('%Y-%m-%d %H:%M:%S')}</p>
            <p><strong>结束时间:</strong> {workflow_result.end_time.strftime('%Y-%m-%d %H:%M:%S') if workflow_result.end_time else 'N/A'}</p>
            <p><strong>总耗时:</strong> {workflow_result.total_duration:.2f} 秒</p>
            <p><strong>最终状态:</strong> <span class="{'success' if workflow_result.status == TaskStatus.SUCCESS else 'failed'}">{workflow_result.status.value.upper()}</span></p>
        </div>
        
        <div class="stats">
            <div class="stat-box">
                <div class="stat-value">{workflow_result.total_tasks}</div>
                <div class="stat-label">总任务数</div>
            </div>
            <div class="stat-box">
                <div class="stat-value" style="color: #4CAF50;">{workflow_result.success_tasks}</div>
                <div class="stat-label">成功</div>
            </div>
            <div class="stat-box">
                <div class="stat-value" style="color: #f44336;">{workflow_result.failed_tasks}</div>
                <div class="stat-label">失败</div>
            </div>
            <div class="stat-box">
                <div class="stat-value" style="color: #2196F3;">{pass_rate:.1f}%</div>
                <div class="stat-label">通过率</div>
            </div>
        </div>
        
        <h2>阶段详情</h2>
"""
        
        # 添加各阶段详情
        for phase_result in workflow_result.phase_results:
            html += f"""
        <div class="phase">
            <h3>{phase_result.phase.value.upper()} 阶段</h3>
            <p>状态: <span class="{'success' if phase_result.status == TaskStatus.SUCCESS else 'failed'}">{phase_result.status.value}</span></p>
            <p>耗时: {phase_result.duration:.2f} 秒</p>
            <p>成功: {phase_result.success_count} / 失败: {phase_result.failed_count}</p>
            
            <table>
                <tr>
                    <th>任务ID</th>
                    <th>任务名称</th>
                    <th>状态</th>
                    <th>耗时</th>
                    <th>重试次数</th>
                    <th>错误信息</th>
                </tr>
"""
            for task_result in phase_result.tasks_results:
                # 根据状态设置不同的CSS类和emoji
                if task_result.status == TaskStatus.SUCCESS:
                    status_class = 'success'
                elif task_result.status == TaskStatus.FAILED:
                    status_class = 'failed'
                elif task_result.status == TaskStatus.SKIPPED:
                    status_class = 'skipped'
                else:
                    status_class = 'pending'
                
                # 获取任务名称（如果存在）
                task_name = getattr(task_result, 'task_name', 'N/A')
                html += f"""
                <tr>
                    <td>{task_result.task_id}</td>
                    <td>{task_name}</td>
                    <td class="{status_class}">{task_result.status.value}</td>
                    <td>{task_result.duration:.2f}s</td>
                    <td>{task_result.retry_count}</td>
                    <td>{task_result.error or '-'}</td>
                </tr>
"""
            html += """
            </table>
            
            <h4>详细执行结果</h4>
"""
            # 添加每个任务的详细执行结果
            for task_result in phase_result.tasks_results:
                status_emoji = '✅' if task_result.status == TaskStatus.SUCCESS else '❌'
                task_name = getattr(task_result, 'task_name', 'N/A')
                
                html += f"""
            <div class="task-details">
                <h5>{status_emoji} {task_result.task_id} - {task_name}</h5>
                <p><strong>状态:</strong> <span class="{'success' if task_result.status == TaskStatus.SUCCESS else 'failed'}">{task_result.status.value}</span></p>
                <p><strong>耗时:</strong> {task_result.duration:.2f} 秒</p>
                <p><strong>重试次数:</strong> {task_result.retry_count}</p>
                <p><strong>执行时间:</strong> {task_result.timestamp.strftime('%Y-%m-%d %H:%M:%S')}</p>
                
                <div class="task-output">
                    <strong>执行输出:</strong>
                    {task_result.output if task_result.output else '无详细输出'}
                </div>
                
                {f'<p><strong>错误信息:</strong> {task_result.error}</p>' if task_result.error else ''}
                
                {f'<p><strong>性能数据:</strong> {task_result.performance_data}</p>' if task_result.performance_data else ''}
            </div>
"""
            
            html += """
        </div>
"""
        
        html += """
    </div>
</body>
</html>
"""
        return html
    
    def _generate_markdown_content(self, workflow_result: WorkflowResult, test_plan: TestPlan = None) -> str:
        """生成Markdown内容"""
        pass_rate = (workflow_result.success_tasks / workflow_result.total_tasks * 100) if workflow_result.total_tasks > 0 else 0
        
        md = f"""# 📊 测试执行报告

## 测试概要

- **计划ID**: {workflow_result.plan_id}
- **开始时间**: {workflow_result.start_time.strftime('%Y-%m-%d %H:%M:%S')}
- **结束时间**: {workflow_result.end_time.strftime('%Y-%m-%d %H:%M:%S') if workflow_result.end_time else 'N/A'}
- **总耗时**: {workflow_result.total_duration:.2f} 秒
- **最终状态**: {'✅ ' + workflow_result.status.value.upper() if workflow_result.status == TaskStatus.SUCCESS else '❌ ' + workflow_result.status.value.upper()}

## 执行统计

| 指标 | 数值 |
|------|------|
| 总任务数 | {workflow_result.total_tasks} |
| 成功任务 | ✅ {workflow_result.success_tasks} |
| 失败任务 | ❌ {workflow_result.failed_tasks} |
| 通过率 | {pass_rate:.1f}% |

## 阶段详情

"""
        
        # 添加各阶段详情
        for phase_result in workflow_result.phase_results:
            status_emoji = '✅' if phase_result.status == TaskStatus.SUCCESS else '❌'
            md += f"""
### {status_emoji} {phase_result.phase.value.upper()} 阶段

- **状态**: {phase_result.status.value}
- **耗时**: {phase_result.duration:.2f} 秒
- **成功**: {phase_result.success_count} / **失败**: {phase_result.failed_count}

#### 任务列表

| 任务ID | 任务名称 | 状态 | 耗时 | 重试次数 | 错误信息 |
|--------|----------|------|------|----------|----------|
"""
            for task_result in phase_result.tasks_results:
                # 根据状态设置不同的emoji
                if task_result.status == TaskStatus.SUCCESS:
                    status_symbol = '✅'
                elif task_result.status == TaskStatus.FAILED:
                    status_symbol = '❌'
                elif task_result.status == TaskStatus.SKIPPED:
                    status_symbol = '⏭️'
                else:
                    status_symbol = '⏳'
                
                task_name = getattr(task_result, 'task_name', 'N/A')
                md += f"| {task_result.task_id} | {task_name} | {status_symbol} {task_result.status.value} | {task_result.duration:.2f}s | {task_result.retry_count} | {task_result.error or '-'} |\n"
        
        # 添加详细执行结果
        md += """

## 📋 详细执行结果

"""
        
        for phase_result in workflow_result.phase_results:
            md += f"""
### {phase_result.phase.value.upper()} 阶段 - 详细结果

"""
            for task_result in phase_result.tasks_results:
                # 根据状态设置不同的emoji
                if task_result.status == TaskStatus.SUCCESS:
                    status_emoji = '✅'
                elif task_result.status == TaskStatus.FAILED:
                    status_emoji = '❌'
                elif task_result.status == TaskStatus.SKIPPED:
                    status_emoji = '⏭️'
                else:
                    status_emoji = '⏳'
                
                task_name = getattr(task_result, 'task_name', 'N/A')
                
                md += f"""
#### {status_emoji} {task_result.task_id} - {task_name}

- **状态**: {task_result.status.value}
- **耗时**: {task_result.duration:.2f} 秒
- **重试次数**: {task_result.retry_count}
- **执行时间**: {task_result.timestamp.strftime('%Y-%m-%d %H:%M:%S')}

**执行输出**:
```
{task_result.output if task_result.output else '无详细输出'}
```

"""
                
                if task_result.error:
                    md += f"""
**错误信息**:
```
{task_result.error}
```

"""
                
                if task_result.performance_data:
                    md += f"""
**性能数据**:
```json
{task_result.performance_data}
```

"""
                
                md += "---\n\n"
        
        md += f"""
---

**报告生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
        
        return md
    
    def generate_summary(self, workflow_result: WorkflowResult) -> str:
        """
        生成简单的文本摘要
        
        参数:
            workflow_result: 工作流结果
        
        返回:
            摘要文本
        """
        pass_rate = (workflow_result.success_tasks / workflow_result.total_tasks * 100) if workflow_result.total_tasks > 0 else 0
        
        summary = f"""
📊 测试执行摘要
{'='*50}
计划ID: {workflow_result.plan_id}
状态: {workflow_result.status.value.upper()}
总任务: {workflow_result.total_tasks}
成功: {workflow_result.success_tasks}
失败: {workflow_result.failed_tasks}
通过率: {pass_rate:.1f}%
总耗时: {workflow_result.total_duration:.2f}秒
{'='*50}
"""
        return summary


if __name__ == "__main__":
    # 测试代码
    from planner import TestPlanner
    from orchestrator import WorkflowOrchestrator
    
    logging.basicConfig(level=logging.INFO)
    
    # 创建测试数据
    planner = TestPlanner()
    orchestrator = WorkflowOrchestrator()
    plan = planner.create_test_plan("测试应用启动功能")
    result = orchestrator.execute_workflow(plan)
    
    # 生成报告
    reporter = ReportGenerator()
    
    # 生成各种格式报告
    html_file = reporter.generate_html_report(result, plan)
    md_file = reporter.generate_markdown_report(result, plan)
    json_file = reporter.generate_json_report(result)
    
    print(reporter.generate_summary(result))
    print(f"\n报告文件:")
    print(f"- HTML: {html_file}")
    print(f"- Markdown: {md_file}")
    print(f"- JSON: {json_file}")
