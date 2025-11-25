# 部署配置文档

## 概述

本文档详细说明Appium测试代理系统的部署和配置流程，包括环境准备、依赖安装、配置设置和部署验证。

## 环境要求

### 操作系统
- **推荐**: Ubuntu 20.04+ / CentOS 8+ / Windows 10+ / macOS 10.15+
- **最低要求**: 4GB RAM, 20GB 磁盘空间

### 软件依赖

#### 必需软件
1. **Python 3.8+**
   ```bash
   # Ubuntu/Debian
   sudo apt update
   sudo apt install python3 python3-pip
   
   # CentOS/RHEL
   sudo yum install python3 python3-pip
   
   # macOS
   brew install python3
   
   # Windows
   # 从官网下载Python安装包
   ```

2. **Node.js 14+** (用于Appium)
   ```bash
   # Ubuntu/Debian
   curl -fsSL https://deb.nodesource.com/setup_16.x | sudo -E bash -
   sudo apt-get install -y nodejs
   
   # CentOS/RHEL
   curl -fsSL https://rpm.nodesource.com/setup_16.x | sudo bash -
   sudo yum install -y nodejs
   
   # macOS
   brew install node
   
   # Windows
   # 从官网下载Node.js安装包
   ```

3. **Java 8+** (Android SDK依赖)
   ```bash
   # Ubuntu/Debian
   sudo apt install openjdk-11-jdk
   
   # CentOS/RHEL
   sudo yum install java-11-openjdk-devel
   
   # macOS
   brew install openjdk@11
   
   # Windows
   # 从官网下载JDK安装包
   ```

#### Android开发环境

1. **Android SDK**
   ```bash
   # 下载Android Studio或命令行工具
   wget https://dl.google.com/android/repository/commandlinetools-linux-8512546_latest.zip
   unzip commandlinetools-linux-8512546_latest.zip
   mkdir -p android-sdk/cmdline-tools/latest
   mv cmdline-tools/* android-sdk/cmdline-tools/latest/
   
   # 设置环境变量
   export ANDROID_HOME=$PWD/android-sdk
   export PATH=$PATH:$ANDROID_HOME/cmdline-tools/latest/bin:$ANDROID_HOME/platform-tools
   
   # 接受许可证
   yes | sdkmanager --licenses
   
   # 安装必要组件
   sdkmanager "platform-tools" "platforms;android-30" "build-tools;30.0.3"
   ```

2. **Appium Server**
   ```bash
   # 全局安装Appium
   npm install -g appium
   
   # 安装Appium Doctor检查环境
   npm install -g appium-doctor
   
   # 检查环境
   appium-doctor
   ```

## 项目部署

### 1. 获取代码

```bash
# 克隆项目
git clone https://github.com/your-org/appium-agent.git
cd appium-agent

# 或下载ZIP包解压
```

### 2. 安装Python依赖

```bash
# 创建虚拟环境（推荐）
python3 -m venv venv

# 激活虚拟环境
# Linux/macOS
source venv/bin/activate
# Windows
venv\\Scripts\\activate

# 安装依赖
pip install -r requirements.txt

# 安装开发依赖（可选）
pip install -r requirements-dev.txt
```

### 3. 配置环境变量

创建 `.env` 文件：

```bash
# 复制示例配置
cp .env.example .env

# 编辑配置
nano .env
```

配置文件内容：

```ini
# Appium配置
APPIUM_SERVER_URL=http://localhost:4723
ANDROID_HOME=/path/to/android-sdk

# LLM配置（可选）
OPENAI_API_KEY=your-openai-api-key
LLM_PROVIDER=openai
LLM_MODEL=gpt-4

# 数据库配置（可选）
DATABASE_URL=sqlite:///test_results.db

# 日志配置
LOG_LEVEL=INFO
LOG_FILE=logs/appium_agent.log

# 代理配置
AGENT_NAME=appium-test-agent
MAX_CONCURRENT_TASKS=5
TASK_TIMEOUT_MINUTES=60
```

### 4. 配置文件设置

创建 `config.yaml` 文件：

```yaml
# 代理配置
agent:
  name: "appium-test-agent"
  version: "1.0.0"
  max_concurrent_tasks: 5
  timeout_minutes: 60
  retry_attempts: 3

# Appium配置
appium:
  server_url: "http://localhost:4723"
  desired_capabilities:
    platformName: "Android"
    platformVersion: "11.0"
    deviceName: "Android Emulator"
    automationName: "UiAutomator2"
    newCommandTimeout: 300

# 测试配置
testing:
  default_package: "com.example.app"
  test_timeout: 300
  screenshot_on_failure: true
  video_recording: false

# LLM配置（可选）
llm:
  provider: "openai"
  model: "gpt-4"
  api_key: "${OPENAI_API_KEY}"
  temperature: 0.1
  max_tokens: 2000

# 报告配置
reporting:
  output_dir: "reports"
  formats:
    - "html"
    - "markdown"
    - "json"
  include_screenshots: true
  include_logs: true
```

## 启动服务

### 1. 启动Appium Server

```bash
# 方式1: 直接启动
appium --log-level info --log-timestamp --local-timezone

# 方式2: 后台启动
appium --log-level info --log-timestamp --local-timezone &

# 方式3: 使用配置文件
appium --config appium-config.json
```

### 2. 启动测试代理

```bash
# 方式1: 直接运行
python main.py

# 方式2: 使用模块方式
python -m appium_agent

# 方式3: 开发模式（自动重载）
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### 3. 验证部署

```bash
# 检查Appium服务
curl http://localhost:4723/status

# 检查测试代理
curl http://localhost:8000/health

