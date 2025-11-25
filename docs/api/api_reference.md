# API参考文档

## 概述

本文档详细说明Appium测试代理系统的所有API接口，包括核心模块的类、方法和参数说明。

## 核心模块API

### 1. 测试代理 (Agent)

#### Agent类

**文件**: `agent.py`

**功能**: 测试代理主类，负责协调所有测试活动

**主要方法**:

```python
class Agent:
    def __init__(self, config: Dict[str, Any]):
        """初始化测试代理"""
        
    async def run_test_plan(self, test_plan: TestPlan) -> TestResult:
        """执行测试计划"""
        
    async def execute_task(self, task: Task) -> TaskResult:
        """执行单个测试任务"""
        
    def get_status(self) -> AgentStatus:
        """获取代理状态"""
        
    def stop(self):
        """停止代理运行"""
```

### 2. 任务规划器 (Planner)

#### Planner类

**文件**: `planner.py`

**功能**: 将测试需求分解为具体的测试任务

**主要方法**:

```python
class Planner:
    def __init__(self, config: Dict[str, Any]):
        """初始化规划器"""
        
    def create_test_plan(self, requirements: str) -> TestPlan:
        """根据需求创建测试计划"""
        
    def decompose_requirements(self, requirements: str) -> List[TestPhase]:
        """分解需求为测试阶段"""
        
    def generate_tasks_for_phase(self, phase: TestPhase) -> List[Task]:
        """为测试阶段生成具体任务"""
```

#### TestPlan数据类

```python
@dataclass
class TestPlan:
    id: str
    name: str
    description: str
    phases: List[TestPhase]
    created_at: datetime
    status: TestPlanStatus
```

#### TestPhase数据类

```python
@dataclass
class TestPhase:
    name: str
    type: str  # 'smoke', 'functional', 'api', 'performance', 'regression'
    description: str
    tasks: List[Task]
    dependencies: List[str]
```

### 3. 工作流编排器 (Orchestrator)

#### WorkflowOrchestrator类

**文件**: `orchestrator.py`

**功能**: 编排测试任务的执行顺序和依赖关系

**主要方法**:

```python
class WorkflowOrchestrator:
    def __init__(self, config: Dict[str, Any]):
        """初始化编排器"""
        
    async def execute_workflow(self, test_plan: TestPlan) -> WorkflowResult:
        """执行完整工作流"""
        
    def get_task_dependencies(self, task: Task) -> List[Task]:
        """获取任务依赖关系"""
        
    def can_execute_task(self, task: Task, completed_tasks: List[Task]) -> bool:
        """检查任务是否可以执行"""
        
    async def execute_task_group(self, tasks: List[Task]) -> List[TaskResult]:
        """执行任务组（并发）"""
```

#### TaskStatus枚举

```python
class TaskStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
```

#### TaskResult数据类

```python
@dataclass
class TaskResult:
    task_id: str
    status: TaskStatus
    output: str
    error: Optional[str]
    start_time: datetime
    end_time: Optional[datetime]
    duration: Optional[float]
```

### 4. 状态管理器 (StateManager)

#### StateManager类

**文件**: `statemanager.py`

**功能**: 管理测试执行状态，支持断点续跑

**主要方法**:

```python
class StateManager:
    def __init__(self, storage_path: str):
        """初始化状态管理器"""
        
    def create_session(self, test_plan: TestPlan) -> str:
        """创建新的测试会话"""
        
    def save_task_result(self, session_id: str, task_result: TaskResult):
        """保存任务执行结果"""
        
    def get_session_state(self, session_id: str) -> SessionState:
        """获取会话状态"""
        
    def get_completed_tasks(self, session_id: str) -> List[TaskResult]:
        """获取已完成任务"""
        
    def get_pending_tasks(self, session_id: str) -> List[Task]:
        """获取待执行任务"""
        
    def resume_session(self, session_id: str) -> TestPlan:
        """恢复测试会话"""
```

#### SessionState数据类

```python
@dataclass
class SessionState:
    session_id: str
    test_plan: TestPlan
    completed_tasks: List[TaskResult]
    pending_tasks: List[Task]
    current_phase: str
    start_time: datetime
    last_update: datetime
    status: str  # 'running', 'paused', 'completed', 'failed'
```

### 5. 验证器 (Validator)

#### ResultValidator类

**文件**: `validator.py`

**功能**: 验证测试结果，支持规则和LLM双重验证

**主要方法**:

```python
class ResultValidator:
    def __init__(self, config: Dict[str, Any]):
        """初始化验证器"""
        
    async def validate(self, task_result: TaskResult, expected_result: str) -> ValidationResult:
        """验证测试结果"""
        
    def add_validation_rule(self, rule: ValidationRule):
        """添加验证规则"""
        
    def check_rules(self, task_result: TaskResult) -> List[RuleCheckResult]:
        """检查所有规则"""
        
    async def analyze_with_llm(self, task_result: TaskResult, expected_result: str) -> LLMAnalysisResult:
        """使用LLM分析结果"""
```

#### ValidationRule数据类

```python
@dataclass
class ValidationRule:
    name: str
    condition: str
    field: str
    operator: str  # 'equals', 'contains', 'greater_than', etc.
    value: Any
    severity: str  # 'critical', 'warning', 'info'
```

#### ValidationResult数据类

