import json
import subprocess
import os
import xml.etree.ElementTree as ET
import re
import base64
import time
from typing import Optional,List,Dict
from PIL import Image, ImageDraw


class AdbUITools:
    """
    ADB UI工具类 - 提供UI元素获取和操作功能
    使用uiautomator dump命令获取UI元素信息
    """


    @staticmethod
    def tap_element(element_id: str) -> str:
        """
        点击指定ID的UI元素。
        参数:
        - element_id: 要点击的元素ID，必须是analyze_current_screen返回的元素ID
        """
        try:
            # 先生成并拉取最新的UI层次结构
            ui_path = "window_dump.xml"
            try:
                subprocess.run(
                    ['adb', 'shell', 'uiautomator', 'dump', '/sdcard/window_dump.xml'],
                    capture_output=True, text=True, check=True
                )
                subprocess.run(
                    ['adb', 'pull', '/sdcard/window_dump.xml', ui_path],
                    capture_output=True, check=True
                )
            except Exception as _:
                return "无法获取当前界面结构，请确认ADB连接正常"

            tree = ET.parse(ui_path)
            root = tree.getroot()

            # 解析元素ID
            try:
                element_num = int(element_id.replace("#", ""))
            except ValueError:
                return "无效的元素ID，请提供有效的数字ID"

            # 重新遍历找到对应ID的元素
            elements = []
            id_counter = 1
            target_bounds = None

            for elem in root.findall(".//*"):
                text = elem.get("text", "")
                content_desc = elem.get("content-desc", "")
                resource_id = elem.get("resource-id", "")
                classname = elem.get("class", "").split(".")[-1]

                if (not text and not content_desc and not resource_id) or classname in ["FrameLayout", "LinearLayout"]:
                    id_counter += 1
                    continue

                if id_counter == element_num:
                    bounds = elem.get("bounds", "")
                    match = re.match(r'\[(\d+),(\d+)\]\[(\d+),(\d+)\]', bounds)
                    if match:
                        left, top, right, bottom = map(int, match.groups())
                        center_x = (left + right) // 2
                        center_y = (top + bottom) // 2
                        target_bounds = (center_x, center_y)
                    break

                id_counter += 1

            if target_bounds:
                # 执行点击操作
                x, y = target_bounds
                subprocess.run(["adb", "shell", f"input tap {x} {y}"], check=True)
                return f"成功点击元素 #{element_num} 在坐标 ({x}, {y})"
            else:
                return f"未找到ID为 #{element_num} 的元素"

        except Exception as e:
            return f"点击元素时出错: {str(e)}"
        finally:
            try:
                if os.path.exists(ui_path):
                    os.remove(ui_path)
            except Exception:
                pass

    @staticmethod
    def input_text(text: str) -> str:
        """
        在当前焦点（如文本框）输入文本
        参数:
        - text: 要输入的文本内容
        """
        try:
            # 替换特殊字符
            escaped_text = text.replace(" ", "%s").replace("'", "\\'").replace("\"", "\\\"")

            # 执行文本输入
            subprocess.run(["adb", "shell", f"input text {escaped_text}"], check=True)
            return f"成功输入文本: {text}"
        except Exception as e:
            return f"输入文本时出错: {str(e)}"

    @staticmethod
    def swipe_screen(direction: str) -> str:
        """
        在屏幕上滑动。
        参数:
        - direction: 滑动方向，可选 'up', 'down', 'left', 'right'
        """
        try:
            # 获取屏幕尺寸
            size_output = subprocess.check_output(["adb", "shell", "wm", "size"]).decode()
            match = re.search(r'Physical size: (\d+)x(\d+)', size_output)
            if not match:
                return "无法获取屏幕尺寸"

            width, height = map(int, match.groups())

            # 设置滑动参数
            start_x, start_y, end_x, end_y = 0, 0, 0, 0

            if direction.lower() == 'up':
                start_x = width // 2
                start_y = height * 2 // 3
                end_x = width // 2
                end_y = height // 3
            elif direction.lower() == 'down':
                start_x = width // 2
                start_y = height // 3
                end_x = width // 2
                end_y = height * 2 // 3
            elif direction.lower() == 'left':
                start_x = width * 2 // 3
                start_y = height // 2
                end_x = width // 3
                end_y = height // 2
            elif direction.lower() == 'right':
                start_x = width // 3
                start_y = height // 2
                end_x = width * 2 // 3
                end_y = height // 2
            else:
                return f"无效的方向: {direction}。请使用 'up', 'down', 'left', 或 'right'"

            # 执行滑动
            subprocess.run(["adb", "shell", f"input swipe {start_x} {start_y} {end_x} {end_y} 300"], check=True)
            return f"成功向{direction}方向滑动屏幕"

        except Exception as e:
            return f"滑动屏幕时出错: {str(e)}"

    @staticmethod
    def press_back() -> str:
        """按下返回键"""
        try:
            subprocess.run(["adb", "shell", "input", "keyevent", "4"], check=True)
            return "已按下返回键"
        except Exception as e:
            return f"按返回键时出错: {str(e)}"

    @staticmethod
    def press_home() -> str:
        """按下Home键"""
        try:
            subprocess.run(["adb", "shell", "input", "keyevent", "3"], check=True)
            return "已按下Home键"
        except Exception as e:
            return f"按Home键时出错: {str(e)}"

    @staticmethod
    def launch_app(package_name: str) -> str:
        """
        启动指定的应用程序
        参数:
        - package_name: 应用包名，如 com.example.app
        """
        try:
            # 尝试获取应用的主Activity
            output = subprocess.check_output(
                ["adb", "shell", f"cmd package resolve-activity --brief {package_name}"],
                text=True
            )

            if "/" in output:
                activity = output.strip().split("/")[1].split(" ")[0]
                full_activity = f"{package_name}/{activity}"
                subprocess.run(["adb", "shell", f"am start -n {full_activity}"], check=True)
                return f"已启动应用: {package_name}"
            else:
                # 尝试直接启动应用
                subprocess.run(["adb", "shell", f"monkey -p {package_name} -c android.intent.category.LAUNCHER 1"],
                               check=True)
                return f"已启动应用: {package_name}"
        except Exception as e:
            return f"启动应用时出错: {str(e)}"

    @staticmethod
    def list_installed_apps() -> str:
        """列出设备上已安装的应用"""
        try:
            output = subprocess.check_output(
                ["adb", "shell", "pm", "list", "packages", "-3"],
                text=True
            )
            apps = output.strip().split("\n")
            # 格式化输出
            result = "已安装的第三方应用:\n\n"
            for app in apps:
                if app.startswith("package:"):
                    result += f"- {app[8:]}\n"
            return result
        except Exception as e:
            return f"获取应用列表时出错: {str(e)}"

    @staticmethod
    def get_ui_elements() -> List[Dict[str, str]]:
        """获取当前页面的UI元素信息（使用uiautomator dump）"""
        try:
            # 使用uiautomator dump获取UI层次结构
            result = subprocess.run(
                ['adb', 'shell', 'uiautomator', 'dump', '/sdcard/window_dump.xml'],
                capture_output=True, text=True
            )
            
            if result.returncode != 0:
                print(f"uiautomator dump失败: {result.stderr}")
                return []
            
            # 拉取XML文件到本地
            subprocess.run(['adb', 'pull', '/sdcard/window_dump.xml', 'window_dump.xml'], 
                         capture_output=True)
            
            # 解析XML文件
            tree = ET.parse('window_dump.xml')
            root = tree.getroot()
            
            elements = []
            for elem in root.iter():
                element_info = {
                    'class': elem.get('class', ''),
                    'text': elem.get('text', ''),
                    'resource-id': elem.get('resource-id', ''),
                    'content-desc': elem.get('content-desc', ''),
                    'bounds': elem.get('bounds', ''),
                    'clickable': elem.get('clickable', ''),
                    'enabled': elem.get('enabled', ''),
                    'focusable': elem.get('focusable', ''),
                    'focused': elem.get('focused', ''),
                    'scrollable': elem.get('scrollable', ''),
                    'long-clickable': elem.get('long-clickable', ''),
                    'password': elem.get('password', ''),
                    'selected': elem.get('selected', ''),
                    'checkable': elem.get('checkable', ''),
                    'checked': elem.get('checked', '')
                }
                elements.append(element_info)
            
            # 清理临时文件
            import os
            if os.path.exists('window_dump.xml'):
                os.remove('window_dump.xml')
            
            return elements
        except Exception as e:
            print(f"获取UI元素失败: {e}")
            return []

    @staticmethod
    def find_element_by_text(text: str) -> str:
        """
        根据文本内容查找UI元素（使用uiautomator）
        参数:
        - text: 要查找的文本内容
        """
        try:
            # 使用uiautomator dump获取UI层次结构
            result = subprocess.run(
                ['adb', 'shell', 'uiautomator', 'dump', '/sdcard/window_dump.xml'],
                capture_output=True, text=True
            )
            
            if result.returncode != 0:
                return f"uiautomator dump失败: {result.stderr}"
            
            # 拉取XML文件到本地
            subprocess.run(['adb', 'pull', '/sdcard/window_dump.xml', 'window_dump.xml'], 
                         capture_output=True)
            
            # 解析XML文件
            tree = ET.parse('window_dump.xml')
            root = tree.getroot()
            
            # 查找包含指定文本的元素
            elements_found = []
            id_counter = 1
            
            for elem in root.iter():
                elem_text = elem.get('text', '')
                if text in elem_text:
                    content_desc = elem.get('content-desc', '')
                    resource_id = elem.get('resource-id', '')
                    classname = elem.get('class', '').split('.')[-1]
                    bounds = elem.get('bounds', '')
                    
                    # 解析坐标
                    match = re.match(r'\[(\d+),(\d+)\]\[(\d+),(\d+)\]', bounds)
                    if match:
                        left, top, right, bottom = map(int, match.groups())
                        center_x = (left + right) // 2
                        center_y = (top + bottom) // 2
                    else:
                        center_x, center_y = 0, 0
                    
                    elements_found.append({
                        'id': id_counter,
                        'text': elem_text,
                        'content_desc': content_desc,
                        'resource_id': resource_id,
                        'classname': classname,
                        'bounds': bounds,
                        'center_x': center_x,
                        'center_y': center_y
                    })
                    id_counter += 1
            
            # 清理临时文件
            import os
            if os.path.exists('window_dump.xml'):
                os.remove('window_dump.xml')
            
            if not elements_found:
                return f"未找到包含文本 '{text}' 的元素"
            
            result = f"找到 {len(elements_found)} 个匹配文本 '{text}' 的元素:\n\n"
            
            for element in elements_found:
                result += f"元素ID: #{element['id']}\n"
                result += f"  文本: {element['text'] or '(无文本)'}\n"
                result += f"  描述: {element['content_desc'] or '(无描述)'}\n"
                result += f"  ID: {element['resource_id'] or '(无ID)'}\n"
                result += f"  类名: {element['classname'] or '(无类名)'}\n"
                result += f"  坐标: ({element['center_x']}, {element['center_y']})\n"
                result += "-" * 40 + "\n"
            
            return result
                
        except Exception as e:
            return f"查找元素时出错: {str(e)}"

    @staticmethod
    def find_element_by_class(class_name: str) -> Optional[Dict[str, str]]:
        """通过类名查找元素（使用uiautomator）"""
        try:
            # 使用uiautomator查找指定类名的元素
            result = subprocess.run(
                ['adb', 'shell', 'uiautomator', 'dump', '/sdcard/window_dump.xml'],
                capture_output=True, text=True
            )
            
            if result.returncode != 0:
                return None
            
            # 拉取XML文件到本地
            subprocess.run(['adb', 'pull', '/sdcard/window_dump.xml', 'window_dump.xml'], 
                         capture_output=True)
            
            # 解析XML文件
            tree = ET.parse('window_dump.xml')
            root = tree.getroot()
            
            # 查找指定类名的元素
            for elem in root.iter():
                elem_class = elem.get('class', '')
                if class_name in elem_class:
                    return {
                        'text': elem.get('text', ''),
                        'resource-id': elem.get('resource-id', ''),
                        'class': elem_class,
                        'bounds': elem.get('bounds', '')
                    }
            
            # 清理临时文件
            import os
            if os.path.exists('window_dump.xml'):
                os.remove('window_dump.xml')
                
        except Exception as e:
            print(f"查找元素失败: {e}")
        
        return None

    @staticmethod
    def get_element_info(element_id: str) -> str:
        """
        获取指定元素的详细信息
        参数:
        - element_id: 元素ID（格式如：#1, #2等）
        """
        try:
            elements = AdbUITools.get_ui_elements()
            if not elements:
                return "未找到有效的UI元素"

            try:
                index = int(element_id.replace('#', '')) - 1
            except Exception:
                return "无效的元素ID，请使用如 #1 的格式"

            if index < 0 or index >= len(elements):
                return f"未找到ID为 {element_id} 的元素"

            elem = elements[index]

            center_line = ""
            b = elem.get('bounds', '')
            m = re.match(r'\[(\d+),(\d+)\]\[(\d+),(\d+)\]', b)
            if m:
                x1, y1, x2, y2 = map(int, m.groups())
                center_line = f"坐标: ({(x1+x2)//2}, {(y1+y2)//2})\n"

            result = f"元素 {element_id} 的详细信息:\n\n"
            result += f"元素ID: {element_id}\n"
            result += f"文本: {elem.get('text', '') or 'N/A'}\n"
            result += f"描述: {elem.get('content-desc', '') or 'N/A'}\n"
            result += f"资源ID: {elem.get('resource-id', '') or 'N/A'}\n"
            result += f"类名: {elem.get('class', '') or 'N/A'}\n"
            if center_line:
                result += center_line
            return result
                
        except Exception as e:
            return f"获取元素信息时出错: {str(e)}"


