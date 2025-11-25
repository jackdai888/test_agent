# ==================== 基础导入 ====================
import os
import sys
import logging
from typing import TypedDict, List, Annotated

# ==================== LangChain相关导入 ====================
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from langchain_core.tools import tool
from langgraph.graph import StateGraph, START, END, add_messages
from langgraph.prebuilt import ToolNode
from langgraph.checkpoint.memory import InMemorySaver

# ==================== 日志配置 ====================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('agent.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ==================== 设备工具导入 ====================
# ADB工具类 - 用于基础设备操作
from adb_tools import DeviceInfoCollector, AdbUITools

# Appium工具类 - 用于高级UI自动化测试
from appium_tools import driver_init, driver_quit, AppiumUITools

# 知识库工具类 - 用于智能文档查询
from knowledge_base import VectorKnowledgeBase

# 测试工程组件（已集成）
from statemanager import StateManager
from memory import ConversationMemory

# 测试编排和规划组件
from orchestrator import WorkflowOrchestrator, TestPhase, TaskStatus
from planner import TestPlanner, TestPlan

# 报告生成器
from reporter import ReportGenerator

# 添加项目路径到系统路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# ==================== 配置部分 ====================

# 初始化模型 - 多厂商备用方案
# 支持BMC Claude API、OpenAI、本地模型等多种选择

def create_model_with_fallback():
    """创建模型，支持多厂商备用方案"""
    
    # 方案1: BMC Claude API (主要) - 使用具有图像识别功能的claude-sonnet-4-5-20250929
    try:
        claude_api_key = ""
        claude_base_url = ""
        
        model = ChatAnthropic(
            model="claude-sonnet-4-5-20250929",
            temperature=0.7,
            base_url=claude_base_url,
            api_key=claude_api_key
        )
        logger.info("✅ 使用BMC Claude API (claude-sonnet-4-5-20250929) - 具有图像识别功能")
        return model
    except Exception as e:
        logger.warning(f"BMC Claude API不可用: {e}")
    
    # 方案2: OpenAI API (备用)
    try:
        openai_api_key = os.getenv("OPENAI_API_KEY")
        if openai_api_key:
            from langchain_openai import ChatOpenAI
            model = ChatOpenAI(
                model="gpt-4o-mini",
                temperature=0.7,
                api_key=openai_api_key
            )
            logger.info("✅ 使用OpenAI GPT-4o-mini")
            return model
    except Exception as e:
        logger.warning(f"OpenAI API不可用: {e}")
    
    # 如果所有方案都失败，抛出异常
    raise Exception("所有模型方案都不可用，请检查网络连接或API配置")

# 创建模型
model = create_model_with_fallback()
primary_model = model

# ==================== 初始化记忆和状态管理 ====================
# 全局单例，用于跨会话保存测试状态
test_memory = ConversationMemory(max_turns=20)  # 记住最近20轮对话
test_state_manager = StateManager()  # 持久化测试状态到文件

logger.info("记忆管理器已初始化")
logger.info("状态管理器已初始化")

# ==================== 错误处理装饰器 ====================
def handle_tool_errors(func):
    """工具函数错误处理装饰器"""
    def wrapper(*args, **kwargs):
        try:
            logger.info(f"调用工具: {func.__name__}")
            result = func(*args, **kwargs)
            logger.info(f"工具 {func.__name__} 执行成功")
            return result
        except Exception as e:
            error_msg = f"工具 {func.__name__} 执行失败: {str(e)}"
            logger.error(error_msg)
            return f"❌ {error_msg}"
    return wrapper

# ==================== API重试机制 ====================
# 请求频率控制
import time
import random
from threading import Lock

# 全局请求频率控制
last_request_time = 0
request_lock = Lock()
MIN_REQUEST_INTERVAL = 2.0  # 最小请求间隔2秒

def api_call_with_retry(func, max_retries=5, delay=3):
    """API调用重试机制，处理速率限制"""
    
    def wrapper(*args, **kwargs):
        # 请求频率控制
        global last_request_time
        with request_lock:
            current_time = time.time()
            time_since_last_request = current_time - last_request_time
            if time_since_last_request < MIN_REQUEST_INTERVAL:
                wait_time = MIN_REQUEST_INTERVAL - time_since_last_request
                logger.info(f"请求频率控制，等待{wait_time:.1f}秒")
                time.sleep(wait_time)
            last_request_time = time.time()
        
        for attempt in range(max_retries):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                error_str = str(e)
                
                # 检测不同类型的API限制
                if any(keyword in error_str for keyword in ["RateLimitError", "429", "TPM", "quota", "limit"]):
                    # 指数退避 + 随机抖动
                    wait_time = delay * (2 ** attempt) + random.uniform(0, 1)
                    logger.warning(f"API速率限制，第{attempt+1}次重试，等待{wait_time:.1f}秒")
                    time.sleep(wait_time)
                    continue
                elif "timeout" in error_str.lower() or "timed out" in error_str.lower():
                    # 超时错误，等待时间较短
                    wait_time = delay + random.uniform(0, 0.5)
                    logger.warning(f"API超时，第{attempt+1}次重试，等待{wait_time:.1f}秒")
                    time.sleep(wait_time)
                    continue
                elif "5" in error_str and "server" in error_str.lower():
                    # 服务器错误，等待时间较长
                    wait_time = delay * (2 ** attempt) + random.uniform(1, 2)
                    logger.warning(f"服务器错误，第{attempt+1}次重试，等待{wait_time:.1f}秒")
                    time.sleep(wait_time)
                    continue
                else:
                    # 其他错误，直接抛出
                    raise e
        # 如果所有重试都失败
        raise Exception(f"API调用失败，已重试{max_retries}次")
    return wrapper


# ==================== 工具定义模块 ====================