```python
@dataclass
class ValidationResult:
    is_valid: bool
    confidence: float
    rule_violations: List[RuleCheckResult]
    llm_analysis: Optional[LLMAnalysisResult]
    suggestions: List[str]
```

### 6. 报告生成器 (Reporter)

#### ReportGenerator类

**文件**: `reporter.py`

**功能**: 生成多种格式的测试报告

**主要方法**:

```python
class ReportGenerator:
    def __init__(self, config: Dict[str, Any]):
        """初始化报告生成器"""
        
    def generate_html_report(self, session_state: SessionState, output_path: str) -> str:
        """生成HTML格式报告"""
        
    def generate_markdown_report(self, session_state: SessionState, output_path: str) -> str:
        """生成Markdown格式报告"""
        
    def generate_json_report(self, session_state: SessionState, output_path: str) -> str:
        """生成JSON格式报告"""
        
    def generate_excel_report(self, session_state: SessionState, output_path: str) -> str:
        """生成Excel格式报告"""
        
    def calculate_statistics(self, session_state: SessionState) -> TestStatistics:
        """计算测试统计数据"""
```

#### TestStatistics数据类

```python
@dataclass
class TestStatistics:
    total_tasks: int
    completed_tasks: int
    failed_tasks: int
    skipped_tasks: int
    success_rate: float
    total_duration: float
    average_duration: float
    phase_statistics: Dict[str, PhaseStatistics]
```

## 工具API

### 设备连接工具

#### connect_devices
- **功能**: 连接Android设备并获取设备信息
- **参数**: 无
- **返回**: 设备连接状态和设备信息

### 基础操作工具

#### input_text
- **功能**: 在文本框输入文字
- **参数**: `text` (字符串)

#### swipe_screen  
- **功能**: 滑动屏幕
- **参数**: `start_x`, `start_y`, `end_x`, `end_y`, `duration` (可选)

#### press_key
- **功能**: 按下设备按键
- **参数**: `key_name` (字符串)

### 应用管理工具

#### launch_app
- **功能**: 启动应用
- **参数**: `package_name` (字符串)

### UI元素操作工具

#### get_ui_elements
- **功能**: 获取界面上的UI元素
- **参数**: `filters` (对象, 可选)

#### click_element
- **功能**: 点击UI元素
- **参数**: `identifier`, `by`

### 性能监测工具

#### get_memory_info
- **功能**: 获取应用内存使用情况
- **参数**: `package_name`

#### get_cpu_usage_by_package
- **功能**: 获取应用CPU使用率
- **参数**: `package_name`

#### get_fps_info
- **功能**: 获取应用帧率信息
- **参数**: `package_name`

#### get_app_startup_time
- **功能**: 测量应用启动时间
- **参数**: `package_name`, `count` (可选)

#### get_logcat
- **功能**: 获取应用日志
- **参数**: `package_name`, `lines` (可选)

#### get_performance_snapshot
- **功能**: 获取应用性能快照
- **参数**: `package_name`

#### monitor_performance
- **功能**: 持续监测应用性能
- **参数**: `package_name`, `duration`

### 广告分析工具

#### analyze_ad
- **功能**: 分析应用中的广告
- **参数**: `package_name`

## 配置参数

### Agent配置
```yaml
agent:
  name: "appium-test-agent"
  version: "1.0.0"
  max_concurrent_tasks: 5
  timeout_minutes: 60
  retry_attempts: 3
```

### Appium配置
```yaml
appium:
  server_url: "http://localhost:4723"
  desired_capabilities:
    platformName: "Android"
    platformVersion: "11.0"
    deviceName: "Android Emulator"
    app: "/path/to/app.apk"
    automationName: "UiAutomator2"
```

### LLM配置
```yaml
llm:
  provider: "openai"
  model: "gpt-4"
  api_key: "your-api-key"
  temperature: 0.1
  max_tokens: 2000
```

## 错误处理

### 常见错误码

- `AGENT_001`: 代理初始化失败
- `PLANNER_001`: 测试计划创建失败
- `ORCHESTRATOR_001`: 工作流执行失败
- `VALIDATOR_001`: 验证规则检查失败
- `REPORTER_001`: 报告生成失败

### 异常处理

所有API方法都使用标准的异常处理机制：

```python
try:
    result = await agent.run_test_plan(test_plan)
except AgentError as e:
    logger.error(f"代理执行失败: {e}")
    # 处理异常
```

## 使用示例

### 基本使用
```python
from agent import Agent
from planner import Planner

# 初始化代理
agent = Agent(config)
planner = Planner(config)

# 创建测试计划
test_plan = planner.create_test_plan("测试微信应用的基本功能")

# 执行测试
result = await agent.run_test_plan(test_plan)

# 生成报告
report = reporter.generate_html_report(result, "report.html")
```

### 断点续跑
```python
from statemanager import StateManager

# 恢复会话
state_manager = StateManager("./sessions")
session_state = state_manager.resume_session("session_123")

# 继续执行
result = await agent.run_test_plan(session_state.test_plan)
```

## 版本历史

- v1.0.0: 初始版本，包含完整的测试生命周期管理
- v1.1.0: 新增LLM验证功能
- v1.2.0: 增强报告生成功能

## 支持与反馈

如有问题或建议，请通过以下方式联系：
- 文档问题: 提交Issue到项目仓库
- 功能建议: 创建Feature Request
- Bug报告: 提供详细的错误信息和复现步骤