class DeviceInfoCollector:
    def __init__(self):
        self.devices = []

    def execute_adb_command(self, command, device_id=None):
        try:
            if device_id:
                result = subprocess.check_output(f"adb -s {device_id} {command}", shell=True).decode('utf-8').strip()
            else:
                result = subprocess.check_output(f"adb {command}", shell=True).decode('utf-8').strip()
            return result
        except subprocess.CalledProcessError as e:
            print(f"执行ADB命令失败: {command}")
            print(f"错误信息: {e}")
            return None

    def get_connected_devices(self):
        try:
            result = subprocess.check_output(['adb', 'devices'], text=True)
            lines = result.strip().split('\n')[1:]
            return [line.split('\t')[0] for line in lines if line.endswith('device')]
        except subprocess.CalledProcessError:
            print("无法获取连接的设备")
            return []

    def get_android_version(self, device_id):
        try:
            result = subprocess.check_output(['adb', '-s', device_id, 'shell', 'getprop', 'ro.build.version.release'],
                                             text=True)
            return result.strip()
        except subprocess.CalledProcessError:
            print(f"无法获取设备 {device_id} 的 Android 版本")
            return "未知"

    def get_device_model(self, device_id):
        try:
            result = subprocess.check_output(['adb', '-s', device_id, 'shell', 'getprop', 'ro.product.model'],
                                             text=True)
            return result.strip()
        except subprocess.CalledProcessError:
            print(f"无法获取设备 {device_id} 的型号")
            return "未知"

    def get_app_package(self, device_id):
        try:
            result = subprocess.check_output(['adb', '-s', device_id, 'shell', 'pm', 'list', 'packages'], text=True)
            packages = [line.split(':',1)[1] for line in result.strip().split('\n') if line.startswith('package:')]
            # 优先匹配 bluex，如无则返回第一个第三方包
            for p in packages:
                if 'bluex' in p:
                    return p
            if packages:
                return packages[0]
        except subprocess.CalledProcessError:
            print(f"无法获取设备 {device_id} 的应用包名")
        return None

    def collect_info(self):
        print("开始收集设备信息...")
        try:
            # 获取连接的设备ID
            result = subprocess.check_output(['adb', 'devices'], text=True)
            lines = result.strip().split('\n')[1:]
            if not lines:
                print("未找到连接的设备")
                return None
            
            device_id = lines[0].split('\t')[0]
            print(f"设备ID: {device_id}")
            
            # 获取设备信息
            android_version = subprocess.check_output(
                ['adb', '-s', device_id, 'shell', 'getprop', 'ro.build.version.release'], text=True).strip()
            device_name = subprocess.check_output(
                ['adb', '-s', device_id, 'shell', 'getprop', 'ro.product.model'], text=True).strip()
            
            print(f"Android版本: {android_version}")
            print(f"设备型号: {device_name}")
            
            # 智能检测应用包名和Activity
            app_package, app_activity = self._detect_app_activity(device_id)
            
            print(f"检测到的 app_package: {app_package}")
            print(f"检测到的 app_activity: {app_activity}")
            
            device_info = {
                'deviceId': device_id,
                'platformName': 'Android',
                'platformVersion': android_version,
                'deviceName': device_name,
                'appPackage': app_package,
                'appActivity': app_activity
            }
            print("成功收集到设备信息")
            return device_info
        except Exception as e:
            print(f"收集设备信息时出错: {e}")
            return None
    
    def _detect_app_activity(self, device_id):
        """智能检测应用包名和Activity - 优先获取当前前台应用"""
        
        # 方法1：从dumpsys activity获取当前前台应用（最准确）
        try:
            result = subprocess.check_output(
                ['adb', '-s', device_id, 'shell', 'dumpsys', 'activity', 'activities'],
                text=True, stderr=subprocess.DEVNULL
            )
            
            # 查找 mResumedActivity 或 mFocusedActivity
            patterns = [
                r'mResumedActivity:\s*ActivityRecord\{[^ ]+ [^ ]+ ([^/\s]+)/([^ \}]+)',
                r'mFocusedActivity:\s*ActivityRecord\{[^ ]+ [^ ]+ ([^/\s]+)/([^ \}]+)',
            ]
            
            for pattern in patterns:
                match = re.search(pattern, result)
                if match:
                    app_package = match.group(1)
                    app_activity = match.group(2)
                    print(f"✅ 从dumpsys activity检测到前台应用: {app_package}/{app_activity}")
                    return app_package, app_activity
        except Exception as e:
            print(f"⚠️ 从dumpsys activity获取失败: {e}")
        
        # 方法2：从dumpsys window获取当前焦点窗口
        try:
            result = subprocess.check_output(
                ['adb', '-s', device_id, 'shell', 'dumpsys', 'window'],
                text=True, stderr=subprocess.DEVNULL
            )
            
            # 查找 mCurrentFocus
            patterns = [
                r'mCurrentFocus=Window\{[^ ]+ [^ ]+ ([^/\s]+)/([^/\s\}]+)\}',
                r'mFocusedWindow=Window\{[^ ]+ [^ ]+ ([^/\s]+)/([^/\s\}]+)\}',
            ]
            
            for pattern in patterns:
                match = re.search(pattern, result)
                if match:
                    app_package = match.group(1)
                    app_activity = match.group(2)
                    print(f"✅ 从dumpsys window检测到焦点窗口: {app_package}/{app_activity}")
                    return app_package, app_activity
        except Exception as e:
            print(f"⚠️ 从dumpsys window获取失败: {e}")
        
        # 方法3：使用dumpsys activity top获取顶层Activity
        try:
            result = subprocess.check_output(
                ['adb', '-s', device_id, 'shell', 'dumpsys', 'activity', 'top'],
                text=True, stderr=subprocess.DEVNULL
            )
            
            # 查找 ACTIVITY 行
            lines = result.split('\n')
            for line in lines:
                if 'ACTIVITY' in line and not 'pid=' not in line:
                    match = re.search(r'ACTIVITY\s+([^/\s]+)/([^\s]+)', line)
                    if match:
                        app_package = match.group(1)
                        app_activity = match.group(2)
                        print(f"✅ 从dumpsys activity top检测到: {app_package}/{app_activity}")
                        return app_package, app_activity
        except Exception as e:
            print(f"⚠️ 从dumpsys activity top获取失败: {e}")
        
        # 方法4：使用adb shell am stack list查看Activity栈
        try:
            result = subprocess.check_output(
                ['adb', '-s', device_id, 'shell', 'am', 'stack', 'list'],
                text=True, stderr=subprocess.DEVNULL
            )
            
            # 查找顶层Activity
            match = re.search(r'topActivity=ComponentInfo\{([^/\s]+)/([^\}]+)\}', result)
            if match:
                app_package = match.group(1)
                app_activity = match.group(2)
                print(f"✅ 从am stack list检测到: {app_package}/{app_activity}")
                return app_package, app_activity
        except Exception as e:
            print(f"⚠️ 从am stack list获取失败: {e}")
        
        # 如果所有方法都失败，返回默认值
        print("⚠️ 无法检测当前前台应用，使用默认值")
        default_package = "com.bluex.sdk.demo"
        default_activity = ".ui.MainActivity"
        return default_package, default_activity
    
    def _get_main_activity(self, device_id, package_name):
        """获取应用的主Activity"""
        try:
            # 使用dumpsys package命令获取Activity信息
            result = subprocess.check_output(
                ['adb', '-s', device_id, 'shell', 'dumpsys', 'package', package_name], text=True)
            
            # 查找主Activity
            for line in result.split('\n'):
                if 'android.intent.action.MAIN' in line and 'android.intent.category.LAUNCHER' in line:
                    # 提取Activity名称
                    match = re.search(r'([^/\s]+/[^\s]+)', line)
                    if match:
                        full_activity = match.group(1)
                        if '/' in full_activity:
                            return full_activity.split('/')[1]
        except Exception as e:
            print(f"获取应用 {package_name} 的主Activity失败: {e}")
        
        return None
    
    def _verify_activity_exists(self, device_id, package_name, activity_name):
        """验证Activity是否存在"""
        try:
            # 使用am start命令测试Activity是否存在
            test_cmd = f"am start -n {package_name}/{activity_name} -W"
            result = subprocess.check_output(
                ['adb', '-s', device_id, 'shell', test_cmd], 
                stderr=subprocess.STDOUT, 
                text=True
            )
            
            # 检查是否成功启动或Activity存在
            if "Error" not in result and "does not exist" not in result:
                # 立即停止测试启动的应用
                subprocess.run(['adb', '-s', device_id, 'shell', 'am', 'force-stop', package_name], 
                              capture_output=True)
                return True
        except subprocess.CalledProcessError:
            # 启动失败，Activity可能不存在
            pass
        except Exception as e:
            print(f"验证Activity {package_name}/{activity_name} 失败: {e}")
        
        return False


    def get_device_info(self):
        try:
            # 获取连接的设备ID
            device_id = subprocess.check_output(['adb', 'devices']).decode().strip().split('\n')[1].split('\t')[0]
            # 获取设备信息
            android_version = subprocess.check_output(
                ['adb', '-s', device_id, 'shell', 'getprop', 'ro.build.version.release']).decode().strip()
            device_name = subprocess.check_output(
                ['adb', '-s', device_id, 'shell', 'getprop', 'ro.product.model']).decode().strip()
            
            # 使用智能检测应用包名和Activity
            app_package, app_activity = self._detect_app_activity(device_id)
            
            return {
                'deviceId': device_id,
                'platformName': 'Android',
                'platformVersion': android_version,
                'deviceName': device_name,
                'appPackage': app_package,
                'appActivity': app_activity
            }
        except Exception as e:
            print(f"获取设备信息时出错: {e}")
            return None

    # 新增的实用ADB命令功能
    def install_app(self, apk_path, device_id=None):
        return self.execute_adb_command(f"install {apk_path}", device_id)

    def uninstall_app(self, package_name, device_id=None):
        return self.execute_adb_command(f"uninstall {package_name}", device_id)

    def clear_app_data(self, package_name, device_id=None):
        return self.execute_adb_command(f"shell pm clear {package_name}", device_id)

    def take_screenshot(self, output_path, device_id=None):
        self.execute_adb_command(f"shell screencap -p /sdcard/screenshot.png", device_id)
        self.execute_adb_command(f"pull /sdcard/screenshot.png {output_path}", device_id)
        self.execute_adb_command(f"shell rm /sdcard/screenshot.png", device_id)
        return f"Screenshot saved to {output_path}"

    def get_battery_info(self, device_id=None):
        battery_info = self.execute_adb_command("shell dumpsys battery", device_id)
        level = re.search(r'level: (\d+)', battery_info)
        status = re.search(r'status: (\d+)', battery_info)
        return {
            "level": int(level.group(1)) if level else None,
            "status": int(status.group(1)) if status else None
        }

    def get_device_logs(self, output_path, device_id=None):
        self.execute_adb_command(f"logcat -d > {output_path}", device_id)
        return f"Logs saved to {output_path}"

    def reboot_device(self, device_id=None):
        return self.execute_adb_command("reboot", device_id)


