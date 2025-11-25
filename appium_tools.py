from appium import webdriver
from appium.options.common import AppiumOptions
from appium.webdriver.common.appiumby import AppiumBy
import subprocess
import time
import xml.etree.ElementTree as ET
from adb_tools import DeviceInfoCollector
def driver_init(device_info):
    # 检查必要的设备信息是否存在
    required_fields = ["platformName", "platformVersion", "deviceName", "appPackage", "appActivity", "deviceId"]
    for field in required_fields:
        if field not in device_info or device_info[field] is None:
            print(f"错误: 设备信息缺少 {field} 或其值为 None")
            return None

    """初始化并返回Appium WebDriver，基于设备信息"""
    capabilities_config = {
        "platformName": device_info["platformName"],
        "appium:platformVersion": device_info["platformVersion"],
        "appium:deviceName": device_info["deviceId"],
        "appium:appPackage": device_info["appPackage"],
        "appium:appActivity": device_info["appActivity"],
        "appium:noReset": True,
        "appium:fullReset": False,
        "appium:autoGrantPermissions": True,
        "appium:skipUnlock": True,
        "appium:automationName": "UiAutomator2",
        "appium:grantAllPermissions": True,
        "appium:allowTestPackages": True,
        "appium:enableNotificationListener": True,
        "appium:autoLaunch": True,
        "appium:appWaitActivity": f"{device_info['appActivity']}*",
        "appium:ignoreHiddenApiPolicyError": True,
        "appium:newCommandTimeout": 600,
        "appium:adbExecTimeout": 120000,
        "appium:uiautomator2ServerLaunchTimeout": 60000,
        "appium:ensureWebviewsHavePages": True,
        "appium:autoWebview": False,
        "appium:disableAndroidWatchers": True,
        "appium:nativeWebScreenshot": True,
        "appium:connectHardwareKeyboard": True
    }

    # 使用AppiumOptions
    options = AppiumOptions()
    for key, value in capabilities_config.items():
        options.set_capability(key, value)

    # 创建WebDriver实例
    try:
        driver = webdriver.Remote(
            command_executor="http://127.0.0.1:4723",
            options=options
        )
    except Exception as e:
        print(f"创建WebDriver实例时出错: {e}")
        return None

    # 验证应用是否真正启动成功
    try:
        time.sleep(3)
        current_activity = driver.current_activity
        print(f"应用启动成功，当前Activity: {current_activity}")
        page_source_length = len(driver.page_source)
        print(f"页面内容长度: {page_source_length} 字符")
        if page_source_length < 100:
            print("警告: 页面内容可能未完全加载，等待额外时间...")
            time.sleep(5)
    except Exception as e:
        print(f"应用启动验证过程中出现警告: {e}")

    return driver


def driver_quit(driver, device_id):
    """增强的驱动关闭函数，确保应用完全关闭"""
    app_package = "com.bluex.sdk.demo"

    try:
        driver.quit()
        print("Appium 驱动已关闭")
    except Exception as e:
        print(f"关闭 Appium 驱动时出现警告: {e}")

    try:
        subprocess.run(['adb', '-s', device_id, 'shell', 'am', 'force-stop', app_package], check=True, timeout=10)
        print(f"应用 {app_package} 已强制停止")
        # ... 其他清理命令 ...
    except Exception as e:
        print(f"强制关闭应用时出现未知错误: {e}")