# ==================== 知识库查询工具 ====================
@tool
def search_knowledge_base(query: str) -> str:
    """
    查询知识库获取相关信息
    
    参数:
    - query: 查询问题或关键词
    
    返回:
    - 知识库中相关的文档信息
    """
    try:
        logger.info(f"调用工具: search_knowledge_base, 参数: {query}")
        
        # 初始化知识库
        kb = VectorKnowledgeBase()
        
        # 执行搜索
        results = kb.search(query, top_k=3)
        
        if not results:
            return "❌ 知识库中没有找到相关信息"
        
        # 格式化结果
        response = f"🔍 知识库查询结果 (查询: '{query}'):\n"
        response += "=" * 60 + "\n"
        
        for i, doc in enumerate(results, 1):
            response += f"\n📄 结果 {i} (相似度: {doc['score']:.2f}):\n"
            response += f"   来源: {doc['source']}\n"
            response += f"   标题: {doc['title']}\n"
            response += f"   内容: {doc['content'][:200]}...\n"
            response += "-" * 40 + "\n"
        
        logger.info("工具 search_knowledge_base 执行成功")
        return response
        
    except Exception as e:
        error_msg = f"工具 search_knowledge_base 执行失败: {str(e)}"
        logger.error(error_msg)
        return f"❌ {error_msg}"


# ==================== 设备连接工具 ====================
@tool
def connect_devices() -> str:
    """连接设备并返回设备信息"""
    try:
        logger.info("调用工具: connect_devices")
        # 获取设备信息
        collector = DeviceInfoCollector()
        device_info = collector.collect_info()
        # 初始化驱动连接
        driver = driver_init(device_info)

        # 将设备信息传递给AppiumUITools
        if device_info and "deviceId" in device_info:
            # 设置AppiumUITools的设备信息
            from appium_tools import AppiumUITools
            AppiumUITools.set_device_info(device_info)
            logger.info("设备信息已传递给AppiumUITools")

        if device_info and driver:
            result = f"✅ 设备已成功连接。设备信息: {device_info}"
            logger.info("工具 connect_devices 执行成功")
            return result
        elif not driver:
            result = "⚠️ 无法初始化设备连接，但获取了设备信息：" + str(device_info)
            logger.warning("工具 connect_devices 部分成功")
            return result
        else:
            result = "❌ 无法获取设备信息"
            logger.error("工具 connect_devices 执行失败")
            return result
    except Exception as e:
        error_msg = f"工具 connect_devices 执行失败: {str(e)}"
        logger.error(error_msg)
        return f"❌ {error_msg}"

# ==================== 基础操作工具 ====================
@tool
def input_text(text: str) -> str:
    """
    在Android设备当前焦点处（如文本框）输入文本。
    参数:
    - text: 要输入的文本内容
    """
    try:
        logger.info(f"调用工具: input_text, 参数: {text}")
        result = AdbUITools.input_text(text)
        logger.info("工具 input_text 执行成功")
        return result
    except Exception as e:
        error_msg = f"工具 input_text 执行失败: {str(e)}"
        logger.error(error_msg)
        return f"❌ {error_msg}"

@tool
def swipe_screen(start_x: int, start_y: int, end_x: int, end_y: int, duration: int = 500, device_id: str = None) -> str:
    """
    在设备屏幕上滑动
    参数:
    - start_x: 起始点X坐标
    - start_y: 起始点Y坐标
    - end_x: 终点X坐标
    - end_y: 终点Y坐标
    - duration: 滑动持续时间（毫秒）
    - device_id: 设备ID（可选）
    """
    from appium_tools import AppiumUITools
    return AppiumUITools.swipe_screen(start_x, start_y, end_x, end_y, duration, device_id)

@tool
def press_key(key_name: str, device_id: str = None) -> str:
    """
    按下指定按键
    
    参数:
        key_name (str): 按键名称
            - 导航键: "back"(返回), "home"(主页), "menu"(菜单), "recent"(最近应用)
            - 电源键: "power"(电源), "sleep"(休眠), "wakeup"(唤醒)
            - 音量键: "volume_up"(音量+), "volume_down"(音量-), "volume_mute"(静音)
            - 媒体键: "media_play"(播放), "media_pause"(暂停), "media_next"(下一首), "media_previous"(上一首)
            - 方向键: "dpad_up"(上), "dpad_down"(下), "dpad_left"(左), "dpad_right"(右), "dpad_center"(确定)
            - 功能键: "f1"-"f12"(功能键), "tab"(制表符), "enter"(回车), "delete"(删除)
            - 数字键: "0"-"9"(数字键), "*"(星号), "#"(井号)
            - 字母键: "a"-"z"(字母键)
        device_id: 设备ID（可选）
    
    返回:
        执行结果
    
    按键码映射表:
        # 导航键
        "back": 4, "home": 3, "menu": 82, "recent": 187
        # 电源键
        "power": 26, "sleep": 26, "wakeup": 224
        # 音量键
        "volume_up": 24, "volume_down": 25, "volume_mute": 164
        # 媒体键
        "media_play": 126, "media_pause": 127, "media_next": 87, "media_previous": 88
        # 方向键
        "dpad_up": 19, "dpad_down": 20, "dpad_left": 21, "dpad_right": 22, "dpad_center": 23
        # 功能键
        "f1": 131, "f2": 132, "f3": 133, "f4": 134, "f5": 135, "f6": 136, "f7": 137, "f8": 138,
        "f9": 139, "f10": 140, "f11": 141, "f12": 142, "tab": 61, "enter": 66, "delete": 67
        # 数字键
        "0": 7, "1": 8, "2": 9, "3": 10, "4": 11, "5": 12, "6": 13, "7": 14, "8": 15, "9": 16,
        "*": 17, "#": 18
        # 字母键
        "a": 29, "b": 30, "c": 31, "d": 32, "e": 33, "f": 34, "g": 35, "h": 36, "i": 37, "j": 38,
        "k": 39, "l": 40, "m": 41, "n": 42, "o": 43, "p": 44, "q": 45, "r": 46, "s": 47, "t": 48,
        "u": 49, "v": 50, "w": 51, "x": 52, "y": 53, "z": 54
    
    使用示例:
        press_key("back")  # 返回
        press_key("home")  # 回到桌面
        press_key("volume_up")  # 音量+
        press_key("volume_down")  # 音量-
        press_key("menu")  # 菜单键
        press_key("power")  # 电源键
        press_key("dpad_up")  # 方向上键
        press_key("enter")  # 回车键
    """
    from appium_tools import AppiumUITools
    return AppiumUITools.press_key(key_name, device_id)



# ==================== 应用管理工具 ====================
@tool
def launch_app(package_name: str) -> str:
    """
    在Android设备上启动指定的应用程序。
    参数:
    - package_name: 应用包名，如 com.example.app
    """
    try:
        logger.info(f"调用工具: launch_app, 参数: {package_name}")
        result = AdbUITools.launch_app(package_name)
        logger.info("工具 launch_app 执行成功")
        return result
    except Exception as e:
        error_msg = f"工具 launch_app 执行失败: {str(e)}"
        logger.error(error_msg)
        return f"❌ {error_msg}"



