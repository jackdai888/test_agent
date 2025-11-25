# ⚡ 快速开始指南

## 5分钟上手Appium测试代理

### 第一步：环境准备 (1分钟)

1. **确保已安装Python 3.8+**
   ```bash
   python --version
   # 应该显示 Python 3.8.x 或更高版本
   ```

2. **安装基础依赖**
   ```bash
   # 创建虚拟环境
   python -m venv venv
   
   # 激活虚拟环境
   # Windows
   venv\Scripts\activate
   # Linux/macOS
   source venv/bin/activate
   ```

### 第二步：一键安装 (1分钟)

```bash
# 安装所有依赖
pip install -r requirements.txt

# 如果安装慢，使用国内镜像
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple/
```

### 第三步：基础配置 (1分钟)

1. **创建配置文件**
   ```bash
   # 复制示例配置
   copy .env.example .env
   ```

2. **编辑配置文件** (用文本编辑器打开 `.env`)
   ```ini
   # 基础配置
   APP_NAME="My Test App"
   LOG_LEVEL=INFO
   
   # 可选：AI功能配置
   # OPENAI_API_KEY=your-api-key-here
   ```

### 第四步：连接设备 (1分钟)

1. **连接Android设备**
   - 启用USB调试模式
   - 连接USB线

2. **验证连接**
   ```bash
   adb devices
   # 应该显示你的设备ID
   ```

### 第五步：运行第一个测试 (1分钟)

```python
# 创建 test_demo.py 文件
from adb_tools import AdbUITools

# 初始化工具
tools = AdbUITools()

# 获取设备信息
print("设备信息:", tools.get_device_info())

# 测试屏幕点击
result = tools.tap_element("#123")
print("点击结果:", result)

# 测试文本输入
result = tools.input_text("Hello Appium!")
print("输入结果:", result)
```

运行测试：
```bash
python test_demo.py
```

## 🎯 核心功能速览

### 1. 智能测试规划
```python
from planner import TestPlanner

planner = TestPlanner()
plan = planner.create_test_plan("测试登录功能")
print(plan)
```

### 2. 性能监控
```python
from adb_tools import AdvancedPerformanceMonitor

monitor = AdvancedPerformanceMonitor()
data = monitor.monitor_performance("com.example.app", duration=30)
print("性能数据:", data['summary'])
```

### 3. 生成报告
```python
from reporter import ReportGenerator

generator = ReportGenerator()
report = generator.generate_report(test_data, format="markdown")
print(report)
```

## 🚨 常见问题速查

### Q: 设备连接失败？
**A:** 检查USB调试是否开启，运行 `adb devices` 验证

### Q: 依赖安装失败？
**A:** 使用国内镜像源：`-i https://pypi.tuna.tsinghua.edu.cn/simple/`

### Q: 找不到模块？
**A:** 确保虚拟环境已激活，重新运行 `pip install -r requirements.txt`

## 📚 下一步

- 📖 查看详细文档：`USAGE.md`
- 🔧 了解高级配置：`docs/` 目录
- 🐛 报告问题：查看 `ISSUES.md`

---

**提示**: 遇到问题？先检查上面的常见问题，或查看详细文档！