class PerformanceMonitor:
    """
    性能监测工具类 - 提供设备性能监测功能
    包括CPU、内存、电池、网络等性能指标监测
    """

    @staticmethod
    def get_cpu_usage(device_id: str = None) -> str:
        """
        获取设备CPU使用率
        参数:
        - device_id: 设备ID（可选）
        """
        try:
            cmd = "shell top -n 1"
            if device_id:
                cmd = f"-s {device_id} {cmd}"
            
            result = subprocess.check_output(f"adb {cmd}", shell=True, text=True)
            
            # 解析CPU使用率
            lines = result.strip().split('\n')
            for line in lines:
                if 'CPU:' in line:
                    # 提取CPU使用率百分比
                    cpu_match = re.search(r'CPU:\s*(\d+)%', line)
                    if cpu_match:
                        cpu_usage = cpu_match.group(1)
                        return f"当前CPU使用率: {cpu_usage}%"
            
            return "无法获取CPU使用率信息"
            
        except Exception as e:
            return f"获取CPU使用率失败: {str(e)}"

    @staticmethod
    def get_memory_usage(device_id: str = None) -> str:
        """
        获取设备内存使用情况
        参数:
        - device_id: 设备ID（可选）
        """
        try:
            cmd = "shell dumpsys meminfo"
            if device_id:
                cmd = f"-s {device_id} {cmd}"
            
            result = subprocess.check_output(f"adb {cmd}", shell=True, text=True)
            
            # 解析内存信息
            lines = result.strip().split('\n')
            memory_info = []
            
            for line in lines:
                if 'Total RAM:' in line:
                    memory_info.append(line.strip())
                elif 'Free RAM:' in line:
                    memory_info.append(line.strip())
                elif 'Used RAM:' in line:
                    memory_info.append(line.strip())
                elif 'Lost RAM:' in line:
                    memory_info.append(line.strip())
            
            if memory_info:
                return "内存使用情况:\n" + "\n".join(memory_info)
            else:
                return "无法获取内存使用信息"
                
        except Exception as e:
            return f"获取内存使用情况失败: {str(e)}"

    @staticmethod
    def get_battery_status(device_id: str = None) -> str:
        """
        获取设备电池状态
        参数:
        - device_id: 设备ID（可选）
        """
        try:
            cmd = "shell dumpsys battery"
            if device_id:
                cmd = f"-s {device_id} {cmd}"
            
            result = subprocess.check_output(f"adb {cmd}", shell=True, text=True)
            
            # 解析电池信息
            battery_info = []
            lines = result.strip().split('\n')
            
            for line in lines:
                if 'level:' in line:
                    battery_info.append(f"电池电量: {line.split(':')[1].strip()}%")
                elif 'status:' in line:
                    status = line.split(':')[1].strip()
                    status_map = {
                        '1': '未知',
                        '2': '充电中',
                        '3': '放电中',
                        '4': '未充电',
                        '5': '充满'
                    }
                    battery_info.append(f"电池状态: {status_map.get(status, '未知')}")
                elif 'temperature:' in line:
                    temp = int(line.split(':')[1].strip())
                    battery_info.append(f"电池温度: {temp/10}°C")
            
            if battery_info:
                return "电池状态:\n" + "\n".join(battery_info)
            else:
                return "无法获取电池状态信息"
                
        except Exception as e:
            return f"获取电池状态失败: {str(e)}"

    @staticmethod
    def get_network_status(device_id: str = None) -> str:
        """
        获取设备网络状态
        参数:
        - device_id: 设备ID（可选）
        """
        try:
            cmd = "shell netstat"
            if device_id:
                cmd = f"-s {device_id} {cmd}"
            
            result = subprocess.check_output(f"adb {cmd}", shell=True, text=True)
            
            # 统计网络连接数
            lines = result.strip().split('\n')
            tcp_connections = 0
            udp_connections = 0
            
            for line in lines:
                if 'tcp' in line.lower():
                    tcp_connections += 1
                elif 'udp' in line.lower():
                    udp_connections += 1
            
            return f"网络连接状态:\nTCP连接数: {tcp_connections}\nUDP连接数: {udp_connections}"
            
        except Exception as e:
            return f"获取网络状态失败: {str(e)}"

    @staticmethod
    def get_storage_info(device_id: str = None) -> str:
        """
        获取设备存储信息
        参数:
        - device_id: 设备ID（可选）
        """
        try:
            cmd = "shell df"
            if device_id:
                cmd = f"-s {device_id} {cmd}"
            
            result = subprocess.check_output(f"adb {cmd}", shell=True, text=True)
            
            # 解析存储信息
            lines = result.strip().split('\n')
            storage_info = []
            
            for line in lines:
                if '/sdcard' in line or '/storage' in line:
                    parts = line.split()
                    if len(parts) >= 5:
                        mount_point = parts[-1]
                        total = parts[1]
                        used = parts[2]
                        available = parts[3]
                        usage_percent = parts[4]
                        
                        storage_info.append(f"{mount_point}: 总空间 {total}, 已用 {used}, 可用 {available}, 使用率 {usage_percent}")
            
            if storage_info:
                return "存储信息:\n" + "\n".join(storage_info)
            else:
                return "无法获取存储信息"
                
        except Exception as e:
            return f"获取存储信息失败: {str(e)}"

    @staticmethod
    def get_running_processes(device_id: str = None) -> str:
        """
        获取设备运行进程信息
        参数:
        - device_id: 设备ID（可选）
        """
        try:
            cmd = "shell ps"
            if device_id:
                cmd = f"-s {device_id} {cmd}"
            
            result = subprocess.check_output(f"adb {cmd}", shell=True, text=True)
            
            # 统计进程数量
            lines = result.strip().split('\n')
            process_count = len(lines) - 1  # 减去标题行
            
            # 获取前5个CPU使用率最高的进程
            top_cmd = "shell top -n 1 -o %CPU"
            if device_id:
                top_cmd = f"-s {device_id} {top_cmd}"
            
            top_result = subprocess.check_output(f"adb {top_cmd}", shell=True, text=True)
            top_lines = top_result.strip().split('\n')
            
            top_processes = []
            for i, line in enumerate(top_lines[1:6]):  # 跳过标题行，取前5个
                parts = line.split()
                if len(parts) >= 9:
                    pid = parts[0]
                    cpu = parts[2]
                    name = parts[8]
                    top_processes.append(f"{i+1}. PID: {pid}, CPU: {cpu}%, 进程: {name}")
            
            result_text = f"运行进程总数: {process_count}\n\nCPU使用率最高的5个进程:\n"
            result_text += "\n".join(top_processes)
            
            return result_text
            
        except Exception as e:
            return f"获取进程信息失败: {str(e)}"

    @staticmethod
    def get_comprehensive_performance(device_id: str = None) -> str:
        """
        获取设备综合性能报告
        参数:
        - device_id: 设备ID（可选）
        """
        try:
            performance_report = []
            performance_report.append("=== 设备性能综合报告 ===\n")
            
            # CPU使用率
            cpu_info = PerformanceMonitor.get_cpu_usage(device_id)
            performance_report.append(cpu_info)
            
            # 内存使用情况
            memory_info = PerformanceMonitor.get_memory_usage(device_id)
            performance_report.append(memory_info)
            
            # 电池状态
            battery_info = PerformanceMonitor.get_battery_status(device_id)
            performance_report.append(battery_info)
            
            # 网络状态
            network_info = PerformanceMonitor.get_network_status(device_id)
            performance_report.append(network_info)
            
            # 存储信息
            storage_info = PerformanceMonitor.get_storage_info(device_id)
            performance_report.append(storage_info)
            
            # 进程信息
            process_info = PerformanceMonitor.get_running_processes(device_id)
            performance_report.append(process_info)
            
            return "\n\n".join(performance_report)
            
        except Exception as e:
            return f"生成综合性能报告失败: {str(e)}"

    @staticmethod
    def monitor_performance_continuous(device_id: str = None, duration: int = 60, interval: int = 5) -> str:
        """
        持续监测设备性能
        参数:
        - device_id: 设备ID（可选）
        - duration: 监测持续时间（秒）
        - interval: 监测间隔（秒）
        """
        try:
            import time
            
            if duration <= 0 or interval <= 0:
                return "监测参数无效，请确保duration和interval大于0"
            
            iterations = duration // interval
            performance_log = []
            
            performance_log.append(f"开始持续性能监测 - 持续时间: {duration}秒, 间隔: {interval}秒\n")
            
            for i in range(iterations):
                current_time = time.strftime("%Y-%m-%d %H:%M:%S")
                performance_log.append(f"\n=== 第{i+1}次监测 - {current_time} ===")
                
                # 获取CPU使用率
                cpu_info = PerformanceMonitor.get_cpu_usage(device_id)
                performance_log.append(cpu_info)
                
                # 获取内存使用情况
                memory_info = PerformanceMonitor.get_memory_usage(device_id)
                performance_log.append(memory_info)
                
                # 等待间隔时间
                time.sleep(interval)
            
            performance_log.append(f"\n=== 监测完成，共监测{iterations}次 ===")
            
            return "\n".join(performance_log)
            
        except Exception as e:
            return f"持续性能监测失败: {str(e)}"