# ==================== UI元素操作工具 ====================
@tool
def get_ui_elements(filters: dict = None, device_id: str = None) -> str:
    """
    获取界面元素信息（支持过滤）
    
    参数:
        filters (dict, optional): 过滤条件
            - text: 按文本过滤，如 {"text": "登录"}
            - class_name: 按类名过滤，如 {"class_name": "android.widget.Button"}
            - resource_id: 按ID过滤，如 {"resource_id": "com.app:id/btn"}
            - None: 返回所有元素
        device_id: 设备ID（可选）
    
    返回:
        匹配的元素列表
    
    实现示例:
        # 使用Appium的find_elements方法进行元素查找
        # 1. 按文本查找: driver.find_elements(AppiumBy.XPATH, f"//*[contains(@text, '{text}')]")
        # 2. 按类名查找: driver.find_elements(AppiumBy.CLASS_NAME, class_name)
        # 3. 按ID查找: driver.find_elements(AppiumBy.ID, resource_id)
        # 4. 组合过滤: 使用多个条件进行精确匹配
    
    使用示例:
        # 查找文本为"登录"的元素
        get_ui_elements({"text": "登录"})
        
        # 查找所有按钮
        get_ui_elements({"class_name": "android.widget.Button"})
        
        # 查找特定ID的元素
        get_ui_elements({"resource_id": "com.tencent.mm:id/btn_login"})
        
        # 组合过滤（文本和类名）
        get_ui_elements({"text": "登录", "class_name": "android.widget.Button"})
        
        # 获取所有元素
        get_ui_elements()
        
        # 获取可点击的元素
        get_ui_elements({"clickable": True})
    """
    try:
        logger.info(f"调用工具: get_ui_elements, 参数: filters={filters}, device_id={device_id}")
        appium_tools = AppiumUITools()
        result = appium_tools.get_ui_elements_with_filters(filters, device_id)
        logger.info("工具 get_ui_elements 执行成功")
        return result
    except Exception as e:
        error_msg = f"工具 get_ui_elements 执行失败: {str(e)}"
        logger.error(error_msg)
        return f"❌ {error_msg}"



@tool
def click_element(element_identifier: str, by: str = "text") -> str:
    """
    点击指定的UI元素。
    参数:
    - element_identifier: 元素标识符（文本、类名或resource-id）
    - by: 查找方式，可选值："text"（文本）、"class"（类名）、"id"（resource-id）
    """
    try:
        logger.info(f"调用工具: click_element, 参数: {element_identifier}, 方式: {by}")
        appium_tools = AppiumUITools()
        result = appium_tools.click_element(element_identifier, by)
        logger.info("工具 click_element 执行成功")
        return result
    except Exception as e:
        error_msg = f"工具 click_element 执行失败: {str(e)}"
        logger.error(error_msg)
        return f"❌ {error_msg}"





@tool
def analyze_ad(package_name=None, analysis_type="comprehensive") -> str:
    """
    分析广告相关信息
    
    参数:
        package_name (str, optional): 应用包名，None表示分析当前界面
        analysis_type (str): 分析类型
            - "comprehensive": 综合分析（默认）
            - "sdk": 仅分析SDK
            - "types": 仅分析广告类型
            - "behavior": 仅分析行为
    
    返回:
        {
            "sdk_info": {SDK信息},
            "ad_types": [广告类型],
            "behaviors": [行为分析],
            "recommendations": [优化建议]
        }
    
    示例:
        # 综合分析
        analyze_ad("com.app.test")
        
        # 仅分析SDK
        analyze_ad("com.app.test", "sdk")
    """
    try:
        logger.info(f"调用工具: analyze_ad, package_name={package_name}, analysis_type={analysis_type}")
        # 占位实现 - 实际应该调用广告分析模块
        result = {
            "sdk_info": {"ad_sdks": [], "version_info": {}},
            "ad_types": [],
            "behaviors": [],
            "recommendations": ["建议优化广告加载策略"]
        }
        logger.info("工具 analyze_ad 执行成功")
        return str(result)
    except Exception as e:
        error_msg = f"工具 analyze_ad 执行失败: {str(e)}"
        logger.error(error_msg)
        return f"❌ {error_msg}"

# ==================== 工具分类管理 ====================
# 设备连接相关工具
device_tools = [connect_devices]

# 基础操作相关工具
basic_operation_tools = [input_text, swipe_screen, press_key]

# 应用管理相关工具
app_management_tools = [launch_app]

# UI元素操作相关工具
ui_element_tools = [get_ui_elements, click_element]

# 分析工具
analysis_tools = [analyze_ad]

# 性能监测工具
from adb_tools import AdvancedPerformanceMonitor

@tool
def get_battery_status(device_id: str = None) -> str:
    """
    获取设备电池状态
    参数:
    - device_id: 设备ID（可选）
    """
    from adb_tools import PerformanceMonitor
    return PerformanceMonitor.get_battery_status(device_id)

# 高级性能监测工具
@tool
def get_memory_info(package_name: str, device_id: str = None) -> str:
    """
    获取指定应用的内存详细信息
    参数:
    - package_name: 应用包名
    - device_id: 设备ID（可选）
    """
    return AdvancedPerformanceMonitor.get_memory_info(package_name, device_id)

@tool
def get_cpu_usage_by_package(package_name: str, device_id: str = None) -> str:
    """
    获取指定应用的CPU使用率
    参数:
    - package_name: 应用包名
    - device_id: 设备ID（可选）
    """
    return AdvancedPerformanceMonitor.get_cpu_usage_by_package(package_name, device_id)

@tool
def get_fps_info(package_name: str, device_id: str = None) -> str:
    """
    获取指定应用的帧率信息
    参数:
    - package_name: 应用包名
    - device_id: 设备ID（可选）
    """
    return AdvancedPerformanceMonitor.get_fps_info(package_name, device_id)

@tool
def get_app_startup_time(package_name: str, activity_name: str = None, device_id: str = None) -> str:
    """
    获取应用启动时间
    参数:
    - package_name: 应用包名
    - activity_name: 活动名（可选）
    - device_id: 设备ID（可选）
    """
    return AdvancedPerformanceMonitor.get_app_startup_time(package_name, activity_name, device_id)

