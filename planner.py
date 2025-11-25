# ==================== 任务规划器模块 ====================
"""
TestPlanner - 测试任务规划器
负责分析测试需求，生成测试计划，并将复杂需求分解为可执行的测试任务
"""

import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)


# ==================== 枚举定义 ====================
class TestPhase(Enum):
    """测试阶段枚举"""
    SMOKE = "smoke"  # 冒烟测试
    FUNCTIONAL = "functional"  # 功能测试
    REGRESSION = "regression"  # 回归测试
    PERFORMANCE = "performance"  # 性能测试
    SECURITY = "security"  # 安全测试


class TaskPriority(Enum):
    """任务优先级"""
    CRITICAL = 1  # 关键
    HIGH = 2  # 高
    MEDIUM = 3  # 中
    LOW = 4  # 低
    TRIVIAL = 5  # 微不足道


# ==================== 数据模型 ====================
@dataclass
class TestTask:
    """测试任务数据类"""
    id: str
    name: str
    description: str
    phase: TestPhase
    tool_name: str
    parameters: Dict[str, Any]
    dependencies: List[str] = field(default_factory=list)
    timeout: int = 300  # 默认5分钟
    retry_count: int = 3
    priority: TaskPriority = TaskPriority.MEDIUM
    expected_result: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "phase": self.phase.value,
            "tool_name": self.tool_name,
            "parameters": self.parameters,
            "dependencies": self.dependencies,
            "timeout": self.timeout,
            "retry_count": self.retry_count,
            "priority": self.priority.value,
            "expected_result": self.expected_result
        }


@dataclass
class TestPlan:
    """测试计划数据类"""
    id: str
    name: str
    description: str
    requirements: str
    tasks: Dict[TestPhase, List[TestTask]] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    estimated_duration: int = 0  # 预估时长（秒）
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "requirements": self.requirements,
            "tasks": {
                phase.value: [task.to_dict() for task in tasks]
                for phase, tasks in self.tasks.items()
            },
            "created_at": self.created_at.isoformat(),
            "estimated_duration": self.estimated_duration
        }