class AdvancedPerformanceMonitor:
    """
    高级性能监测类 - 提供核心性能指标监测功能
    包括内存监控、CPU使用率、帧率、网络流量、启动时间、应用日志等
    """

    @staticmethod
    def get_memory_info(package_name: str, device_id: str = None) -> dict:
        """
        获取应用内存详细信息
        参数:
        - package_name: 应用包名
        - device_id: 设备ID（可选）
        返回: 结构化内存数据
        """
        try:
            cmd = f"shell dumpsys meminfo {package_name}"
            if device_id:
                cmd = f"-s {device_id} {cmd}"
            
            result = subprocess.check_output(f"adb {cmd}", shell=True, text=True)
            
            # 解析内存信息
            memory_data = {
                "success": True,
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                "package_name": package_name,
                "metrics": {
                    "memory": {
                        "java_heap_mb": 0,
                        "native_heap_mb": 0,
                        "graphics_mb": 0,
                        "total_pss_mb": 0,
                        "trend": "stable"
                    }
                },
                "anomalies": []
            }
            
            lines = result.strip().split('\n')
            for line in lines:
                if 'Java Heap:' in line:
                    # 提取Java堆内存
                    match = re.search(r'Java Heap:\s*(\d+)', line)
                    if match:
                        memory_data["metrics"]["memory"]["java_heap_mb"] = int(match.group(1)) / 1024
                elif 'Native Heap:' in line:
                    # 提取Native堆内存
                    match = re.search(r'Native Heap:\s*(\d+)', line)
                    if match:
                        memory_data["metrics"]["memory"]["native_heap_mb"] = int(match.group(1)) / 1024
                elif 'Graphics:' in line:
                    # 提取Graphics内存
                    match = re.search(r'Graphics:\s*(\d+)', line)
                    if match:
                        memory_data["metrics"]["memory"]["graphics_mb"] = int(match.group(1)) / 1024
                elif 'TOTAL PSS:' in line:
                    # 提取Total PSS
                    match = re.search(r'TOTAL PSS:\s*(\d+)', line)
                    if match:
                        memory_data["metrics"]["memory"]["total_pss_mb"] = int(match.group(1)) / 1024
            
            # 检测内存泄漏风险
            if memory_data["metrics"]["memory"]["total_pss_mb"] > 200:  # 超过200MB视为高风险
                memory_data["anomalies"].append({
                    "type": "memory_leak"
                })

            return memory_data

        except Exception as e:
            return {
                "success": False,
                "error": f"获取内存信息失败: {str(e)}",
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
            }
    @staticmethod
    def get_cpu_usage_by_package(package_name: str, device_id: str = None) -> dict:
        """
        获取指定应用的CPU使用率
        参数:
        - package_name: 应用包名
        - device_id: 设备ID（可选）
        返回: 结构化CPU数据
        """
        try:
            cmd = "shell top -n 1"
            if device_id:
                cmd = f"-s {device_id} {cmd}"
            
            result = subprocess.check_output(f"adb {cmd}", shell=True, text=True)
            
            cpu_data = {
                "success": True,
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                "package_name": package_name,
                "metrics": {
                    "cpu": {
                        "usage_percent": 0,
                        "status": "normal"
                    }
                },
                "anomalies": []
            }
            
            lines = result.strip().split('\n')
            for line in lines:
                if package_name in line:
                    # 解析进程CPU使用率
                    parts = line.split()
                    if len(parts) >= 9:
                        cpu_usage = float(parts[2])
                        cpu_data["metrics"]["cpu"]["usage_percent"] = cpu_usage
                        
                        # 判断CPU状态
                        if cpu_usage > 80:
                            cpu_data["metrics"]["cpu"]["status"] = "critical"
                            cpu_data["anomalies"].append({
                                "type": "high_cpu_usage",
                                "severity": "critical",
                                "description": f"CPU使用率过高: {cpu_usage}%"
                            })
                        elif cpu_usage > 50:
                            cpu_data["metrics"]["cpu"]["status"] = "high"
                            cpu_data["anomalies"].append({
                                "type": "high_cpu_usage",
                                "severity": "warning",
                                "description": f"CPU使用率较高: {cpu_usage}%"
                            })
                        break
            
            return cpu_data
            
        except Exception as e:
            return {
                "success": False,
                "error": f"获取CPU使用率失败: {str(e)}",
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
            }

    @staticmethod
    def get_fps_info(package_name: str, device_id: str = None) -> dict:
        """
        获取应用帧率信息
        参数:
        - package_name: 应用包名
        - device_id: 设备ID（可选）
        返回: 结构化FPS数据
        """
        try:
            cmd = f"shell dumpsys gfxinfo {package_name} framestats"
            if device_id:
                cmd = f"-s {device_id} {cmd}"
            
            result = subprocess.check_output(f"adb {cmd}", shell=True, text=True)
            
            fps_data = {
                "success": True,
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                "package_name": package_name,
                "metrics": {
                    "fps": {
                        "average": 60,
                        "jank_count": 0,
                        "status": "smooth"
                    }
                },
                "anomalies": []
            }
            
            # 解析帧率信息（简化实现）
            lines = result.strip().split('\n')
            frame_times = []
            
            for line in lines:
                if 'FrameTime' in line:
                    # 提取帧渲染时间
                    match = re.findall(r'\d+\.?\d*', line)
                    if match:
                        frame_times.extend([float(t) for t in match])
            
            if frame_times:
                # 计算平均FPS
                avg_frame_time = sum(frame_times) / len(frame_times)
                avg_fps = 1000 / avg_frame_time if avg_frame_time > 0 else 60
                fps_data["metrics"]["fps"]["average"] = min(avg_fps, 60)
                
                # 计算掉帧情况
                jank_count = sum(1 for t in frame_times if t > 16.67)  # 超过16.67ms视为掉帧
                fps_data["metrics"]["fps"]["jank_count"] = jank_count
                
                # 判断帧率状态
                if avg_fps < 30:
                    fps_data["metrics"]["fps"]["status"] = "frozen"
                    fps_data["anomalies"].append({
                        "type": "low_fps",
                        "severity": "critical",
                        "description": f"帧率过低: {avg_fps:.1f}FPS"
                    })
                elif avg_fps < 45:
                    fps_data["metrics"]["fps"]["status"] = "laggy"
                    fps_data["anomalies"].append({
                        "type": "low_fps",
                        "severity": "warning",
                        "description": f"帧率较低: {avg_fps:.1f}FPS"
                    })
            
            return fps_data
            
        except Exception as e:
            return {
                "success": False,
                "error": f"获取帧率信息失败: {str(e)}",
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
            }

    @staticmethod
    def get_battery_info(package_name: str, device_id: str = None) -> dict:
        """
        获取应用电池信息
        参数:
        - package_name: 应用包名
        - device_id: 设备ID（可选）
        返回: 结构化电池数据
        """
        try:
            cmd = "shell dumpsys battery"
            if device_id:
                cmd = f"-s {device_id} {cmd}"
            
            result = subprocess.check_output(f"adb {cmd}", shell=True, text=True)
            
            battery_data = {
                "success": True,
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                "package_name": package_name,
                "metrics": {
                    "battery": {
                        "level": 85,
                        "temperature": 35,
                        "status": "normal"
                    }
                },
                "anomalies": []
            }
            
            # 解析电池信息
            lines = result.strip().split('\n')
            for line in lines:
                if 'level:' in line:
                    match = re.search(r'level:\s*(\d+)', line)
                    if match:
                        battery_data["metrics"]["battery"]["level"] = int(match.group(1))
                elif 'temperature:' in line:
                    match = re.search(r'temperature:\s*(\d+)', line)
                    if match:
                        battery_data["metrics"]["battery"]["temperature"] = int(match.group(1)) / 10
                elif 'status:' in line:
                    match = re.search(r'status:\s*(\d+)', line)
                    if match:
                        status_code = int(match.group(1))
                        status_map = {
                            1: "未知",
                            2: "充电中",
                            3: "放电中",
                            4: "未充电",
                            5: "充满"
                        }
                        battery_data["metrics"]["battery"]["status"] = status_map.get(status_code, "未知")
            
            # 检测电池异常
            if battery_data["metrics"]["battery"]["level"] < 20:
                battery_data["anomalies"].append({
                    "type": "low_battery",
                    "severity": "warning",
                    "description": f"电池电量低: {battery_data['metrics']['battery']['level']}%"
                })
            
            if battery_data["metrics"]["battery"]["temperature"] > 40:
                battery_data["anomalies"].append({
                    "type": "high_temperature",
                    "severity": "critical",
                    "description": f"电池温度过高: {battery_data['metrics']['battery']['temperature']}°C"
                })
            
            return battery_data
            
        except Exception as e:
            return {
                "success": False,
                "error": f"获取电池信息失败: {str(e)}",
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
            }

    @staticmethod
    def get_network_traffic(package_name: str, device_id: str = None) -> dict:
        """
        获取应用网络流量信息
        参数:
        - package_name: 应用包名
        - device_id: 设备ID（可选）
        返回: 结构化网络数据
        """
        try:
            # 获取网络统计信息
            cmd = "shell cat /proc/net/xt_qtaguid/stats"
            if device_id:
                cmd = f"-s {device_id} {cmd}"
            
            result = subprocess.check_output(f"adb {cmd}", shell=True, text=True)
            
            network_data = {
                "success": True,
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                "package_name": package_name,
                "metrics": {
                    "network": {
                        "wifi_kb": 0,
                        "mobile_kb": 0,
                        "total_kb": 0
                    }
                },
                "anomalies": []
            }
            
            # 解析网络流量（简化实现）
            lines = result.strip().split('\n')
            total_rx = 0
            total_tx = 0
            
            for line in lines:
                if package_name in line:
                    parts = line.split()
                    if len(parts) >= 8:
                        rx_bytes = int(parts[5])
                        tx_bytes = int(parts[7])
                        total_rx += rx_bytes
                        total_tx += tx_bytes
            
            total_kb = (total_rx + total_tx) / 1024
            network_data["metrics"]["network"]["total_kb"] = total_kb
            
            # 判断流量是否异常
            if total_kb > 5000:  # 超过5MB视为异常
                network_data["anomalies"].append({
                    "type": "high_network_usage",
                    "severity": "warning",
                    "description": f"网络流量较高: {total_kb:.1f}KB"
                })
            
            return network_data
            
        except Exception as e:
            return {
                "success": False,
                "error": f"获取网络流量失败: {str(e)}",
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
            }

    @staticmethod
    def get_app_startup_time(package_name: str, activity_name: str = None, device_id: str = None) -> dict:
        """
        获取应用启动时间
        参数:
        - package_name: 应用包名
        - activity_name: Activity名称（可选）
        - device_id: 设备ID（可选）
        返回: 结构化启动时间数据
        """
        try:
            if not activity_name:
                # 尝试获取主Activity
                cmd = f"shell cmd package resolve-activity --brief {package_name}"
                if device_id:
                    cmd = f"-s {device_id} {cmd}"
                
                result = subprocess.check_output(f"adb {cmd}", shell=True, text=True)
                if '/' in result:
                    activity_name = result.strip().split('/')[1].split(' ')[0]
                else:
                    activity_name = ".MainActivity"  # 默认Activity
            
            full_activity = f"{package_name}/{activity_name}"
            cmd = f"shell am start -W {full_activity}"
            if device_id:
                cmd = f"-s {device_id} {cmd}"
            
            result = subprocess.check_output(f"adb {cmd}", shell=True, text=True)
            
            startup_data = {
                "success": True,
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                "package_name": package_name,
                "activity_name": activity_name,
                "metrics": {
                    "startup_time": {
                        "total_time_ms": 0,
                        "wait_time_ms": 0,
                        "status": "normal"
                    }
                },
                "anomalies": []
            }
            
            # 解析启动时间
            lines = result.strip().split('\n')
            for line in lines:
                if 'TotalTime:' in line:
                    match = re.search(r'TotalTime:\s*(\d+)', line)
                    if match:
                        startup_data["metrics"]["startup_time"]["total_time_ms"] = int(match.group(1))
                elif 'WaitTime:' in line:
                    match = re.search(r'WaitTime:\s*(\d+)', line)
                    if match:
                        startup_data["metrics"]["startup_time"]["wait_time_ms"] = int(match.group(1))
            
            # 判断启动时间是否异常
            total_time = startup_data["metrics"]["startup_time"]["total_time_ms"]
            if total_time > 3000:  # 超过3秒视为异常
                startup_data["metrics"]["startup_time"]["status"] = "slow"
                startup_data["anomalies"].append({
                    "type": "slow_startup",
                    "severity": "warning",
                    "description": f"启动时间过长: {total_time}ms"
                })
            
            return startup_data
            
        except Exception as e:
            return {
                "success": False,
                "error": f"获取启动时间失败: {str(e)}",
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
            }

    @staticmethod
    def get_logcat(keyword: str = None, level: str = "ERROR", device_id: str = None) -> dict:
        """
        获取应用日志
        参数:
        - keyword: 关键词过滤（可选）
        - level: 日志级别（ERROR, WARN, INFO等）
        - device_id: 设备ID（可选）
        返回: 结构化日志数据
        """
        try:
            cmd = "logcat -d"
            if keyword:
                cmd += f" | grep {keyword}"
            if device_id:
                cmd = f"-s {device_id} shell {cmd}"
            else:
                cmd = f"shell {cmd}"
            
            result = subprocess.check_output(f"adb {cmd}", shell=True, text=True)
            
            log_data = {
                "success": True,
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                "level": level,
                "keyword": keyword,
                "logs": [],
                "anomalies": []
            }
            
            # 解析日志
            lines = result.strip().split('\n')
            error_count = 0
            
            for line in lines:
                if level in line or (keyword and keyword in line):
                    log_data["logs"].append(line.strip())
                    if 'FATAL' in line or 'CRASH' in line:
                        error_count += 1
            
            # 检测异常
            if error_count > 0:
                log_data["anomalies"].append({
                    "type": "fatal_error",
                    "severity": "critical",
                    "description": f"发现{error_count}个致命错误"
                })
            
            return log_data
            
        except Exception as e:
            return {
                "success": False,
                "error": f"获取日志失败: {str(e)}",
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
            }

    @staticmethod
    def get_performance_snapshot(package_name: str, metrics: list = None, device_id: str = None) -> dict:
        """
        获取应用性能快照
        
        参数:
            package_name (str): 应用包名
            metrics (list, optional): 要获取的指标，默认全部
                可选: ["cpu", "memory", "fps", "battery"]
            device_id (str, optional): 设备ID
        
        返回:
            {
                "cpu": {"usage": 15.5, "threads": 25},
                "memory": {"pss": 120MB, "heap": 80MB},
                "fps": {"current": 58, "avg": 59.5},
                "battery": {"level": 85, "temp": 35}
            }
        """
        try:
            # 设置默认指标
            if metrics is None:
                metrics = ["cpu", "memory", "fps", "battery"]
            
            snapshot = {
                "success": True,
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                "package_name": package_name,
                "metrics": {},
                "anomalies": []
            }
            
            # 根据metrics参数获取指定指标
            if "memory" in metrics:
                memory_info = AdvancedPerformanceMonitor.get_memory_info(package_name, device_id)
                if memory_info.get("success"):
                    snapshot["metrics"]["memory"] = memory_info["metrics"]["memory"]
                    snapshot["anomalies"].extend(memory_info.get("anomalies", []))
            
            if "cpu" in metrics:
                cpu_info = AdvancedPerformanceMonitor.get_cpu_usage_by_package(package_name, device_id)
                if cpu_info.get("success"):
                    snapshot["metrics"]["cpu"] = cpu_info["metrics"]["cpu"]
                    snapshot["anomalies"].extend(cpu_info.get("anomalies", []))
            
            if "fps" in metrics:
                fps_info = AdvancedPerformanceMonitor.get_fps_info(package_name, device_id)
                if fps_info.get("success"):
                    snapshot["metrics"]["fps"] = fps_info["metrics"]["fps"]
                    snapshot["anomalies"].extend(fps_info.get("anomalies", []))
            
            if "battery" in metrics:
                battery_info = AdvancedPerformanceMonitor.get_battery_info(package_name, device_id)
                if battery_info.get("success"):
                    snapshot["metrics"]["battery"] = battery_info["metrics"]["battery"]
                    snapshot["anomalies"].extend(battery_info.get("anomalies", []))
            
            return snapshot
            
        except Exception as e:
            return {
                "success": False,
                "error": f"获取性能快照失败: {str(e)}",
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
            }

    @staticmethod
    def monitor_performance(package_name: str, duration: int = 60, interval: int = 5, metrics: list = None, device_id: str = None) -> dict:
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
        """
        try:
            # 设置默认指标
            if metrics is None:
                metrics = ["cpu", "memory", "fps"]
                
            if duration <= 0 or interval <= 0:
                return {
                    "success": False,
                    "error": "监测参数无效，请确保duration和interval大于0"
                }
            
            iterations = duration // interval
            performance_history = []
            
            for i in range(iterations):
                current_time = time.strftime("%Y-%m-%d %H:%M:%S")
                print(f"第{i+1}次监测 - {current_time}")
                
                # 获取性能快照（使用新的get_performance_snapshot方法）
                snapshot = AdvancedPerformanceMonitor.get_performance_snapshot(package_name, metrics, device_id)
                snapshot["iteration"] = i + 1
                snapshot["timestamp"] = current_time
                performance_history.append(snapshot)
                
                # 等待间隔时间
                time.sleep(interval)
            
            # 分析趋势
            trends = AdvancedPerformanceMonitor._analyze_performance_trends(performance_history)
            
            # 生成时间序列数据
            timeline = []
            alerts = []
            
            for snapshot in performance_history:
                if snapshot.get("success"):
                    timeline_data = {
                        "timestamp": snapshot.get("timestamp"),
                        "iteration": snapshot.get("iteration"),
                        "metrics": snapshot.get("metrics", {})
                    }
                    timeline.append(timeline_data)
                    
                    # 收集异常告警
                    alerts.extend(snapshot.get("anomalies", []))
            
            return {
                "success": True,
                "summary": AdvancedPerformanceMonitor._generate_summary(performance_history),
                "timeline": timeline,
                "alerts": alerts,
                "duration": duration,
                "interval": interval,
                "iterations": iterations,
                "trends": trends
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"持续性能监测失败: {str(e)}",
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
            }

    @staticmethod
    def _analyze_performance_trends(performance_history: list) -> dict:
        """分析性能趋势"""
        trends = {
            "memory_trend": "stable",
            "cpu_trend": "stable",
            "fps_trend": "stable",
            "anomaly_count": 0
        }
        
        if len(performance_history) < 2:
            return trends
        
        # 分析内存趋势
        memory_values = []
        for snapshot in performance_history:
            if snapshot.get("success") and "memory" in snapshot.get("metrics", {}):
                memory_values.append(snapshot["metrics"]["memory"]["total_pss_mb"])
        
        if len(memory_values) >= 2:
            # 简单线性趋势分析
            if memory_values[-1] > memory_values[0] * 1.2:  # 增长超过20%
                trends["memory_trend"] = "increasing"
            elif memory_values[-1] < memory_values[0] * 0.8:  # 减少超过20%
                trends["memory_trend"] = "decreasing"
        
        # 统计异常数量
        for snapshot in performance_history:
            trends["anomaly_count"] += len(snapshot.get("anomalies", []))
        
        return trends

    @staticmethod
    def _generate_summary(performance_history: list) -> dict:
        """生成监测摘要"""
        if not performance_history:
            return {}
        
        summary = {
            "total_snapshots": len(performance_history),
            "successful_snapshots": sum(1 for s in performance_history if s.get("success")),
            "total_anomalies": sum(len(s.get("anomalies", [])) for s in performance_history),
            "average_memory_mb": 0,
            "average_cpu_percent": 0,
            "average_fps": 0
        }
        
        # 计算平均值
        memory_values = []
        cpu_values = []
        fps_values = []
        
        for snapshot in performance_history:
            if snapshot.get("success"):
                metrics = snapshot.get("metrics", {})
                if "memory" in metrics:
                    memory_values.append(metrics["memory"]["total_pss_mb"])
                if "cpu" in metrics:
                    cpu_values.append(metrics["cpu"]["usage_percent"])
                if "fps" in metrics:
                    fps_values.append(metrics["fps"]["average"])
        
        if memory_values:
            summary["average_memory_mb"] = sum(memory_values) / len(memory_values)
        if cpu_values:
            summary["average_cpu_percent"] = sum(cpu_values) / len(cpu_values)
        if fps_values:
            summary["average_fps"] = sum(fps_values) / len(fps_values)
        
        return summary


# 使用示例
if __name__ == "__main__":
    collector = DeviceInfoCollector()
    devices_info = collector.collect_info()

    if devices_info:
        print(json.dumps(devices_info, indent=2))

        # 示例：对第一个设备执行一些操作
        if devices_info:
            first_device = devices_info[0]
            device_id = first_device["deviceId"]

            print("\n安装应用:")
            print(collector.install_app("path/to/your/app.apk", device_id))

            print("\n获取电池信息:")
            print(collector.get_battery_info(device_id))

            print("\n截图:")
            print(collector.take_screenshot("screenshot.png", device_id))

            print("\n获取日志:")
            print(collector.get_device_logs("device_logs.txt", device_id))

            # 性能监测示例
            print("\n=== 性能监测示例 ===")
            monitor = PerformanceMonitor()
            
            print("\n1. CPU使用率:")
            print(monitor.get_cpu_usage(device_id))
            
            print("\n2. 内存使用情况:")
            print(monitor.get_memory_usage(device_id))
            
            print("\n3. 电池状态:")
            print(monitor.get_battery_status(device_id))
            
            print("\n4. 综合性能报告:")
            print(monitor.get_comprehensive_performance(device_id))

            # 高级性能监测示例
            print("\n=== 高级性能监测示例 ===")
            advanced_monitor = AdvancedPerformanceMonitor()
            
            # 测试包名（需要替换为实际包名）
            test_package = "com.example.testapp"
            
            print("\n1. 内存详细信息:")
            memory_info = advanced_monitor.get_memory_info(test_package, device_id)
            print(json.dumps(memory_info, indent=2, ensure_ascii=False))
            
            print("\n2. CPU使用率（按包名）:")
            cpu_info = advanced_monitor.get_cpu_usage_by_package(test_package, device_id)
            print(json.dumps(cpu_info, indent=2, ensure_ascii=False))
            
            print("\n3. 综合性能快照:")
            snapshot = advanced_monitor.get_comprehensive_performance_snapshot(test_package, device_id)
            print(json.dumps(snapshot, indent=2, ensure_ascii=False))

            # 谨慎使用以下命令
            # print("\n重启设备:")
            # print(collector.reboot_device(device_id))
    else:
        print("无法获取设备信息")