@tool
def get_logcat(keyword: str = None, level: str = "ERROR", package_name: str = None, device_id: str = None) -> str:
    """
    获取应用日志
    参数:
    - keyword: 关键词过滤（可选）
    - level: 日志级别（ERROR/WARN/INFO/DEBUG，默认ERROR）
    - package_name: 应用包名（可选）
    - device_id: 设备ID（可选）
    """
    return AdvancedPerformanceMonitor.get_logcat(keyword, level, package_name, device_id)

@tool
def get_performance_snapshot(package_name: str, metrics: list = None, device_id: str = None) -> str:
    """
    获取应用性能快照
    
    参数:
        package_name (str): 应用包名
        metrics (list, optional): 要获取的指标，默认全部
            可选: ["cpu", "memory", "fps", "battery"]
        device_id: 设备ID（可选）
    
    返回:
        {
            "cpu": {"usage": 15.5, "threads": 25},
            "memory": {"pss": 120MB, "heap": 80MB},
            "fps": {"current": 58, "avg": 59.5},
            "battery": {"level": 85, "temp": 35}
        }
    
    示例:
        # 获取所有指标
        get_performance_snapshot("com.app.test")
        
        # 只获取CPU和内存
        get_performance_snapshot("com.app.test", ["cpu", "memory"])
    """
    return AdvancedPerformanceMonitor.get_performance_snapshot(package_name, metrics, device_id)

@tool
def monitor_performance(package_name: str, duration: int = 60, interval: int = 5, metrics: list = None, device_id: str = None) -> str:
    """
    持续监测应用性能
    
    参数:
        package_name (str): 应用包名
        duration (int): 监测时长（秒），默认60
        interval (int): 采样间隔（秒），默认5
        metrics (list, optional): 监测指标，默认["cpu", "memory", "fps"]
        device_id (str, optional): 设备ID
    
    返回:
        {
            "summary": {统计摘要},
            "timeline": [时间序列数据],
            "alerts": [异常告警]
        }
    
    示例:
        # 监测60秒，每5秒采样一次
        monitor_performance("com.app.test")
        
        # 自定义监测
        monitor_performance("com.app.test", duration=120, interval=10, metrics=["memory"])
    """
    return AdvancedPerformanceMonitor.monitor_performance(package_name, duration, interval, metrics, device_id)

# 性能监测工具
performance_tools = []

# 高级性能监测工具
advanced_performance_tools = [
    get_memory_info,
    get_cpu_usage_by_package,
    get_fps_info,
    get_app_startup_time,
    get_logcat,
    get_performance_snapshot,
    monitor_performance
]

# 知识库查询工具
knowledge_base_tools = [search_knowledge_base]

# ==================== 测试规划工具 ====================
@tool
def create_test_plan(requirement: str) -> str:
    """
    创建测试计划 - 这是测试的第一步
    
    参数:
        requirement (str): 测试需求描述，例如：
            "测试插屏广告功能，包括：
             1. 广告是否正确加载
             2. 关闭按钮是否可点击
             3. 关闭后是否返回正常界面"
    
    返回:
        测试计划，包含分阶段的测试任务
    
    使用示例:
        create_test_plan("测试应用启动时的插屏广告功能")
    """
    try:
        logger.info(f"调用工具: create_test_plan, 需求: {requirement}")
        
        # 简化版规划器 - 使用 AI 模型生成测试计划
        prompt = f"""你是一个专业的测试工程师。请为以下需求制定详细的测试计划。

需求:
{requirement}

请按照以下测试阶段规划:
1. 🔥 冒烟测试 (Smoke) - 基本功能检查
2. ⚙️ 功能测试 (Functional) - 详细功能验证
3. 🔄 回归测试 (Regression) - 确保无破坏

对于每个测试任务，请说明:
- 任务ID（如 smoke_1, func_1）
- 测试阶段
- 详细描述
- 需要使用的工具
- 优先级（1-5）
- 预期结果

请以清晰的格式返回测试计划。
"""
        
        response = primary_model.invoke([HumanMessage(content=prompt)])
        plan = response.content
        
        result = f"✅ 测试计划已生成:\n\n{plan}"
        logger.info("工具 create_test_plan 执行成功")
        return result
        
    except Exception as e:
        error_msg = f"工具 create_test_plan 执行失败: {str(e)}"
        logger.error(error_msg)
        return f"❌ {error_msg}"


@tool
def create_test_case(test_scenario: str, expected_result: str = None) -> str:
    """
    生成具体的测试用例
    
    参数:
        test_scenario (str): 测试场景描述
        expected_result (str): 预期结果（可选）
    
    返回:
        详细的测试用例，包含步骤和检查点
    
    使用示例:
        create_test_case(
            "插屏广告关闭测试",
            "点击关闭按钮后，广告消失，返回应用主界面"
        )
    """
    try:
        logger.info(f"调用工具: create_test_case, 场景: {test_scenario}")
        
        prompt = f"""请生成一个详细的测试用例。

测试场景: {test_scenario}
{f'预期结果: {expected_result}' if expected_result else ''}

请包含:
1. 测试用例ID
2. 前置条件
3. 详细测试步骤（要具体到每个操作）
4. 预期结果
5. 测试数据（如果需要）
6. 注意事项

格式清晰，便于执行。
"""
        
        response = primary_model.invoke([HumanMessage(content=prompt)])
        test_case = response.content
        
        result = f"✅ 测试用例已生成:\n\n{test_case}"
        logger.info("工具 create_test_case 执行成功")
        return result
        
    except Exception as e:
        error_msg = f"工具 create_test_case 执行失败: {str(e)}"
        logger.error(error_msg)
        return f"❌ {error_msg}"


@tool
def validate_test_result(actual_result: str, expected_result: str) -> str:
    """
    验证测试结果是否符合预期
    
    参数:
        actual_result (str): 实际执行结果
        expected_result (str): 预期结果
    
    返回:
        验证结果：通过/失败，以及详细分析
    
    使用示例:
        validate_test_result(
            "点击关闭按钮后，广告窗口消失",
            "广告应该关闭并返回主界面"
        )
    """
    try:
        logger.info(f"调用工具: validate_test_result")
        
        prompt = f"""请验证测试结果是否符合预期。

预期结果:
{expected_result}

实际结果:
{actual_result}

请分析:
1. 是否通过（PASS/FAIL）
2. 如果失败，具体差异在哪里
3. 可能的原因
4. 建议的后续操作

请给出明确的结论。
"""
        
        response = primary_model.invoke([HumanMessage(content=prompt)])
        validation = response.content
        
        result = f"📊 验证结果:\n\n{validation}"
        logger.info("工具 validate_test_result 执行成功")
        return result
        
    except Exception as e:
        error_msg = f"工具 validate_test_result 执行失败: {str(e)}"
        logger.error(error_msg)
        return f"❌ {error_msg}"


