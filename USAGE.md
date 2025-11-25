# 🚀 Appium测试代理 - 使用说明

## 目录
- [项目概述](#项目概述)
- [环境要求](#环境要求)
- [快速开始](#快速开始)
- [核心功能](#核心功能)
- [配置说明](#配置说明)
- [API接口](#api接口)
- [故障排除](#故障排除)

## 项目概述

Appium测试代理是一个基于AI的自动化测试框架，集成了ADB工具、Appium自动化、性能监控和智能测试规划功能。

### 主要特性
- 🤖 **AI驱动的测试规划**：基于LLM的智能测试用例生成
- 📱 **多平台支持**：Android/iOS设备自动化测试
- 📊 **性能监控**：实时CPU、内存、帧率监控
- 🔍 **智能分析**：测试结果自动分析和验证
- 📋 **报告生成**：多种格式的测试报告

## 环境要求

### 系统要求
- **操作系统**: Windows 10/11, macOS 10.15+, Ubuntu 18.04+
- **Python**: 3.8 或更高版本
- **内存**: 最低 4GB，推荐 8GB+
- **磁盘空间**: 最低 2GB

### 前置依赖
1. **Android开发环境**
   - Android SDK
   - Java 8+
   - ADB工具

2. **Appium服务**
   ```bash
   npm install -g appium
   appium-doctor  # 检查环境
   ```

## 快速开始

### 1. 安装依赖

```bash
# 克隆项目
git clone <项目地址>
cd appium-agent

# 创建虚拟环境
python -m venv venv

# 激活虚拟环境
# Windows
venv\Scripts\activate
# Linux/macOS
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt
```

### 2. 环境配置

创建 `.env` 配置文件：

```bash
# 复制示例配置
cp .env.example .env
```

编辑 `.env` 文件：
```ini
# Appium配置
APPIUM_SERVER_URL=http://localhost:4723
ANDROID_HOME=C:\\Users\\YourName\\AppData\\Local\\Android\\Sdk

# LLM配置 (可选)
OPENAI_API_KEY=your-api-key-here
LLM_PROVIDER=openai
LLM_MODEL=gpt-4

# 日志配置
LOG_LEVEL=INFO
LOG_FILE=logs/appium_agent.log
```

### 3. 连接设备

确保Android设备已连接并启用USB调试：

```bash
# 检查设备连接
adb devices

# 预期输出
List of devices attached
1234567890ABCDEF    device
```

### 4. 启动测试

```python
# 基本使用示例
from agent import create_agent

# 创建测试代理
agent = create_agent()

# 执行简单测试
result = agent.run_test("测试应用启动功能")
print(result)
```

## 核心功能

### 1. 智能测试规划

```python
from planner import TestPlanner

# 创建测试规划器
planner = TestPlanner()

# 生成测试计划
plan = planner.create_test_plan(
    requirements="测试应用登录功能，包括用户名密码验证和错误处理",
    previous_bugs="登录按钮有时无法点击"
)

print(f"测试计划: {plan.name}")
print(f"预估时长: {plan.estimated_duration}秒")
```

### 2. 设备操作

```python
from adb_tools import AdbUITools, DeviceInfoCollector

# 获取设备信息
collector = DeviceInfoCollector()
devices = collector.collect_info()

# UI操作
tools = AdbUITools()

# 点击元素
result = tools.tap_element("#123")
print(result)

# 输入文本
result = tools.input_text("Hello World")
print(result)

# 滑动屏幕
result = tools.swipe_screen("up")
print(result)
```

### 3. 性能监控

```python
from adb_tools import AdvancedPerformanceMonitor

# 性能监控
monitor = AdvancedPerformanceMonitor()

# 监控应用性能
performance_data = monitor.monitor_performance(
    package_name="com.example.app",
    duration=60,  # 监控60秒
    interval=5    # 每5秒采样一次
)

print(f"平均CPU使用率: {performance_data['summary']['average_cpu_percent']}%")
print(f"平均内存使用: {performance_data['summary']['average_memory_mb']}MB")
```

### 4. 测试报告

```python
from reporter import ReportGenerator

# 生成报告
generator = ReportGenerator()
report = generator.generate_report(
    test_results=performance_data,
    format="html"  # 支持 html, markdown, json
)

# 保存报告
with open("test_report.html", "w", encoding="utf-8") as f:
    f.write(report)
```

## 配置说明

### 主要配置文件

#### config.yaml
```yaml
# 测试配置
test:
  timeout: 300  # 测试超时时间(秒)
  retry_count: 3  # 重试次数
  
# 设备配置
device:
  platform_name: "Android"
  platform_version: "11.0"
  device_name: "Android Emulator"
  
# Appium配置
appium:
  server_url: "http://localhost:4723"
  automation_name: "UiAutomator2"
  
# 性能监控
performance:
  sampling_interval: 5  # 采样间隔(秒)
  memory_threshold: 500  # 内存阈值(MB)
  cpu_threshold: 80  # CPU阈值(%)
```

### 环境变量

| 变量名 | 说明 | 默认值 |
|--------|------|--------|
| `APPIUM_SERVER_URL` | Appium服务器地址 | `http://localhost:4723` |
| `ANDROID_HOME` | Android SDK路径 | 系统环境变量 |
| `OPENAI_API_KEY` | OpenAI API密钥 | 无 |
| `LOG_LEVEL` | 日志级别 | `INFO` |

## API接口

### 主要类和方法

#### Agent类
```python
class Agent:
    def run_test(self, requirements: str) -> TestResult:
        """执行测试"""
        
    def analyze_results(self, test_data: Dict) -> AnalysisResult:
        """分析测试结果"""
        
    def generate_report(self, format: str = "html") -> str:
        """生成测试报告"""
```

#### TestPlanner类
```python
class TestPlanner:
    def create_test_plan(self, requirements: str, previous_bugs: str = None) -> TestPlan:
        """创建测试计划"""
        
    def optimize_strategy(self, historical_data: List[TestResult]) -> OptimizedStrategy:
        """优化测试策略"""
```

## 故障排除

### 常见问题

#### 1. ADB设备未识别
```bash
# 检查设备连接
adb devices

# 如果设备未显示，尝试：
# 1. 重新插拔USB线
# 2. 启用USB调试
# 3. 安装设备驱动
```

#### 2. Appium连接失败
```bash
# 检查Appium服务
appium --address 127.0.0.1 --port 4723

# 检查端口占用
netstat -ano | findstr :4723
```

#### 3. 依赖安装失败
```bash
# 使用国内镜像源
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple/

# 或使用conda
conda install --file requirements.txt
```

#### 4. 内存不足
```python
# 优化内存使用
import gc
gc.collect()  # 手动垃圾回收

# 减少采样频率
monitor.monitor_performance(interval=10)  # 每10秒采样
```

### 日志查看

项目日志保存在 `logs/` 目录：

```bash
# 查看实时日志
tail -f logs/appium_agent.log

# 搜索错误信息
grep "ERROR" logs/appium_agent.log
```

## 进阶使用

### 自定义测试策略

```python
from test_strategy_optimizer import TestStrategyOptimizer

# 创建策略优化器
optimizer = TestStrategyOptimizer()

# 训练自定义策略
optimizer.train(historical_data)

# 获取优化策略
strategy = optimizer.predict(test_requirements)
```

### 知识库集成

```python
from knowledge_base import VectorKnowledgeBase

# 初始化知识库
kb = VectorKnowledgeBase()

# 添加测试文档
kb.add_document("test_cases/login_test.md", "登录功能测试用例")

# 智能查询
results = kb.search("如何处理登录失败场景")
```

## 支持与贡献

### 获取帮助
- 📖 查看详细文档：`docs/` 目录
- 🐛 报告问题：GitHub Issues
- 💬 社区讨论：开发者论坛

### 贡献指南
1. Fork项目仓库
2. 创建功能分支
3. 提交更改
4. 创建Pull Request

## 许可证

本项目采用 MIT 许可证。详情请查看 LICENSE 文件。

---

**注意**: 本说明文档会随项目更新，请定期查看最新版本。