class AppiumUITools:
    """Appium UI元素操作工具类"""
    
    _driver = None
    _device_info = None
    
    @classmethod
    def set_device_info(cls, device_info):
        """设置设备信息，用于初始化Appium驱动"""
        cls._device_info = device_info
        cls._driver = None  # 重置驱动，下次获取时会重新初始化
    
    @classmethod
    def _get_driver(cls):
        """获取Appium驱动实例"""
        if cls._driver is None:
            try:
                # 使用已设置的设备信息初始化驱动
                if cls._device_info:
                    cls._driver = driver_init(cls._device_info)
                else:
                    # 如果没有设备信息，尝试使用ADB收集
                    collector = DeviceInfoCollector()
                    device_info = collector.collect_info()
                    if device_info:
                        cls._driver = driver_init(device_info)
            except Exception as e:
                print(f"初始化Appium驱动失败: {e}")
        return cls._driver
    
    def get_ui_elements(self) -> str:
        """
        获取当前屏幕上的UI元素信息（使用Appium）
        返回格式化的UI元素信息字符串
        """
        try:
            # 获取Appium驱动实例
            driver = self._get_driver()
            if driver is None:
                return "无法获取Appium驱动实例，请先连接设备"
            
            # 获取页面源码（XML格式）
            page_source = driver.page_source
            
            # 解析XML获取UI元素
            try:
                root = ET.fromstring(page_source)
                elements = []
                
                def parse_element(element, depth=0):
                    """递归解析XML元素"""
                    # 获取元素属性
                    attrib = element.attrib
                    
                    # 过滤掉一些系统元素
                    if attrib.get('package', '').startswith('com.android.systemui'):
                        return
                    
                    # 提取有用信息
                    element_info = {
                        'class': attrib.get('class', ''),
                        'text': attrib.get('text', ''),
                        'resource-id': attrib.get('resource-id', ''),
                        'content-desc': attrib.get('content-desc', ''),
                        'bounds': attrib.get('bounds', ''),
                        'clickable': attrib.get('clickable', 'false'),
                        'enabled': attrib.get('enabled', 'false'),
                        'focusable': attrib.get('focusable', 'false'),
                        'depth': depth
                    }
                    
                    # 计算中心坐标
                    bounds = element_info['bounds']
                    if bounds:
                        try:
                            # 处理bounds格式，如"[0,0][1080,2400]"
                            bounds = bounds.replace('[', '').replace(']', '')
                            coords = bounds.split('][')
                            if len(coords) == 2:
                                left_top = coords[0].split(',')
                                right_bottom = coords[1].split(',')
                                if len(left_top) == 2 and len(right_bottom) == 2:
                                    x1, y1 = int(left_top[0]), int(left_top[1])
                                    x2, y2 = int(right_bottom[0]), int(right_bottom[1])
                                    center_x = (x1 + x2) // 2
                                    center_y = (y1 + y2) // 2
                                    element_info['center'] = f"({center_x}, {center_y})"
                                else:
                                    element_info['center'] = "(N/A)"
                            else:
                                element_info['center'] = "(N/A)"
                        except Exception as e:
                            element_info['center'] = f"(解析错误: {str(e)})"
                    
                    # 只保留有意义的元素（有文本、可点击、有ID等）
                    if (element_info['text'] or 
                        element_info['resource-id'] or 
                        element_info['content-desc'] or 
                        element_info['clickable'] == 'true'):
                        elements.append(element_info)
                    
                    # 递归处理子元素
                    for child in element:
                        parse_element(child, depth + 1)
                
                parse_element(root)
                
                # 格式化输出
                if elements:
                    result = f"找到 {len(elements)} 个UI元素:\n\n"
                    for i, elem in enumerate(elements, 1):
                        result += f"元素ID: #{i}\n"
                        result += f"  类名: {elem['class']}\n"
                        if elem['text']:
                            result += f"  文本: {elem['text']}\n"
                        if elem['resource-id']:
                            result += f"  ID: {elem['resource-id']}\n"
                        if elem['content-desc']:
                            result += f"  描述: {elem['content-desc']}\n"
                        if elem['center']:
                            result += f"  中心坐标: {elem['center']}\n"
                        result += f"  可点击: {elem['clickable']}, 启用: {elem['enabled']}, 可聚焦: {elem['focusable']}\n"
                        result += "-" * 40 + "\n"
                    return result
                else:
                    return "未找到有效的UI元素"
                    
            except Exception as e:
                return f"解析UI元素时出错: {str(e)}"
                
        except Exception as e:
            return f"获取UI元素时出错: {str(e)}"
    
    def find_element_by_text(self, text: str) -> str:
        """
        根据文本内容查找UI元素（使用Appium）
        参数:
        - text: 要查找的文本内容
        """
        try:
            # 获取Appium驱动实例
            driver = self._get_driver()
            if driver is None:
                return "无法获取Appium驱动实例，请先连接设备"
            
            # 使用Appium查找包含指定文本的元素
            elements = driver.find_elements(AppiumBy.XPATH, f"//*[contains(@text, '{text}')]")
            
            if not elements:
                return f"未找到包含文本 '{text}' 的元素"
            
            result = f"找到 {len(elements)} 个匹配文本 '{text}' 的元素:\n\n"
            
            for i, element in enumerate(elements, 1):
                # 获取元素属性
                element_text = element.get_attribute("text") or "(无文本)"
                content_desc = element.get_attribute("content-desc") or "(无描述)"
                resource_id = element.get_attribute("resource-id") or "(无ID)"
                classname = element.get_attribute("class") or "(无类名)"
                
                # 获取元素位置
                location = element.location
                size = element.size
                center_x = location['x'] + size['width'] // 2
                center_y = location['y'] + size['height'] // 2
                
                result += f"元素ID: #{i}\n"
                result += f"  文本: {element_text}\n"
                result += f"  描述: {content_desc}\n"
                result += f"  ID: {resource_id}\n"
                result += f"  类名: {classname}\n"
                result += f"  坐标: ({center_x}, {center_y})\n"
                result += "-" * 40 + "\n"
            
            return result
                
        except Exception as e:
            return f"查找元素时出错: {str(e)}"
    
    def find_element_by_class(self, class_name: str) -> str:
        """
        根据类名查找UI元素（使用Appium）
        参数:
        - class_name: 要查找的类名
        """
        try:
            # 获取Appium驱动实例
            driver = self._get_driver()
            if driver is None:
                return "无法获取Appium驱动实例，请先连接设备"
            
            # 使用Appium查找指定类名的元素
            elements = driver.find_elements(AppiumBy.CLASS_NAME, class_name)
            
            if not elements:
                return f"未找到类名为 '{class_name}' 的元素"
            
            result = f"找到 {len(elements)} 个匹配类名 '{class_name}' 的元素:\n\n"
            
            for i, element in enumerate(elements, 1):
                # 获取元素属性
                element_text = element.get_attribute("text") or "(无文本)"
                content_desc = element.get_attribute("content-desc") or "(无描述)"
                resource_id = element.get_attribute("resource-id") or "(无ID)"
                
                # 获取元素位置
                location = element.location
                size = element.size
                center_x = location['x'] + size['width'] // 2
                center_y = location['y'] + size['height'] // 2
                
                result += f"元素ID: #{i}\n"
                result += f"  类名: {class_name}\n"
                result += f"  文本: {element_text}\n"
                result += f"  描述: {content_desc}\n"
                result += f"  ID: {resource_id}\n"
                result += f"  坐标: ({center_x}, {center_y})\n"
                result += "-" * 40 + "\n"
            
            return result
                
        except Exception as e:
            return f"查找元素时出错: {str(e)}"

    def get_ui_elements_with_filters(self, filters: dict = None, device_id: str = None) -> str:
        """
        获取界面元素信息（支持过滤）
        
        Args:
            filters (dict, optional): 过滤条件
                - text: 按文本过滤，如 {"text": "登录"}
                - class_name: 按类名过滤，如 {"class_name": "android.widget.Button"}
                - resource_id: 按ID过滤，如 {"resource_id": "com.app:id/btn"}
                - None: 返回所有元素
            device_id: 设备ID（可选）
        
        Returns:
            匹配的元素列表
        """
        try:
            # 获取Appium驱动实例
            driver = self._get_driver()
            if driver is None:
                return "无法获取Appium驱动实例，请先连接设备"
            
            # 获取页面源码（XML格式）
            page_source = driver.page_source
            
            # 解析XML获取UI元素
            try:
                root = ET.fromstring(page_source)
                elements = []
                
                def parse_element(element, depth=0):
                    """递归解析XML元素"""
                    # 获取元素属性
                    attrib = element.attrib
                    
                    # 过滤掉一些系统元素
                    if attrib.get('package', '').startswith('com.android.systemui'):
                        return
                    
                    # 提取有用信息
                    element_info = {
                        'class': attrib.get('class', ''),
                        'text': attrib.get('text', ''),
                        'resource-id': attrib.get('resource-id', ''),
                        'content-desc': attrib.get('content-desc', ''),
                        'bounds': attrib.get('bounds', ''),
                        'clickable': attrib.get('clickable', 'false'),
                        'enabled': attrib.get('enabled', 'false'),
                        'focusable': attrib.get('focusable', 'false'),
                        'depth': depth
                    }
                    
                    # 计算中心坐标
                    bounds = element_info['bounds']
                    if bounds:
                        try:
                            # 处理bounds格式，如"[0,0][1080,2400]"
                            bounds = bounds.replace('[', '').replace(']', '')
                            coords = bounds.split('][')
                            if len(coords) == 2:
                                left_top = coords[0].split(',')
                                right_bottom = coords[1].split(',')
                                if len(left_top) == 2 and len(right_bottom) == 2:
                                    x1, y1 = int(left_top[0]), int(left_top[1])
                                    x2, y2 = int(right_bottom[0]), int(right_bottom[1])
                                    center_x = (x1 + x2) // 2
                                    center_y = (y1 + y2) // 2
                                    element_info['center'] = f"({center_x}, {center_y})"
                                else:
                                    element_info['center'] = "(N/A)"
                            else:
                                element_info['center'] = "(N/A)"
                        except Exception as e:
                            element_info['center'] = f"(解析错误: {str(e)})"
                    
                    # 应用过滤条件
                    matches_filter = True
                    if filters:
                        if 'text' in filters and filters['text'] not in element_info['text']:
                            matches_filter = False
                        if 'class_name' in filters and filters['class_name'] not in element_info['class']:
                            matches_filter = False
                        if 'resource_id' in filters and filters['resource_id'] not in element_info['resource-id']:
                            matches_filter = False
                    
                    # 只保留有意义的元素（有文本、可点击、有ID等）并且匹配过滤条件
                    if matches_filter and (element_info['text'] or 
                        element_info['resource-id'] or 
                        element_info['content-desc'] or 
                        element_info['clickable'] == 'true'):
                        elements.append(element_info)
                    
                    # 递归处理子元素
                    for child in element:
                        parse_element(child, depth + 1)
                
                parse_element(root)
                
                # 格式化输出
                if elements:
                    filter_info = f"过滤条件: {filters}" if filters else "无过滤条件"
                    result = f"找到 {len(elements)} 个UI元素 ({filter_info}):\n\n"
                    for i, elem in enumerate(elements, 1):
                        result += f"元素ID: #{i}\n"
                        result += f"  类名: {elem['class']}\n"
                        if elem['text']:
                            result += f"  文本: {elem['text']}\n"
                        if elem['resource-id']:
                            result += f"  ID: {elem['resource-id']}\n"
                        if elem['content-desc']:
                            result += f"  描述: {elem['content-desc']}\n"
                        if elem['center']:
                            result += f"  中心坐标: {elem['center']}\n"
                        result += f"  可点击: {elem['clickable']}, 启用: {elem['enabled']}, 可聚焦: {elem['focusable']}\n"
                        result += "-" * 40 + "\n"
                    return result
                else:
                    filter_info = f"过滤条件: {filters}" if filters else ""
                    return f"未找到有效的UI元素 {filter_info}"
                    
            except Exception as e:
                return f"解析UI元素时出错: {str(e)}"
                
        except Exception as e:
            return f"获取UI元素时出错: {str(e)}"

    def click_element(self, element_identifier: str, by: str = "text") -> str:
        """
        点击指定的UI元素
        
        Args:
            element_identifier: 元素标识符（文本、类名或resource-id）
            by: 查找方式，可选值："text", "class", "id"
        """
        try:
            # 获取Appium驱动实例
            driver = self._get_driver()
            if driver is None:
                return "无法获取Appium驱动实例，请先连接设备"
            
            # 根据查找方式定位元素
            if by == "text":
                elements = driver.find_elements(AppiumBy.XPATH, f"//*[contains(@text, '{element_identifier}')]")
            elif by == "class":
                elements = driver.find_elements(AppiumBy.CLASS_NAME, element_identifier)
            elif by == "id":
                elements = driver.find_elements(AppiumBy.ID, element_identifier)
            else:
                return f"不支持的查找方式: {by}，请使用 'text', 'class' 或 'id'"
            
            if not elements:
                return f"未找到匹配的元素: {element_identifier} (方式: {by})"
            
            # 点击第一个匹配的元素
            element = elements[0]
            element.click()
            
            # 获取元素信息用于确认
            element_text = element.get_attribute("text") or "(无文本)"
            content_desc = element.get_attribute("content-desc") or "(无描述)"
            resource_id = element.get_attribute("resource-id") or "(无ID)"
            classname = element.get_attribute("class") or "(无类名)"
            
            return f"✅ 成功点击元素:\n" \
                   f"   文本: {element_text}\n" \
                   f"   描述: {content_desc}\n" \
                   f"   ID: {resource_id}\n" \
                   f"   类名: {classname}\n" \
                   f"   查找方式: {by}"
                    
        except Exception as e:
            return f"点击元素时出错: {str(e)}"

    def press_key(self, key_name: str, device_id: str = None) -> str:
        """
        按下设备按键
        
        Args:
            key_name: 按键名称，支持："back"（返回键）、"home"（主页键）、"menu"（菜单键）、"power"（电源键）、"volume_up"（音量+）、"volume_down"（音量-）
            device_id: 设备ID（可选）
        """
        try:
            # 获取Appium驱动实例
            driver = self._get_driver()
            if driver is None:
                return "无法获取Appium驱动实例，请先连接设备"
            
            # 映射按键名称到Android整数按键码
            # 参考: https://developer.android.com/reference/android/view/KeyEvent
            key_mapping = {
                "back": 4,
                "home": 3,
                "menu": 82,
                "power": 26,
                "volume_up": 24,
                "volume_down": 25
            }
            
            if key_name not in key_mapping:
                return f"不支持的按键名称: {key_name}，请使用: {', '.join(key_mapping.keys())}"
            
            # 使用Appium的按键功能 (整数keycode)
            key_code = key_mapping[key_name]
            driver.press_keycode(key_code)
            
            return f"✅ 成功按下 {key_name} 键"
                    
        except Exception as e:
            return f"按下按键时出错: {str(e)}"

    def get_element_info(self, element_identifier: str, by: str = "text") -> dict:
        """
        获取特定元素的详细信息
        
        Args:
            element_identifier: 元素标识符（文本、类名或resource-id）
            by: 查找方式，可选值："text", "class", "id"
            
        Returns:
            元素详细信息字典
        """
        try:
            driver = self._get_driver()
            if driver is None:
                return {"error": "无法获取Appium驱动实例，请先连接设备"}
            
            if by == "text":
                elements = driver.find_elements(AppiumBy.XPATH, f"//*[@text='{element_identifier}']")
            elif by == "class":
                elements = driver.find_elements(AppiumBy.CLASS_NAME, element_identifier)
            elif by == "id":
                elements = driver.find_elements(AppiumBy.ID, element_identifier)
            else:
                return {"error": f"不支持的查找方式: {by}"}
            
            if not elements:
                return {"error": f"未找到元素: {element_identifier} (方式: {by})"}
            
            element = elements[0]
            location = element.location
            size = element.size
            
            # 获取元素的更多属性
            element_info = {
                "identifier": element_identifier,
                "type": by,
                "x": location['x'],
                "y": location['y'],
                "width": size['width'],
                "height": size['height'],
                "center_x": location['x'] + size['width'] / 2,
                "center_y": location['y'] + size['height'] / 2,
                "enabled": element.is_enabled(),
                "displayed": element.is_displayed(),
                "selected": element.is_selected()
            }
            
            # 尝试获取更多属性
            try:
                element_info["text"] = element.text
            except:
                element_info["text"] = ""
                
            try:
                element_info["resource_id"] = element.get_attribute("resource-id")
            except:
                element_info["resource_id"] = ""
                
            try:
                element_info["class"] = element.get_attribute("class")
            except:
                element_info["class"] = ""
            
            return element_info
            
        except Exception as e:
            return {"error": f"获取元素信息失败: {str(e)}"}


if __name__ == "__main__":
    try:
        print("开始执行主程序...")
        collector = DeviceInfoCollector()
        device_info = collector.collect_info()

        if not device_info:
            print("警告: 没有收集到设备信息")
            exit(1)

        print("收集到的设备信息:")
        for key, value in device_info.items():
            print(f"{key}: {value}")

        print("开始初始化驱动...")
        start_time = time.time()
        timeout = 60  # 设置超时时间为60秒
        driver = None

        while time.time() - start_time < timeout:
            driver = driver_init(device_info)
            if driver:
                break
            print("驱动初始化失败，5秒后重试...")
            time.sleep(5)

        if driver:
            try:
                print("驱动初始化成功，开始执行 Appium 测试")
                print("当前活动页面:", driver.current_activity)
                time.sleep(5)
            except Exception as e:
                print(f"执行测试时出现错误: {e}")
            finally:
                driver_quit(driver, device_info["deviceId"])
        else:
            print(f"无法在 {timeout} 秒内初始化驱动，请检查 Appium 服务器和设备连接")
    except Exception as e:
        print(f"主程序执行过程中出现未捕获的异常: {e}")