@tool
def generate_test_report(test_summary: str) -> str:
    """
    生成测试报告
    
    参数:
        test_summary (str): 测试执行摘要，包括：
            - 测试的功能
            - 执行的测试用例
            - 测试结果
            - 发现的问题
    
    返回:
        格式化的测试报告
    
    使用示例:
        generate_test_report(
            "插屏广告测试完成，共执行3个用例，2个通过，1个失败"
        )
    """
    try:
        logger.info(f"调用工具: generate_test_report")
        
        prompt = f"""请生成一份专业的测试报告。

测试摘要:
{test_summary}

报告应包含:
1. 📋 测试概述
2. 📊 执行统计（通过率、失败率）
3. ✅ 通过的测试用例
4. ❌ 失败的测试用例
5. 🐛 发现的问题（如果有）
6. 💡 建议和结论

格式专业、清晰，使用适当的emoji增强可读性。
"""
        
        response = primary_model.invoke([HumanMessage(content=prompt)])
        report = response.content
        
        result = f"📄 测试报告已生成:\n\n{report}"
        logger.info("工具 generate_test_report 执行成功")
        return result
        
    except Exception as e:
        error_msg = f"工具 generate_test_report 执行失败: {str(e)}"
        logger.error(error_msg)
        return f"❌ {error_msg}"


@tool
def save_test_context(key: str, value: str) -> str:
    """
    保存测试上下文信息 - 记住重要的测试状态
    
    参数:
        key (str): 上下文键，例如：
            - "current_test_plan": 当前测试计划
            - "completed_cases": 已完成的测试用例
            - "current_step": 当前执行步骤
            - "test_target": 测试目标功能
        value (str): 对应的值
    
    返回:
        保存结果
    
    使用示例:
        # 记住测试计划
        save_test_context("test_plan", "插屏广告测试：包含3个测试用例")
        
        # 记住当前进度
        save_test_context("current_step", "正在执行第2个测试用例：关闭按钮测试")
        
        # 记住已完成的用例
        save_test_context("completed", "TC-AD-001(PASS), TC-AD-002(PASS)")
    """
    try:
        logger.info(f"保存测试上下文: {key}")
        test_memory.set_context(key, value)
        
        # 同时保存到状态管理器
        if key == "test_plan":
            test_state_manager.save_plan({"description": value})
        
        return f"✅ 已保存: {key} = {value}"
    except Exception as e:
        return f"❌ 保存失败: {str(e)}"


@tool
def get_test_context(key: str = None) -> str:
    """
    查询测试上下文信息 - 查看当前测试状态
    
    参数:
        key (str, optional): 要查询的键，None表示查询所有
    
    返回:
        查询结果
    
    使用示例:
        # 查询测试计划
        get_test_context("test_plan")
        
        # 查询当前进度
        get_test_context("current_step")
        
        # 查询所有上下文
        get_test_context()
    """
    try:
        if key:
            value = test_memory.get_context(key)
            if value:
                return f"📋 {key}: {value}"
            else:
                return f"⚠️ 未找到: {key}"
        else:
            # 返回所有上下文
            context = test_memory.context_vars
            if not context:
                return "📋 当前无测试上下文"
            
            result = "📋 当前测试上下文:\n"
            for k, v in context.items():
                result += f"  • {k}: {v}\n"
            return result
    except Exception as e:
        return f"❌ 查询失败: {str(e)}"


@tool
def get_test_progress() -> str:
    """
    获取当前测试进度摘要
    
    返回:
        包含以下信息的摘要：
        - 测试目标
        - 测试计划
        - 当前执行步骤
        - 已完成的测试
        - 下一步要做什么
    
    使用示例:
        # 在测试过程中查看进度
        get_test_progress()
        
        # 在测试开始前查看是否有未完成的测试
        get_test_progress()
    """
    try:
        logger.info("查询测试进度")
        
        context = test_memory.context_vars
        
        if not context:
            return "📋 当前无进行中的测试"
        
        # 构建进度报告
        progress = "📊 测试进度摘要\n"
        progress += "=" * 50 + "\n\n"
        
        # 测试目标
        if "test_target" in context:
            progress += f"🎯 测试目标: {context['test_target']}\n\n"
        
        # 测试计划
        if "test_plan" in context:
            progress += f"📋 测试计划:\n{context['test_plan']}\n\n"
        
        # 当前步骤
        if "current_step" in context:
            progress += f"▶️  当前步骤: {context['current_step']}\n\n"
        
        # 已完成的测试
        if "completed" in context:
            progress += f"✅ 已完成: {context['completed']}\n\n"
        
        # 失败的测试
        if "failed" in context:
            progress += f"❌ 失败: {context['failed']}\n\n"
        
        # 下一步
        if "next_step" in context:
            progress += f"⏭️  下一步: {context['next_step']}\n"
        
        progress += "\n" + "=" * 50
        
        return progress
    except Exception as e:
        return f"❌ 查询失败: {str(e)}"


