# Appium测试代理快速入门指南

## 🚀 快速开始

### 1. 环境准备

#### 系统要求
- Android设备或模拟器
- ADB工具已安装并配置
- Appium Server运行中

#### 安装依赖
```bash
# 克隆项目
git clone <repository-url>
cd appium-agent

# 创建虚拟环境
python -m venv .venv

# 激活虚拟环境
# Windows:
.venv\\Scripts\\activate
# Linux/Mac:
source .venv/bin/activate

# 安装依赖
pip install -r requirements.txt
```

### 2. 配置设置

#### 修改配置文件
在项目根目录创建或修改 `.env` 文件：
```env
# OpenAI API配置
OPENAI_API_KEY=your_openai_api_key
OPENAI_BASE_URL=https://api.openai.com/v1

# Claude API配置  
ANTHROPIC_API_KEY=your_anthropic_api_key
CLAUDE_BASE_URL=https://api.anthropic.com

# Appium配置
APPIUM_SERVER_URL=http://localhost:4723

# 设备配置
DEFAULT_DEVICE_ID=your_device_id
```

#### 验证设备连接
```bash
# 检查设备连接
adb devices

# 启动Appium Server
appium
```

### 3. 启动测试代理

#### 方式一：命令行启动
```bash
python agent.py
```

#### 方式二：交互式启动
```python
from agent import TestAgent

# 创建代理实例
agent = TestAgent()

# 开始对话
agent.start_conversation()
```

### 4. 基本使用示例

#### 示例1：简单测试任务
```
用户：帮我测试微信的登录功能

代理：好的，我将为您测试微信登录功能：
1. 连接设备并启动微信
2. 检查登录页面元素
3. 测试正确登录流程
4. 测试错误密码处理
5. 验证登录成功状态
```

#### 示例2：性能测试
```
用户：测试抖音应用的启动性能

代理：好的，我将测试抖音应用的启动性能：
1. 测量冷启动时间
2. 测量热启动时间  
3. 监测启动过程中的CPU和内存使用
4. 生成性能报告
```

#### 示例3：广告测试
```
用户：测试应用中的广告展示功能

代理：好的，我将测试广告展示功能：
1. 验证广告容器加载
2. 测试广告点击跳转
3. 监测广告加载性能
4. 检查广告关闭功能
```

### 5. 核心功能说明

#### 智能任务规划
代理能够将自然语言需求分解为具体的测试任务：
- **需求分析**：理解用户意图
- **任务分解**：拆分为可执行步骤
- **工具分配**：选择合适的测试工具
- **参数配置**：自动设置测试参数

#### 自动化执行
- **设备连接**：自动检测和连接设备
- **UI操作**：智能识别和操作界面元素
- **性能监测**：实时监控应用性能指标
- **结果验证**：自动验证测试结果

#### 报告生成
- **HTML报告**：可视化测试结果
- **Markdown报告**：便于文档管理
- **JSON数据**：支持数据分析和集成

### 6. 常用命令示例

#### 设备操作
- "连接设备"
- "启动微信"
- "点击登录按钮"
- "输入用户名和密码"

#### 性能测试  
- "测试应用启动时间"
- "监测内存使用情况"
- "检查CPU占用率"
- "获取帧率信息"

#### 功能测试
- "测试登录功能"
- "验证支付流程"
- "检查页面跳转"
- "测试表单提交"

### 7. 故障排除

#### 常见问题
1. **设备连接失败**：检查USB调试是否开启
2. **Appium连接失败**：确认Appium Server运行正常
3. **API调用失败**：验证API密钥和网络连接
4. **元素找不到**：检查应用界面和元素定位方式

#### 获取帮助
- 查看详细文档：`docs/` 目录
- 查看API说明：`docs/api/` 目录
- 故障排除：`docs/guides/troubleshooting.md`

### 8. 下一步

完成快速入门后，您可以：
1. 查看详细的功能文档
2. 学习高级使用技巧
3. 了解架构设计原理
4. 参与项目开发和贡献

---

**注意**：首次使用时建议从简单的测试任务开始，逐步熟悉代理的各项功能。