# 运行简单测试
python -c "from agent import Agent; print('Agent initialized successfully')"
```

## Docker部署

### 1. 构建Docker镜像

```dockerfile
# Dockerfile
FROM python:3.9-slim

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    wget \
    unzip \
    openjdk-11-jdk \
    android-sdk \
    && rm -rf /var/lib/apt/lists/*

# 安装Node.js
RUN curl -fsSL https://deb.nodesource.com/setup_16.x | bash - \
    && apt-get install -y nodejs

# 安装Appium
RUN npm install -g appium

# 设置工作目录
WORKDIR /app

# 复制项目文件
COPY . .

# 安装Python依赖
RUN pip install -r requirements.txt

# 暴露端口
EXPOSE 8000 4723

# 启动命令
CMD ["python", "main.py"]
```

### 2. 使用Docker Compose

```yaml
# docker-compose.yml
version: '3.8'

services:
  appium:
    image: appium/appium:latest
    ports:
      - "4723:4723"
    volumes:
      - ./config:/config
    environment:
      - APPIUM_HOST=0.0.0.0
      - APPIUM_PORT=4723

  agent:
    build: .
    ports:
      - "8000:8000"
    depends_on:
      - appium
    volumes:
      - ./reports:/app/reports
      - ./logs:/app/logs
    environment:
      - APPIUM_SERVER_URL=http://appium:4723
```

### 3. 部署命令

```bash
# 构建和启动
docker-compose up -d

# 查看日志
docker-compose logs -f

# 停止服务
docker-compose down
```

## 云平台部署

### AWS部署

1. **创建EC2实例**
   - 选择Amazon Linux 2或Ubuntu AMI
   - 配置安全组（开放4723, 8000端口）
   - 分配足够的存储和内存

2. **使用用户数据脚本**
   ```bash
   #!/bin/bash
   yum update -y
   yum install -y python3 python3-pip
   pip3 install -r requirements.txt
   python3 main.py
   ```

### Azure部署

1. **创建虚拟机**
   - 选择Ubuntu Server
   - 配置网络安全组
   - 使用自定义脚本扩展

2. **使用自定义脚本**
   ```bash
   #!/bin/bash
   apt update
   apt install -y python3 python3-pip
   pip3 install -r requirements.txt
   nohup python3 main.py &
   ```

### Kubernetes部署

```yaml
# deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: appium-agent
spec:
  replicas: 2
  selector:
    matchLabels:
      app: appium-agent
  template:
    metadata:
      labels:
        app: appium-agent
    spec:
      containers:
      - name: agent
        image: your-registry/appium-agent:latest
        ports:
        - containerPort: 8000
        env:
        - name: APPIUM_SERVER_URL
          value: "http://appium-service:4723"
---
apiVersion: v1
kind: Service
metadata:
  name: appium-agent-service
spec:
  selector:
    app: appium-agent
  ports:
  - protocol: TCP
    port: 8000
    targetPort: 8000
```

## 监控和维护

### 日志管理

```bash
# 查看实时日志
tail -f logs/appium_agent.log

# 日志轮转配置
# /etc/logrotate.d/appium-agent
/var/log/appium_agent.log {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
}
```

### 性能监控

```bash
# 监控系统资源
top
htop

# 监控网络连接
netstat -tulpn | grep 4723
netstat -tulpn | grep 8000

# 监控进程
ps aux | grep appium
ps aux | grep python
```

### 备份策略

```bash
# 备份测试结果
tar -czf test_results_backup_$(date +%Y%m%d).tar.gz reports/ sessions/

# 备份配置
cp config.yaml config_backup_$(date +%Y%m%d).yaml
cp .env .env_backup_$(date +%Y%m%d)
```

## 故障排除

### 常见问题

1. **Appium连接失败**
   ```bash
   # 检查Appium服务状态
   curl http://localhost:4723/status
   
   # 检查端口占用
   netstat -tulpn | grep 4723
   
   # 重启Appium服务
   pkill -f appium
   appium &
   ```

2. **Android设备未连接**
   ```bash
   # 检查设备连接
   adb devices
   
   # 重启ADB服务
   adb kill-server
   adb start-server
   
   # 检查USB调试
   adb devices -l
   ```

3. **Python依赖问题**
   ```bash
   # 重新安装依赖
   pip install --force-reinstall -r requirements.txt
   
   # 清理缓存
   pip cache purge
   ```

### 调试模式

```bash
# 启用详细日志
python main.py --log-level DEBUG

# 启用开发模式
python main.py --dev

# 单步调试
python -m pdb main.py
```

## 安全配置

### 网络安全

```yaml
# 防火墙配置
# 只允许必要端口
ufw allow 22    # SSH
ufw allow 4723  # Appium
ufw allow 8000  # Agent
ufw enable
```

### API安全

```python
# 添加认证中间件
from fastapi import Security, HTTPException
from fastapi.security import APIKeyHeader

api_key_header = APIKeyHeader(name="X-API-Key")

def verify_api_key(api_key: str = Security(api_key_header)):
    if api_key != os.getenv("API_KEY"):
        raise HTTPException(status_code=403, detail="Invalid API Key")
```

## 更新和维护

### 版本更新

```bash
# 拉取最新代码
git pull origin main

# 更新依赖
pip install -r requirements.txt

# 重启服务
sudo systemctl restart appium-agent
```

### 定期维护

```bash
# 清理旧日志
find logs/ -name "*.log" -mtime +7 -delete

# 清理临时文件
rm -rf tmp/*

# 更新系统包
sudo apt update && sudo apt upgrade
```

## 支持与帮助

- **文档**: 查看 `docs/` 目录获取详细文档
- **问题**: 提交Issue到项目仓库
- **社区**: 加入开发者社区讨论
- **邮件**: 发送邮件到 support@example.com

## 许可证

本项目采用 MIT 许可证。详情请查看 LICENSE 文件。