@tool
def run_regression_test(previous_bugs: str) -> str:
    """
    执行回归测试 - 基于之前发现的bug进行验证
    
    参数:
        previous_bugs (str): 之前测试中发现的bug描述，例如：
            "1. 插屏广告关闭按钮有时无法点击\n2. 应用启动时间超过3秒\n3. 内存泄漏问题"
    
    返回:
        回归测试执行结果
    
    使用示例:
        run_regression_test("插屏广告关闭按钮有时无法点击\n应用启动时间超过3秒")
    """
    try:
        logger.info(f"调用工具: run_regression_test, 参数: {previous_bugs}")
        
        # 1. 创建回归测试计划
        planner = TestPlanner()
        test_plan = planner.create_test_plan(
            requirements="执行回归测试，验证之前发现的bug是否已修复",
            previous_bugs=previous_bugs
        )
        
        # 2. 执行回归测试
        orchestrator = WorkflowOrchestrator()
        workflow_result = orchestrator.execute_workflow(test_plan, is_regression=True)
        
        # 3. 生成回归测试报告
        result = f"🔄 回归测试执行完成\n"
        result += "=" * 50 + "\n"
        result += f"📋 测试计划: {test_plan.name}\n"
        result += f"📊 执行统计: {workflow_result.success_tasks}/{workflow_result.total_tasks} 通过\n"
        result += f"⏱️  总耗时: {workflow_result.total_duration:.2f}秒\n"
        result += f"📈 最终状态: {workflow_result.status.value}\n"
        
        # 4. 详细结果
        result += "\n📋 详细结果:\n"
        for phase_result in workflow_result.phase_results:
            result += f"\n{phase_result.phase.value}: {phase_result.success_count}/{phase_result.task_count} 通过"
            if phase_result.failed_count > 0:
                result += f" ({phase_result.failed_count} 失败)"
        
        # 5. 保存测试上下文
        save_test_context("regression_test_result", result)
        save_test_context("regression_bugs", previous_bugs)
        
        logger.info("工具 run_regression_test 执行成功")
        return result
        
    except Exception as e:
        error_msg = f"工具 run_regression_test 执行失败: {str(e)}"
        logger.error(error_msg)
        return f"❌ {error_msg}"


@tool  
def list_test_sessions() -> str:
    """
    列出所有历史测试会话
    
    返回:
        历史测试会话列表，包括会话ID、状态、任务数等
    
    使用示例:
        # 查看所有测试历史
        list_test_sessions()
    """
    try:
        logger.info("列出测试会话")
        sessions = test_state_manager.list_sessions()
        
        if not sessions:
            return "📚 暂无历史测试会话"
        
        result = "📚 历史测试会话:\n"
        result += "=" * 50 + "\n\n"
        
        for session in sessions[:10]:  # 只显示最近10个
            result += f"🆔 {session['id']}\n"
            result += f"   状态: {session['status']}\n"
            result += f"   开始时间: {session['start_time']}\n"
            result += f"   任务数: {session['tasks_count']}\n\n"
        
        return result
    except Exception as e:
        return f"❌ 查询失败: {str(e)}"


# 测试工程工具
test_engineering_tools = [
    create_test_plan,
    create_test_case,
    validate_test_result,
    generate_test_report,
    save_test_context,      # 新增：保存测试上下文
    get_test_context,       # 新增：查询测试上下文
    get_test_progress,      # 新增：获取测试进度
    list_test_sessions,     # 新增：列出历史会话
    run_regression_test     # 新增：执行回归测试
]

# 所有工具汇总
tools = device_tools + basic_operation_tools + app_management_tools + ui_element_tools + analysis_tools + performance_tools + advanced_performance_tools + knowledge_base_tools + test_engineering_tools

# ==================== 模型配置和工具绑定 ====================

def create_tool_node():
    """创建工具节点"""
    return ToolNode(tools)


def create_model_with_tools():
    """创建绑定工具的语言模型"""
    return primary_model.bind_tools(tools)


# ==================== 代理状态定义 ====================
class AgentState(TypedDict):
    """代理状态，包含对话消息"""
    messages: Annotated[List, add_messages]


# ==================== 系统指导 ====================
SYSTEM_PROMPT = """你是一个专业的 Android 测试工程师 AI 助手。

🎯 **核心职责**
你必须按照专业的测试流程工作。

📋 **标准测试流程（自动执行）**
当用户要求测试某个功能时，你必须按照以下步骤自动执行完整流程：

1️⃣ **制定测试计划** (使用 create_test_plan)
   - 理解测试需求
   - 规划测试阶段（冒烟测试、功能测试、性能测试）
   - 列出测试任务和优先级
   - 📝 **重要：使用 save_test_context 保存测试计划**

2️⃣ **编写测试用例** (使用 create_test_case)
   - 为每个测试任务编写详细用例
   - 包含：前置条件、测试步骤、预期结果
   - 确保用例可执行
   - 📝 **重要：使用 save_test_context 记录测试用例列表**

3️⃣ **执行测试** (使用设备操作工具)
   - 连接设备 (connect_devices)
   - 启动应用 (launch_app)
   - 执行测试步骤 (click_element, get_ui_elements, swipe_screen 等)
   - 📝 **重要：每完成一个用例，使用 save_test_context 更新进度**
   - 记录实际结果

4️⃣ **验证结果** (使用 validate_test_result)
   - 对比实际结果和预期结果
   - 判断测试是否通过
   - 分析失败原因
   - 📝 **重要：使用 save_test_context 记录通过/失败的用例**

5️⃣ **生成报告** (使用 generate_test_report)
   - 汇总测试结果
   - 统计通过率
   - 列出发现的问题
   - 给出建议

⚠️ **重要规则：首次测试不进行回归测试**
- 第一次测试时，只执行标准测试流程（冒烟测试、功能测试、性能测试、安全测试）
- 只有在用户明确要求进行回归测试时，才执行回归测试
- 回归测试专门用于验证之前发现的bug是否已修复

🔄 **回归测试流程（仅在用户明确要求时执行）**
当用户明确要求进行回归测试时，使用专门的回归测试工具：

1️⃣ **收集bug信息**
   - 询问用户之前测试中发现的bug详情
   - 确保bug描述清晰具体

2️⃣ **执行回归测试** (使用 run_regression_test)
   - 基于之前发现的bug创建专门的回归测试计划
   - 只执行冒烟测试和回归测试阶段
   - 重点验证已修复的bug是否重现

3️⃣ **生成回归测试报告**
   - 对比修复前后的测试结果
   - 确认bug是否已真正修复
   - 提供回归测试的通过率统计

 **记忆管理 - 非常重要！**
你有记忆系统来追踪测试进度，避免忘记测试到哪了：

- **save_test_context(key, value)**: 保存重要状态
  例如：
  • save_test_context("test_target", "插屏广告功能")
  • save_test_context("test_plan", "3个测试用例：加载、关闭、状态")
  • save_test_context("current_step", "正在执行TC-AD-002")
  • save_test_context("completed", "TC-AD-001(PASS)")

- **get_test_context(key)**: 查询保存的状态
  例如：
  • get_test_context("test_plan")  # 查看测试计划
  • get_test_context()  # 查看所有状态

- **get_test_progress()**: 查看整体进度
  在每个阶段结束时调用，确保不会忘记进度

 **知识库使用 - 遇到不熟悉的场景必须查询！**
当遇到以下情况时，必须先查询知识库：

1. **不熟悉的测试场景**
   • 插屏广告、横幅广告、激励视频
   • 登录功能、启动页、支付功能
   • 任何你不确定测试步骤的功能

2. **需要详细测试规范**
   • 测试前置条件
   • 详细测试步骤
   • 预期结果标准
   • 常见问题解决方案

3. **遇到问题需要帮助**
   • 广告加载失败怎么办
   • 元素找不到怎么处理
   • 性能指标如何判定

**使用方式：**
 search_knowledge_base("插屏广告测试规范")
 search_knowledge_base("登录功能测试方法")
 search_knowledge_base("广告关闭按钮找不到怎么办")

**正确流程：**
用户: "测试插屏广告"
1.  search_knowledge_base("插屏广告测试规范")  ← 先查知识库！
2. 基于知识库内容， create_test_plan(...)
3.  save_test_context("test_target", "插屏广告")
4. ... 自动继续后续步骤

 **关键规则**
- ❌ 不要直接开始点击操作
- ✅ 必须先规划、再编写用例、最后执行
- ✅ **每个关键步骤都要用 save_test_context 保存状态**
- ✅ 执行多个测试用例时，每完成一个就保存进度
- ✅ 如果不确定做到哪了，调用 get_test_progress 查看
- ✅ **自动执行完整流程，不要频繁询问用户确认**

💡 **示例对话（自动执行）**
用户: "测试插屏广告功能"

你的回应:
1. "我来帮你测试插屏广告功能。首先，让我制定测试计划..."
2. 🔧 create_test_plan("插屏广告功能测试")
3. 🔧 save_test_context("test_target", "插屏广告功能")
4. 🔧 save_test_context("test_plan", "冒烟测试、功能测试、性能测试")
5. 🔧 create_test_case(...)
6. 🔧 save_test_context("current_step", "执行TC-AD-001")
7. 自动执行测试...
8. 🔧 save_test_context("completed", "TC-AD-001(PASS)")
9. 自动继续下一个测试用例...
10. 最后生成测试报告

这样即使测试过程很长，你也不会忘记测试进度！

记住：你是测试工程师，不是操作员。专业性体现在系统化的测试流程和良好的进度追踪上。现在你应该自动执行完整流程，让用户只需等待报告生成。
"""