# ==================== 规划器类 ====================
class TestPlanner:
    """测试任务规划器"""
    
    def __init__(self, llm_model=None):
        """初始化规划器"""
        self.llm_model = llm_model
        logger.info("TestPlanner 已初始化")
    
    def create_test_plan(self, requirements: str, plan_name: str = None, previous_bugs: List[Dict] = None) -> TestPlan:
        """基于需求创建测试计划
        
        参数:
            requirements: 测试需求
            plan_name: 计划名称
            previous_bugs: 之前测试发现的bug列表，用于生成回归测试
        """
        try:
            logger.info(f"开始创建测试计划: {requirements[:50]}...")
            
            plan_id = f"plan_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            if self.llm_model:
                llm_response = self._call_llm_planner(requirements, previous_bugs)
                tasks = self._parse_tasks_from_llm_response(llm_response)
            else:
                tasks = self._generate_simple_plan(requirements, previous_bugs)
            
            grouped_tasks = self._group_tasks_by_phase(tasks)
            estimated_duration = sum(task.timeout for task_list in grouped_tasks.values() for task in task_list)
            
            # 根据是否有previous_bugs确定计划类型
            if previous_bugs:
                plan_type = "回归测试计划"
                plan_desc = f"基于发现的{len(previous_bugs)}个bug生成的回归测试计划"
            else:
                plan_type = "初始测试计划"
                plan_desc = f"基于需求自动生成的{plan_type}"
            
            test_plan = TestPlan(
                id=plan_id,
                name=plan_name or f"{plan_type}_{plan_id}",
                description=plan_desc,
                requirements=requirements,
                tasks=grouped_tasks,
                estimated_duration=estimated_duration
            )
            
            logger.info(f"测试计划创建成功: {test_plan.id}, 包含 {len(tasks)} 个任务")
            return test_plan
            
        except Exception as e:
            logger.error(f"创建测试计划失败: {str(e)}")
            raise
    
    def _call_llm_planner(self, prompt: str, previous_bugs: List[Dict] = None) -> str:
        """调用LLM进行规划分析
        
        参数:
            prompt: 测试需求
            previous_bugs: 之前测试发现的bug列表，用于生成回归测试
        """
        try:
            from langchain_core.messages import HumanMessage
            
            if previous_bugs:
                # 回归测试规划
                bugs_summary = "\n".join([f"- {bug.get('description', '未知bug')} (影响: {bug.get('impact', '未知')})" for bug in previous_bugs])
                
                planning_prompt = f"""你是一个专业的测试工程师。请基于之前测试发现的bug制定回归测试计划。

之前测试发现的bug:
{bugs_summary}

回归测试需求:
{prompt}

请专注于验证这些bug是否已修复，并确保修复不会引入新的问题。
主要关注以下测试阶段:
1. 🔄 回归测试 (regression) - 验证bug修复情况
2. 🔥 冒烟测试 (smoke) - 确保基本功能正常

对于每个测试任务，请使用以下格式:
TASK: <任务ID>
NAME: <任务名称>
PHASE: <测试阶段>
DESCRIPTION: <详细描述>
TOOL: <工具名称>
PARAMETERS: <JSON格式参数>
PRIORITY: <1-5>
EXPECTED: <预期结果>
---
"""
            else:
                # 初始测试规划
                planning_prompt = f"""你是一个专业的测试工程师。请为以下需求制定详细的测试计划。

需求:
{prompt}

请按照以下测试阶段规划:
1. 🔥 冒烟测试 (smoke) - 基本功能检查
2. ⚙️ 功能测试 (functional) - 详细功能验证
3. 📊 性能测试 (performance) - 性能指标验证

注意：第一次测试不需要进行回归测试，只有在发现bug后才需要回归测试。

对于每个测试任务，请使用以下格式:
TASK: <任务ID>
NAME: <任务名称>
PHASE: <测试阶段>
DESCRIPTION: <详细描述>
TOOL: <工具名称>
PARAMETERS: <JSON格式参数>
PRIORITY: <1-5>
EXPECTED: <预期结果>
---
"""
            
            response = self.llm_model.invoke([HumanMessage(content=planning_prompt)])
            return response.content
            
        except Exception as e:
            logger.error(f"调用LLM规划器失败: {str(e)}")
            raise
    
    def _parse_tasks_from_llm_response(self, response: str) -> List[TestTask]:
        """解析LLM响应生成测试任务"""
        tasks = []
        task_blocks = response.split('---')
        
        for i, block in enumerate(task_blocks):
            if not block.strip():
                continue
                
            try:
                task_data = {}
                for line in block.split('\n'):
                    if ':' in line:
                        key, value = line.split(':', 1)
                        task_data[key.strip()] = value.strip()
                
                if 'TASK' in task_data:
                    task = TestTask(
                        id=task_data.get('TASK', f'task_{i}'),
                        name=task_data.get('NAME', f'测试任务{i}'),
                        description=task_data.get('DESCRIPTION', ''),
                        phase=TestPhase(task_data.get('PHASE', 'functional').lower()),
                        tool_name=task_data.get('TOOL', 'unknown'),
                        parameters=self._parse_parameters(task_data.get('PARAMETERS', '{}')),
                        priority=TaskPriority(int(task_data.get('PRIORITY', '3'))),
                        expected_result=task_data.get('EXPECTED')
                    )
                    tasks.append(task)
                    
            except Exception as e:
                logger.warning(f"解析任务块失败: {str(e)}")
                continue
        
        return tasks
    
    def _parse_parameters(self, param_str: str) -> Dict[str, Any]:
        """解析参数字符串"""
        try:
            import json
            return json.loads(param_str)
        except:
            return {}
    
    def _generate_simple_plan(self, requirements: str, previous_bugs: str = None) -> List[TestTask]:
        """生成智能化的测试计划（减少对知识库的依赖）
        
        参数:
            requirements: 测试需求
            previous_bugs: 之前测试发现的bug描述字符串，用于生成回归测试
        """
        tasks = []
        
        if previous_bugs:
            # 回归测试计划：专注于验证bug修复
            # 解析bug字符串，按行分割
            bug_lines = [line.strip() for line in previous_bugs.split('\n') if line.strip()]
            logger.info(f"生成回归测试计划，基于{len(bug_lines)}个发现的bug")
            
            # 冒烟测试确保基本功能正常
            tasks.append(TestTask(
                id="smoke_1",
                name="基本功能冒烟测试",
                description="验证修复后应用的基本功能是否正常",
                phase=TestPhase.SMOKE,
                tool_name="connect_devices",
                parameters={"device_type": "Android", "timeout": 30},
                priority=TaskPriority.CRITICAL
            ))
            
            # 为每个发现的bug创建回归测试任务
            for i, bug_desc in enumerate(bug_lines):
                # 清理bug描述，移除序号等
                clean_bug_desc = bug_desc
                if bug_desc.startswith(('1.', '2.', '3.', '4.', '5.', '6.', '7.', '8.', '9.', '0.')):
                    clean_bug_desc = bug_desc.split('.', 1)[1].strip() if '.' in bug_desc else bug_desc
                
                tasks.append(TestTask(
                    id=f"regression_{i+1}",
                    name=f"Bug修复验证: {clean_bug_desc[:30]}",
                    description=f"验证bug已修复: {clean_bug_desc}",
                    phase=TestPhase.REGRESSION,
                    tool_name="validate_bug_fix",
                    parameters={"bug_description": clean_bug_desc, "bug_impact": "未知"},
                    priority=TaskPriority.HIGH
                ))
            
            # 添加综合回归测试
            tasks.append(TestTask(
                id="regression_final",
                name="综合回归测试",
                description="验证修复没有引入新的问题",
                phase=TestPhase.REGRESSION,
                tool_name="comprehensive_test",
                parameters={},
                priority=TaskPriority.MEDIUM
            ))
            
        else:
            # 智能化的初始测试计划：基于深度需求分析生成多样化测试用例
            logger.info(f"生成智能测试计划，需求: {requirements}")
            
            # 基础冒烟测试 - 总是包含
            tasks.append(TestTask(
                id="smoke_1",
                name="设备连接和Appium会话建立",
                description="验证Android设备连接和Appium会话建立",
                phase=TestPhase.SMOKE,
                tool_name="connect_devices",
                parameters={"device_type": "Android", "timeout": 30, "adb_connect": True},
                priority=TaskPriority.CRITICAL
            ))
            
            # 智能需求分析，生成多样化的测试用例
            tasks.extend(self._analyze_requirements_and_generate_tests(requirements))
            
            # 添加边界条件和异常情况测试
            tasks.extend(self._generate_edge_case_tests())
            
            # 添加用户场景测试
            tasks.extend(self._generate_user_scenario_tests())
            
            # 添加压力测试和性能基准测试
            tasks.extend(self._generate_stress_and_performance_tests())
        
        return tasks
    
    def _generate_launch_tests(self) -> List[TestTask]:
        """生成应用启动相关测试用例"""
        return [
            TestTask(
                id="launch_1",
                name="冷启动测试",
                description="测试应用冷启动时间和启动流程",
                phase=TestPhase.FUNCTIONAL,
                tool_name="launch_app",
                parameters={"package_name": "com.bluex.picflow", "activity": "MainActivity", "launch_type": "cold"},
                priority=TaskPriority.CRITICAL
            ),
            TestTask(
                id="launch_2",
                name="热启动测试",
                description="测试应用热启动时间和状态恢复",
                phase=TestPhase.FUNCTIONAL,
                tool_name="launch_app",
                parameters={"package_name": "com.bluex.picflow", "activity": "MainActivity", "launch_type": "warm"},
                priority=TaskPriority.HIGH
            ),
            TestTask(
                id="launch_3",
                name="启动异常处理测试",
                description="测试应用启动过程中的异常情况处理",
                phase=TestPhase.FUNCTIONAL,
                tool_name="launch_app",
                parameters={"package_name": "com.bluex.picflow", "activity": "MainActivity", "test_scenarios": ["网络异常", "权限拒绝", "存储不足"]},
                priority=TaskPriority.MEDIUM
            )
        ]
    
    def _generate_ad_tests(self) -> List[TestTask]:
        """生成广告功能测试用例"""
        return [
            TestTask(
                id="ad_1",
                name="插屏广告展示测试",
                description="测试插屏广告的展示时机和关闭功能",
                phase=TestPhase.FUNCTIONAL,
                tool_name="analyze_ad",
                parameters={"ad_type": "interstitial", "trigger_actions": ["应用启动", "页面切换", "功能完成"], "timeout": 15},
                priority=TaskPriority.HIGH
            ),
            TestTask(
                id="ad_2",
                name="横幅广告展示测试",
                description="测试横幅广告的展示位置和刷新机制",
                phase=TestPhase.FUNCTIONAL,
                tool_name="analyze_ad",
                parameters={"ad_type": "banner", "display_locations": ["首页底部", "详情页顶部"], "refresh_interval": 30},
                priority=TaskPriority.HIGH
            ),
            TestTask(
                id="ad_3",
                name="广告点击交互测试",
                description="测试广告点击后的跳转和返回功能",
                phase=TestPhase.FUNCTIONAL,
                tool_name="analyze_ad",
                parameters={"ad_type": "interstitial", "test_actions": ["点击广告", "关闭广告", "返回应用"], "verify_landing": True},
                priority=TaskPriority.MEDIUM
            )
        ]
    
    def _generate_navigation_tests(self) -> List[TestTask]:
        """生成UI导航测试用例"""
        return [
            TestTask(
                id="nav_1",
                name="主界面Tab切换测试",
                description="测试主界面各Tab页面的切换和加载",
                phase=TestPhase.FUNCTIONAL,
                tool_name="navigate_ui",
                parameters={"target_screens": ["首页", "发现", "个人中心"], "navigation_type": "tab_switch", "timeout": 5},
                priority=TaskPriority.HIGH
            ),
            TestTask(
                id="nav_2",
                name="页面深度导航测试",
                description="测试多级页面的导航和返回功能",
                phase=TestPhase.FUNCTIONAL,
                tool_name="navigate_ui",
                parameters={"navigation_path": ["首页", "图片详情", "用户主页", "设置"], "verify_back_navigation": True},
                priority=TaskPriority.HIGH
            ),
            TestTask(
                id="nav_3",
                name="手势导航测试",
                description="测试滑动、返回手势等导航操作",
                phase=TestPhase.FUNCTIONAL,
                tool_name="navigate_ui",
                parameters={"gesture_actions": ["左滑返回", "右滑前进", "下拉刷新"], "verify_gesture_response": True},
                priority=TaskPriority.MEDIUM
            )
        ]
    
    def _generate_performance_tests(self) -> List[TestTask]:
        """生成性能测试用例"""
        return [
            TestTask(
                id="perf_1",
                name="启动性能测试",
                description="测试应用冷热启动时间和内存占用",
                phase=TestPhase.PERFORMANCE,
                tool_name="performance_test",
                parameters={"metrics": ["冷启动时间", "热启动时间", "内存峰值"], "iterations": 5},
                priority=TaskPriority.HIGH
            ),
            TestTask(
                id="perf_2",
                name="页面加载性能测试",
                description="测试各页面加载时间和流畅度",
                phase=TestPhase.PERFORMANCE,
                tool_name="performance_test",
                parameters={"metrics": ["页面加载时间", "FPS", "CPU占用"], "target_pages": ["首页", "发现页", "个人中心"]},
                priority=TaskPriority.HIGH
            ),
            TestTask(
                id="perf_3",
                name="内存泄漏测试",
                description="测试长时间使用后的内存泄漏情况",
                phase=TestPhase.PERFORMANCE,
                tool_name="performance_test",
                parameters={"metrics": ["内存增长", "GC频率", "对象引用"], "duration": 300},
                priority=TaskPriority.MEDIUM
            )
        ]
    
    def _generate_security_tests(self) -> List[TestTask]:
        """生成安全测试用例"""
        return [
            TestTask(
                id="sec_1",
                name="权限申请合规性测试",
                description="验证应用权限申请的合规性和必要性",
                phase=TestPhase.SECURITY,
                tool_name="check_permissions",
                parameters={"permissions": ["存储", "相机", "位置", "麦克风"], "compliance_check": True},
                priority=TaskPriority.HIGH
            ),
            TestTask(
                id="sec_2",
                name="数据安全测试",
                description="测试敏感数据的存储和传输安全",
                phase=TestPhase.SECURITY,
                tool_name="check_permissions",
                parameters={"data_types": ["用户信息", "图片数据", "配置信息"], "encryption_check": True},
                priority=TaskPriority.MEDIUM
            ),
            TestTask(
                id="sec_3",
                name="反调试检测测试",
                description="测试应用的反调试和安全检测机制",
                phase=TestPhase.SECURITY,
                tool_name="check_permissions",
                parameters={"security_checks": ["root检测", "调试检测", "模拟器检测"], "bypass_attempts": 3},
                priority=TaskPriority.LOW
            )
        ]
    
    def _generate_comprehensive_tests(self) -> List[TestTask]:
        """生成综合测试用例（默认测试套件）"""
        return [
            TestTask(
                id="func_1",
                name="应用基础功能测试",
                description="测试应用的基本功能和用户交互",
                phase=TestPhase.FUNCTIONAL,
                tool_name="test_interactions",
                parameters={"test_scenarios": ["用户登录", "图片浏览", "功能操作"], "coverage_target": "基本功能"},
                priority=TaskPriority.HIGH
            ),
            TestTask(
                id="func_2",
                name="UI界面完整性测试",
                description="验证各界面元素的显示和布局",
                phase=TestPhase.FUNCTIONAL,
                tool_name="navigate_ui",
                parameters={"ui_checks": ["控件显示", "布局适配", "文本渲染"], "screen_sizes": ["小屏", "中屏", "大屏"]},
                priority=TaskPriority.MEDIUM
            ),
            TestTask(
                id="func_3",
                name="异常情况处理测试",
                description="测试网络异常、数据异常等场景的处理",
                phase=TestPhase.FUNCTIONAL,
                tool_name="test_interactions",
                parameters={"exception_scenarios": ["网络断开", "数据格式错误", "权限拒绝"], "recovery_check": True},
                priority=TaskPriority.MEDIUM
            )
        ]
    
    def _analyze_requirements_and_generate_tests(self, requirements: str) -> List[TestTask]:
        """智能分析需求并生成多样化的测试用例"""
        tasks = []
        
        # 1. 基础功能测试（总是包含）
        tasks.extend(self._generate_basic_functionality_tests())
        
        # 2. 基于关键词的专项测试
        if any(keyword in requirements.lower() for keyword in ["启动", "launch", "open", "begin"]):
            tasks.extend(self._generate_launch_tests())
        
        if any(keyword in requirements.lower() for keyword in ["广告", "ad", "banner", "interstitial"]):
            tasks.extend(self._generate_ad_tests())
        
        if any(keyword in requirements.lower() for keyword in ["导航", "navigate", "ui", "interface"]):
            tasks.extend(self._generate_navigation_tests())
        
        if any(keyword in requirements.lower() for keyword in ["性能", "performance", "speed", "响应"]):
            tasks.extend(self._generate_performance_tests())
        
        if any(keyword in requirements.lower() for keyword in ["安全", "security", "privacy", "权限"]):
            tasks.extend(self._generate_security_tests())
        
        # 3. 智能推断测试类型
        if "登录" in requirements or "register" in requirements.lower():
            tasks.extend(self._generate_auth_tests())
        
        if "支付" in requirements or "payment" in requirements.lower():
            tasks.extend(self._generate_payment_tests())
        
        if "搜索" in requirements or "search" in requirements.lower():
            tasks.extend(self._generate_search_tests())
        
        if "设置" in requirements or "settings" in requirements.lower():
            tasks.extend(self._generate_settings_tests())
        
        return tasks
    
    def _generate_basic_functionality_tests(self) -> List[TestTask]:
        """生成基础功能测试用例"""
        return [
            TestTask(
                id="basic_1",
                name="应用启动和初始化测试",
                description="测试应用冷启动、热启动和初始化流程",
                phase=TestPhase.FUNCTIONAL,
                tool_name="launch_app",
                parameters={
                    "package_name": "com.bluex.picflow", 
                    "activity": "MainActivity",
                    "test_scenarios": ["冷启动", "热启动", "后台恢复"]
                },
                priority=TaskPriority.CRITICAL
            ),
            TestTask(
                id="basic_2",
                name="主界面功能验证",
                description="验证主界面的核心功能和布局",
                phase=TestPhase.FUNCTIONAL,
                tool_name="validate_main_ui",
                parameters={
                    "ui_elements": ["导航栏", "功能按钮", "内容区域"],
                    "validation_timeout": 15
                },
                priority=TaskPriority.HIGH
            ),
            TestTask(
                id="basic_3",
                name="基础交互测试",
                description="测试用户与应用的基本交互功能",
                phase=TestPhase.FUNCTIONAL,
                tool_name="interact_with_app",
                parameters={
                    "interaction_types": ["点击", "滑动", "长按", "输入"],
                    "interaction_timeout": 10
                },
                priority=TaskPriority.HIGH
            )
        ]
    
    def _generate_edge_case_tests(self) -> List[TestTask]:
        """生成边界条件和异常情况测试"""
        return [
            TestTask(
                id="edge_1",
                name="网络异常场景测试",
                description="测试在网络异常情况下的应用行为",
                phase=TestPhase.FUNCTIONAL,
                tool_name="test_network_scenarios",
                parameters={
                    "scenarios": ["无网络", "弱网络", "网络切换", "DNS解析失败"],
                    "test_duration": 30
                },
                priority=TaskPriority.MEDIUM
            ),
            TestTask(
                id="edge_2",
                name="设备资源限制测试",
                description="测试在设备资源受限情况下的应用表现",
                phase=TestPhase.FUNCTIONAL,
                tool_name="test_resource_limits",
                parameters={
                    "limits": ["低内存", "低存储", "CPU占用高", "电池电量低"],
                    "monitor_metrics": ["内存使用", "CPU使用率", "电池消耗"]
                },
                priority=TaskPriority.MEDIUM
            ),
            TestTask(
                id="edge_3",
                name="异常输入测试",
                description="测试应用对异常输入的处理能力",
                phase=TestPhase.FUNCTIONAL,
                tool_name="test_abnormal_input",
                parameters={
                    "input_types": ["超长文本", "特殊字符", "空输入", "非法格式"],
                    "validation_rules": ["输入长度限制", "字符过滤", "格式验证"]
                },
                priority=TaskPriority.MEDIUM
            )
        ]
    
    def _generate_user_scenario_tests(self) -> List[TestTask]:
        """生成基于真实用户场景的测试用例"""
        return [
            TestTask(
                id="scenario_1",
                name="新用户首次使用场景",
                description="模拟新用户首次打开应用的完整流程",
                phase=TestPhase.FUNCTIONAL,
                tool_name="test_new_user_scenario",
                parameters={
                    "user_type": "新用户",
                    "scenario_steps": ["首次启动", "权限申请", "引导流程", "功能探索"],
                    "expected_behavior": "流畅的用户体验"
                },
                priority=TaskPriority.HIGH
            ),
            TestTask(
                id="scenario_2",
                name="日常使用场景测试",
                description="模拟用户日常使用应用的典型场景",
                phase=TestPhase.FUNCTIONAL,
                tool_name="test_daily_usage",
                parameters={
                    "user_type": "活跃用户",
                    "scenario_steps": ["快速启动", "核心功能使用", "多任务切换", "数据同步"],
                    "usage_pattern": "高频使用"
                },
                priority=TaskPriority.HIGH
            ),
            TestTask(
                id="scenario_3",
                name="深度使用场景测试",
                description="模拟用户深度使用应用的复杂场景",
                phase=TestPhase.FUNCTIONAL,
                tool_name="test_advanced_usage",
                parameters={
                    "user_type": "高级用户",
                    "scenario_steps": ["复杂操作", "高级功能", "个性化设置", "数据导出"],
                    "complexity_level": "高"
                },
                priority=TaskPriority.MEDIUM
            )
        ]
    
    def _generate_stress_and_performance_tests(self) -> List[TestTask]:
        """生成压力测试和性能基准测试"""
        return [
            TestTask(
                id="stress_1",
                name="长时间运行稳定性测试",
                description="测试应用在长时间运行下的稳定性",
                phase=TestPhase.PERFORMANCE,
                tool_name="test_long_running",
                parameters={
                    "duration_minutes": 60,
                    "monitor_metrics": ["内存泄漏", "CPU稳定性", "响应时间"],
                    "stress_level": "中等"
                },
                priority=TaskPriority.MEDIUM
            ),
            TestTask(
                id="stress_2",
                name="高并发场景测试",
                description="测试应用在高并发情况下的表现",
                phase=TestPhase.PERFORMANCE,
                tool_name="test_concurrent_usage",
                parameters={
                    "concurrent_users": 10,
                    "test_duration": 15,
                    "performance_metrics": ["响应时间", "错误率", "资源使用"]
                },
                priority=TaskPriority.MEDIUM
            ),
            TestTask(
                id="perf_1",
                name="性能基准测试",
                description="建立应用的性能基准",
                phase=TestPhase.PERFORMANCE,
                tool_name="benchmark_performance",
                parameters={
                    "metrics": ["启动时间", "内存使用", "CPU占用", "电池消耗"],
                    "baseline_requirements": "行业标准"
                },
                priority=TaskPriority.HIGH
            )
        ]
    
    def _generate_auth_tests(self) -> List[TestTask]:
        """生成认证相关测试用例"""
        return [
            TestTask(
                id="auth_1",
                name="用户登录流程测试",
                description="测试用户登录、注册、找回密码等认证流程",
                phase=TestPhase.FUNCTIONAL,
                tool_name="test_auth_flows",
                parameters={
                    "auth_types": ["登录", "注册", "找回密码", "第三方登录"],
                    "validation_criteria": ["安全性", "用户体验", "错误处理"]
                },
                priority=TaskPriority.HIGH
            )
        ]
    
    def _generate_payment_tests(self) -> List[TestTask]:
        """生成支付相关测试用例"""
        return [
            TestTask(
                id="payment_1",
                name="支付流程完整性测试",
                description="测试支付流程的完整性和安全性",
                phase=TestPhase.FUNCTIONAL,
                tool_name="test_payment_flows",
                parameters={
                    "payment_methods": ["支付宝", "微信支付", "银行卡"],
                    "test_scenarios": ["正常支付", "支付失败", "退款流程"]
                },
                priority=TaskPriority.HIGH
            )
        ]
    
    def _generate_search_tests(self) -> List[TestTask]:
        """生成搜索功能测试用例"""
        return [
            TestTask(
                id="search_1",
                name="搜索功能完整性测试",
                description="测试搜索功能的准确性和性能",
                phase=TestPhase.FUNCTIONAL,
                tool_name="test_search_functionality",
                parameters={
                    "search_types": ["关键词搜索", "模糊搜索", "高级搜索"],
                    "performance_metrics": ["响应时间", "搜索结果准确性", "排序逻辑"]
                },
                priority=TaskPriority.MEDIUM
            )
        ]
    
    def _generate_settings_tests(self) -> List[TestTask]:
        """生成设置功能测试用例"""
        return [
            TestTask(
                id="settings_1",
                name="设置功能完整性测试",
                description="测试设置功能的完整性和一致性",
                phase=TestPhase.FUNCTIONAL,
                tool_name="test_settings_functionality",
                parameters={
                    "setting_categories": ["通用设置", "隐私设置", "通知设置", "个性化设置"],
                    "validation_criteria": ["设置生效", "设置持久化", "设置同步"]
                },
                priority=TaskPriority.MEDIUM
            )
        ]
    
    def _generate_security_tests(self) -> List[TestTask]:
        """生成安全相关测试用例"""
        return [
            TestTask(
                id="security_1",
                name="数据安全测试",
                description="测试应用的数据安全和隐私保护",
                phase=TestPhase.SECURITY,
                tool_name="test_data_security",
                parameters={
                    "security_checks": ["数据加密", "权限控制", "隐私保护", "安全传输"],
                    "compliance_standards": ["GDPR", "CCPA", "本地法规"]
                },
                priority=TaskPriority.HIGH
            )
        ]
    
    def _group_tasks_by_phase(self, tasks: List[TestTask]) -> Dict[TestPhase, List[TestTask]]:
        """按测试阶段分组任务"""
        grouped = {}
        for task in tasks:
            if task.phase not in grouped:
                grouped[task.phase] = []
            grouped[task.phase].append(task)
        
        for phase in grouped:
            grouped[phase].sort(key=lambda t: t.priority.value)
        
        return grouped


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    planner = TestPlanner()
    plan = planner.create_test_plan("测试应用的插屏广告功能")
    print(f"测试计划: {plan.name}")
    print(f"计划ID: {plan.id}")