# ==================== 节点函数定义 ====================
def call_model(state: AgentState):
    """调用模型节点"""
    messages = state["messages"]
    
    # 如果是第一条消息，添加系统提示
    if len(messages) == 1 and isinstance(messages[0], HumanMessage):
        messages = [SystemMessage(content=SYSTEM_PROMPT)] + messages
    # 如果对话中没有系统消息，添加系统提示
    elif not any(isinstance(msg, SystemMessage) for msg in messages):
        messages = [SystemMessage(content=SYSTEM_PROMPT)] + messages
    
    model_with_tools = create_model_with_tools()
    response = model_with_tools.invoke(messages)
    return {"messages": [response]}


def should_continue(state: AgentState):
    """决定是否继续到工具节点"""
    messages = state["messages"]
    last_message = messages[-1]

    # 如果最后一条消息包含工具调用，则执行工具
    if last_message.tool_calls:
        return "tools"
    # 否则结束
    return END


# ==================== 代理图构建 ====================
def create_agent():
    """创建智能代理"""
    try:
        logger.info("开始创建智能代理")
        
        # 初始化检查点保存器（用于持久化对话状态）
        checkpointer = InMemorySaver()

        # 创建状态图
        workflow = StateGraph(AgentState)

        # 添加节点
        workflow.add_node("agent", call_model)
        workflow.add_node("tools", create_tool_node())

        # 设置入口点
        workflow.add_edge(START, "agent")

        # 添加条件边
        workflow.add_conditional_edges(
            "agent",
            should_continue,
            {
                "tools": "tools",
                END: END,
            },
        )

        # 工具执行后回到智能代理
        workflow.add_edge("tools", "agent")

        # 编译图
        compiled_agent = workflow.compile(
            checkpointer=checkpointer,
            debug=False,
        )
        logger.info("智能代理创建成功")
        return compiled_agent
        
    except Exception as e:
        logger.error(f"创建智能代理失败: {e}")
        raise


def run_agent_with_safety(agent, messages, thread_id="default", recursion_limit=1000):
    """
    安全运行agent，设置递归限制
    
    参数:
    - agent: 编译后的agent
    - messages: 消息列表或字符串
    - thread_id: 线程ID用于对话持久化
    - recursion_limit: 递归限制（默认1000，足够处理复杂任务）
    """
    # 如果messages是字符串，转换为消息列表
    if isinstance(messages, str):
        from langchain_core.messages import HumanMessage
        messages = [HumanMessage(content=messages)]
    
    # 配置 - 根据LangGraph文档，recursion_limit需要直接设置在config字典中
    config = {
        "configurable": {
            "thread_id": thread_id
        },
        "recursion_limit": recursion_limit  # 正确设置递归限制
    }
    
    logger.info(f"运行agent，递归限制: {recursion_limit}")
    
    # 调用agent（带重试机制）
    @api_call_with_retry
    def stream_agent():
        return list(agent.stream(
            {"messages": messages},
            config=config,  # 明确传递config参数
            stream_mode="values"
        ))
    
    # 使用重试机制
    try:
        for event in stream_agent():
            yield event
    except Exception as e:
        logger.error(f"Agent执行失败: {e}")
        # 检查是否是递归限制错误
        if "recursion limit" in str(e).lower():
            logger.warning(f"递归限制达到，当前限制: {recursion_limit}")
            # 返回提示信息
            yield {"messages": [AIMessage(content=f"⚠️ 任务执行达到递归限制({recursion_limit}步)，任务可能过于复杂。建议简化任务或分步执行。")]}
        else:
            # 返回错误消息
            yield {"messages": [AIMessage(content=f"❌ Agent执行失败: {str(e)}")]}


# ==================== 测试执行函数 ====================
def execute_complete_test_workflow(test_description: str):
    """
    执行完整的测试工作流，包括计划创建、执行和报告生成
    
    参数:
        test_description: 测试描述
    
    返回:
        测试执行结果和报告文件路径
    """
    try:
        logger.info(f"开始执行完整测试工作流: {test_description}")
        
        # 1. 创建测试计划
        print("📋 创建测试计划...")
        planner = TestPlanner()
        test_plan = planner.create_test_plan(test_description)
        logger.info(f"测试计划创建成功: {test_plan.id}")
        
        # 2. 执行工作流
        print("🚀 执行测试工作流...")
        orchestrator = WorkflowOrchestrator()
        workflow_result = orchestrator.execute_workflow(test_plan)
        logger.info(f"工作流执行完成: {workflow_result.status.value}")
        
        # 3. 生成报告
        print("📊 生成测试报告...")
        reporter = ReportGenerator()
        
        # 生成各种格式的报告
        html_report = reporter.generate_html_report(workflow_result, test_plan)
        md_report = reporter.generate_markdown_report(workflow_result, test_plan)
        json_report = reporter.generate_json_report(workflow_result)
        
        # 生成摘要
        summary = reporter.generate_summary(workflow_result)
        
        logger.info("测试报告生成完成")
        
        # 4. 返回结果
        result = {
            "plan_id": test_plan.id,
            "status": workflow_result.status.value,
            "total_tasks": workflow_result.total_tasks,
            "success_tasks": workflow_result.success_tasks,
            "failed_tasks": workflow_result.failed_tasks,
            "total_duration": workflow_result.total_duration,
            "reports": {
                "html": html_report,
                "markdown": md_report,
                "json": json_report
            },
            "summary": summary
        }
        
        return result
        
    except Exception as e:
        logger.error(f"完整测试工作流执行失败: {str(e)}")
        raise


# ==================== 主函数 ====================
def main():
    """主函数 - 运行预设测试场景"""
    print("🤖 Android自动化测试代理")
    print("=" * 30)

    # 创建代理
    agent = create_agent()

    # 预设测试场景
    test_scenarios = [
        {
            "name": "设备连接测试",
            "prompt": "请连接设备并启动 Appium 会话，然后告诉我连接状态和设备信息。"
        },
        {
            "name": "功能介绍测试", 
            "prompt": "你好，请介绍一下你的功能和可用操作"
        },
        {
            "name": "完整测试执行",
            "prompt": "请执行一个完整的测试流程，包括测试计划创建、测试执行和报告生成。测试功能：应用启动和基本导航。执行完成后请生成测试报告。"
        }
    ]

    for i, scenario in enumerate(test_scenarios, 1):
        print(f"\n🔍 测试场景 {i}: {scenario['name']}")
        print("-" * 40)

        # 如果是完整测试执行场景，直接调用报告生成函数
        if scenario['name'] == "完整测试执行":
            try:
                print("🚀 开始执行完整测试工作流...")
                result = execute_complete_test_workflow("应用启动和基本导航测试")
                
                # 精简输出，只显示关键信息
                print(f"✅ 测试完成 - 计划ID: {result['plan_id']}")
                print(f"   状态: {result['status']}, 任务: {result['success_tasks']}/{result['total_tasks']} 通过")
                print(f"   耗时: {result['total_duration']:.2f}秒")
                print(f"   报告: {result['reports']['html']}")
                
            except Exception as e:
                print(f"❌ 完整测试执行失败: {e}")
                logger.error(f"完整测试执行错误: {e}", exc_info=True)
        else:
            # 其他场景使用Agent对话方式
            config = {"configurable": {"thread_id": f"test-{i}"}}

            try:
                # 使用安全包装函数运行agent
                thread_id = config["configurable"]["thread_id"]
                
                for event in run_agent_with_safety(
                    agent=agent,
                    messages=scenario['prompt'],
                    thread_id=thread_id,
                    recursion_limit=1000  # 设置为1000步限制
                ):
                    # 输出最新的助手消息
                    if event["messages"]:
                        last_msg = event["messages"][-1]
                        if isinstance(last_msg, AIMessage):
                            if last_msg.content:  # 如果有内容就打印
                                print(f"🤖 助手: {last_msg.content}")
                            if last_msg.tool_calls:  # 如果有工具调用就打印
                                for tool_call in last_msg.tool_calls:
                                    print(f"🔧 调用工具: {tool_call['name']} - {tool_call['args']}")
                        elif hasattr(last_msg, 'content') and last_msg.content:
                            # 工具返回的消息
                            if "tool" in str(type(last_msg)):
                                print(f"🛠️  工具结果: {last_msg.content}")

            except Exception as e:
                print(f"❌ 测试场景 {i} 出错: {e}")
                logger.error(f"测试场景执行错误: {e}", exc_info=True)

        print("-" * 40)


# ==================== 交互式演示 ====================
def interactive_demo():
    """交互式演示 - 与代理进行对话"""
    print("\n🤖 Android自动化测试代理 - 交互模式")
    print("=" * 40)
    print("输入 'help' 查看详细功能说明")
    print("输入 'quit' 或 'exit' 退出程序")
    print("=" * 40)

    agent = create_agent()
    config = {"configurable": {"thread_id": "interactive-session"}}

    while True:
        user_input = input("\n👤 请输入指令: ").strip()

        # 处理特殊命令
        if user_input.lower() in ['quit', 'exit', '退出']:
            print("👋 感谢使用，再见!")
            break
        elif not user_input:
            print("⚠️  请输入有效指令")
            continue

        try:
            # 使用安全包装函数运行agent
            print("\n🔄 处理中...")
            thread_id = config["configurable"]["thread_id"]
            
            for event in run_agent_with_safety(
                agent=agent,
                messages=user_input,
                thread_id=thread_id,
                recursion_limit=1000  # 设置为1000步限制
            ):
                if event["messages"]:
                    last_msg = event["messages"][-1]
                    if isinstance(last_msg, AIMessage) and last_msg.content:
                        print(f"\n🤖 助手: {last_msg.content}")

        except Exception as e:
            print(f"❌ 处理指令时出错: {e}")
            logger.error(f"Agent执行错误: {e}", exc_info=True)
    


# ==================== 程序入口 ====================
if __name__ == "__main__":
    # 运行预设测试
    main()

    # 询问是否要进行交互式演示
    choice = input("\n是否进入交互式演示模式? (y/n): ").lower().strip()
    if choice.startswith('y'):
        interactive_demo()
    else:
        print("👋 程序结束，感谢使用!")
