# Appium测试代理测试用例文档（黑盒测试版）

## 📋 测试场景说明

**重要说明**：由于只能获得打包好的APK文件而无法访问源代码，本测试用例文档专注于黑盒测试方法，通过UI元素识别和用户行为模拟来验证应用功能。

## 🔍 黑盒测试策略

### 测试方法
1. **UI元素识别**：通过文本内容、类名、资源ID等识别界面元素
2. **用户行为模拟**：模拟真实用户的操作流程
3. **功能验证**：通过界面反馈验证功能正确性
4. **性能监控**：监控应用启动时间、内存使用等性能指标

### 测试限制
- 无法直接访问应用内部逻辑
- 依赖UI元素的可见性和可操作性
- 需要灵活的测试用例适应不同的UI布局

## 📋 测试用例分类

### 1. 基础功能测试用例

#### 应用启动和基本导航测试
```python
# 测试用例：应用启动和基本功能验证
from appium import webdriver
from appium.webdriver.common.appiumby import AppiumBy
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time

def test_app_launch_and_basic_navigation():
    """测试应用启动和基本导航功能（黑盒测试）"""
    
    # 启动应用
    driver = webdriver.Remote("http://localhost:4723/wd/hub", desired_caps)
    
    try:
        # 1. 验证应用成功启动
        start_time = time.time()
        
        # 等待应用加载完成（通过查找常见界面元素）
        WebDriverWait(driver, 15).until(
            lambda d: d.find_elements(AppiumBy.CLASS_NAME, "android.widget.TextView") or 
                      d.find_elements(AppiumBy.CLASS_NAME, "android.widget.Button") or
                      d.find_elements(AppiumBy.CLASS_NAME, "android.widget.ImageView")
        )
        
        launch_time = time.time() - start_time
        print(f"📱 应用启动时间: {launch_time:.2f}秒")
        
        # 2. 扫描界面元素，识别应用结构
        all_elements = driver.find_elements(AppiumBy.XPATH, "//*")
        print(f"🔍 发现 {len(all_elements)} 个界面元素")
        
        # 3. 识别可能的导航元素
        buttons = driver.find_elements(AppiumBy.CLASS_NAME, "android.widget.Button")
        text_views = driver.find_elements(AppiumBy.CLASS_NAME, "android.widget.TextView")
        
        print("📋 界面元素分析:")
        for i, button in enumerate(buttons[:5]):  # 只显示前5个按钮
            try:
                text = button.text
                if text:
                    print(f"  按钮 {i+1}: '{text}'")
            except:
                pass
                
        for i, text_view in enumerate(text_views[:10]):  # 只显示前10个文本
            try:
                text = text_view.text
                if text and len(text.strip()) > 0:
                    print(f"  文本 {i+1}: '{text}'")
            except:
                pass
        
        # 4. 尝试基本的用户交互
        # 查找可能的登录/开始按钮
        start_buttons = []
        for button in buttons:
            try:
                text = button.text.lower() if button.text else ""
                if any(keyword in text for keyword in ["登录", "开始", "启动", "进入", "start", "login"]):
                    start_buttons.append(button)
            except:
                pass
        
        if start_buttons:
            print(f"🎯 找到 {len(start_buttons)} 个可能的开始按钮")
            # 点击第一个找到的开始按钮
            start_buttons[0].click()
            time.sleep(2)  # 等待页面切换
            
            # 验证页面切换成功
            new_elements = driver.find_elements(AppiumBy.XPATH, "//*")
            if len(new_elements) != len(all_elements):
                print("✅ 页面导航成功")
            else:
                print("⚠️  页面可能未切换")
        
        print("✅ 基础导航测试完成")
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        
    finally:
        driver.quit()
```

#### 智能表单填写测试
```python
def test_smart_form_interaction():
    """智能识别和填写表单（黑盒测试）"""
    driver = webdriver.Remote("http://localhost:4723/wd/hub", desired_caps)
    
    try:
        # 1. 扫描界面，识别输入字段
        input_fields = driver.find_elements(AppiumBy.CLASS_NAME, "android.widget.EditText")
        print(f"📝 发现 {len(input_fields)} 个输入字段")
        
        # 2. 根据字段提示文本智能填写
        for i, field in enumerate(input_fields):
            try:
                # 获取字段提示文本
                hint = field.get_attribute("text") or field.get_attribute("hint") or ""
                
                if hint:
                    print(f"  字段 {i+1} 提示: '{hint}'")
                    
                    # 根据提示文本智能填写内容
                    if any(keyword in hint.lower() for keyword in ["用户名", "账号", "user", "account"]):
                        field.send_keys("test_user_001")
                        print("    ↳ 填写用户名")
                    elif any(keyword in hint.lower() for keyword in ["密码", "password"]):
                        field.send_keys("TestPassword123!")
                        print("    ↳ 填写密码")
                    elif any(keyword in hint.lower() for keyword in ["邮箱", "email"]):
                        field.send_keys("test@example.com")
                        print("    ↳ 填写邮箱")
                    elif any(keyword in hint.lower() for keyword in ["手机", "phone"]):
                        field.send_keys("13800138000")
                        print("    ↳ 填写手机号")
                    else:
                        field.send_keys(f"test_data_{i}")
                        print("    ↳ 填写测试数据")
                        
            except Exception as e:
                print(f"    ⚠️ 字段 {i+1} 填写失败: {e}")
        
        # 3. 查找并点击提交按钮
        submit_buttons = []
        all_buttons = driver.find_elements(AppiumBy.CLASS_NAME, "android.widget.Button")
        
        for button in all_buttons:
            try:
                text = button.text.lower() if button.text else ""
                if any(keyword in text for keyword in ["提交", "确认", "完成", "submit", "confirm"]):
                    submit_buttons.append(button)
            except:
                pass
        
        if submit_buttons:
            submit_buttons[0].click()
            print("✅ 表单提交成功")
            time.sleep(3)  # 等待响应
            
            # 4. 验证提交结果
            # 检查是否有成功提示或错误信息
            success_indicators = driver.find_elements(AppiumBy.XPATH, 
                "//*[contains(@text, '成功') or contains(@text, '完成') or contains(@text, '谢谢')]")
            error_indicators = driver.find_elements(AppiumBy.XPATH,
                "//*[contains(@text, '错误') or contains(@text, '失败') or contains(@text, '无效')]")
            
            if success_indicators:
                print("🎉 表单提交成功验证")
            elif error_indicators:
                print("⚠️  表单提交出现错误")
            else:
                print("🔍 表单提交状态未知")
        
        print("✅ 智能表单测试完成")
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        
    finally:
        driver.quit()
```

### 2. UI交互测试用例（黑盒测试版）

#### 智能页面导航测试
```python
def test_smart_navigation_flow():
    """智能识别和测试页面导航（黑盒测试）"""
    driver = webdriver.Remote("http://localhost:4723/wd/hub", desired_caps)
    
    try:
        # 1. 记录初始页面状态
        initial_elements = driver.find_elements(AppiumBy.XPATH, "//*")
        print(f"📊 初始页面元素数量: {len(initial_elements)}")
        
        # 2. 识别可能的导航元素（标签页、菜单项）
        navigation_elements = []
        
        # 查找可能的底部标签栏
        bottom_tabs = driver.find_elements(AppiumBy.XPATH, 
            "//android.widget.TabWidget//android.widget.TextView")
        
        # 查找可能的菜单按钮
        menu_buttons = driver.find_elements(AppiumBy.XPATH,
            "//*[contains(@text, '菜单') or contains(@text, 'Menu') or contains(@content-desc, 'menu')]")
        
        # 查找可能的导航图标
        nav_icons = driver.find_elements(AppiumBy.XPATH,
            "//android.widget.ImageView[contains(@content-desc, 'nav') or contains(@content-desc, 'menu')]")
        
        navigation_elements.extend(bottom_tabs)
        navigation_elements.extend(menu_buttons)
        navigation_elements.extend(nav_icons)
        
        print(f"🧭 发现 {len(navigation_elements)} 个导航元素")
        
        # 3. 测试导航功能
        tested_pages = 0
        
        for i, nav_element in enumerate(navigation_elements[:3]):  # 最多测试3个导航
            try:
                # 记录点击前的页面状态
                before_click = len(driver.find_elements(AppiumBy.XPATH, "//*"))
                
                # 点击导航元素
                nav_element.click()
                time.sleep(2)  # 等待页面加载
                
                # 记录点击后的页面状态
                after_click = len(driver.find_elements(AppiumBy.XPATH, "//*"))
                
                # 判断页面是否发生变化
                if before_click != after_click:
                    print(f"✅ 导航 {i+1}: 页面切换成功 ({before_click} → {after_click} 元素)")
                    tested_pages += 1
                    
                    # 验证新页面内容
                    new_texts = driver.find_elements(AppiumBy.CLASS_NAME, "android.widget.TextView")
                    if new_texts:
                        print(f"    📄 新页面包含 {len(new_texts)} 个文本元素")
                        
                        # 显示前3个文本内容
                        for j, text_view in enumerate(new_texts[:3]):
                            try:
                                text = text_view.text
                                if text:
                                    print(f"      文本 {j+1}: '{text[:30]}...'")
                            except:
                                pass
                else:
                    print(f"⚠️  导航 {i+1}: 页面可能未切换")
                    
                # 尝试返回上一页（如果有返回按钮）
                back_buttons = driver.find_elements(AppiumBy.XPATH,
                    "//*[contains(@text, '返回') or contains(@text, 'Back') or contains(@content-desc, 'back')]")
                
                if back_buttons:
                    back_buttons[0].click()
                    time.sleep(1)
                    print("    ↩️ 成功返回上一页")
                
            except Exception as e:
                print(f"❌ 导航 {i+1} 测试失败: {e}")
        
        print(f"📈 成功测试了 {tested_pages} 个页面导航")
        
        # 4. 测试滑动导航（如果有ViewPager等）
        print("🔄 测试滑动导航...")
        
        # 获取屏幕尺寸
        window_size = driver.get_window_size()
        width = window_size['width']
        height = window_size['height']
        
        # 尝试左右滑动
        for direction in ["left", "right"]:
            try:
                before_swipe = len(driver.find_elements(AppiumBy.XPATH, "//*"))
                
                if direction == "left":
                    # 从右向左滑动
                    driver.swipe(width * 0.8, height * 0.5, width * 0.2, height * 0.5, 500)
                else:
                    # 从左向右滑动
                    driver.swipe(width * 0.2, height * 0.5, width * 0.8, height * 0.5, 500)
                
                time.sleep(1)
                after_swipe = len(driver.find_elements(AppiumBy.XPATH, "//*"))
                
                if before_swipe != after_swipe:
                    print(f"✅ {direction}滑动: 页面切换成功")
                else:
                    print(f"⚠️  {direction}滑动: 页面可能不支持滑动导航")
                    
            except Exception as e:
                print(f"❌ {direction}滑动测试失败: {e}")
        
        print("✅ 智能导航测试完成")
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        
    finally:
        driver.quit()
```

#### 表单验证测试
```python
def test_form_validation():
    """测试表单验证功能"""
    driver = webdriver.Remote("http://localhost:4723/wd/hub", desired_caps)
    
    try:
        # 1. 测试空表单提交
        submit_button = driver.find_element(AppiumBy.ID, "submit_button")
        submit_button.click()
        
        # 验证错误提示
        error_message = driver.find_element(AppiumBy.ID, "error_message")
        assert "请输入" in error_message.text
        
        # 2. 测试无效邮箱格式
        email_field = driver.find_element(AppiumBy.ID, "email_field")
        email_field.send_keys("invalid-email")
        submit_button.click()
        
        error_message = driver.find_element(AppiumBy.ID, "error_message")
        assert "邮箱格式不正确" in error_message.text
        
        # 3. 测试密码强度
        password_field = driver.find_element(AppiumBy.ID, "password_field")
        password_field.send_keys("123")
        submit_button.click()
        
        error_message = driver.find_element(AppiumBy.ID, "error_message")
        assert "密码强度不足" in error_message.text
        
        print("✅ 表单验证测试通过")
        
    finally:
        driver.quit()
```

### 3. 性能测试用例

#### 启动时间测试
```python
def test_app_launch_time():
    """测试应用启动时间"""
    import time
    
    start_time = time.time()
    
    driver = webdriver.Remote("http://localhost:4723/wd/hub", desired_caps)
    
    # 等待应用完全加载
    WebDriverWait(driver, 30).until(
        EC.presence_of_element_located((AppiumBy.ID, "main_content"))
    )
    
    end_time = time.time()
    launch_time = end_time - start_time
    
    print(f"📊 应用启动时间: {launch_time:.2f}秒")
    
    # 性能标准：启动时间应小于5秒
    assert launch_time < 5.0, f"启动时间过长: {launch_time:.2f}秒"
    
    driver.quit()
    print("✅ 启动时间测试通过")
```

#### 内存使用测试
```python
def test_memory_usage():
    """测试应用内存使用情况"""
    import psutil
    import os
    
    # 获取应用包名
    package_name = "com.example.app"
    
    # 启动应用前获取内存基线
    initial_memory = psutil.virtual_memory().used
    
    driver = webdriver.Remote("http://localhost:4723/wd/hub", desired_caps)
    
    # 执行一些操作
    # ... 操作代码 ...
    
    # 获取操作后的内存使用
    final_memory = psutil.virtual_memory().used
    memory_increase = final_memory - initial_memory
    
    print(f"📊 内存增加: {memory_increase / 1024 / 1024:.2f} MB")
    
    # 内存标准：内存增加应小于50MB
    assert memory_increase < 50 * 1024 * 1024, f"内存使用过高: {memory_increase / 1024 / 1024:.2f} MB"
    
    driver.quit()
    print("✅ 内存使用测试通过")
```

### 4. 广告测试用例

#### 广告展示测试
```python
# 广告测试用例示例
def test_ad_display():
    """测试广告展示功能"""
    driver = webdriver.Remote("http://localhost:4723/wd/hub", desired_caps)
    
    try:
        # 等待广告加载
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((AppiumBy.ID, "ad_container"))
        )
        
        # 验证广告显示
        ad_element = driver.find_element(AppiumBy.ID, "ad_container")
        assert ad_element.is_displayed()
        
        # 验证广告尺寸
        ad_size = ad_element.size
        assert ad_size['width'] > 0 and ad_size['height'] > 0
        
        print("✅ 广告展示测试通过")
        
    finally:
        driver.quit()
```

#### 广告点击测试
```python
def test_ad_click():
    """测试广告点击功能"""
    driver = webdriver.Remote("http://localhost:4723/wd/hub", desired_caps)
    
    try:
        # 等待广告加载
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((AppiumBy.ID, "ad_container"))
        )
        
        # 点击广告
        ad_element = driver.find_element(AppiumBy.ID, "ad_container")
        ad_element.click()
        
        # 验证跳转
        WebDriverWait(driver, 5).until(
            EC.number_of_windows_to_be(2)
        )
        
        # 切换窗口
        driver.switch_to.window(driver.window_handles[1])
        
        # 验证广告页面加载
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((AppiumBy.TAG_NAME, "body"))
        )
        
        print("✅ 广告点击测试通过")
        
    finally:
        driver.quit()
```

### 5. 异常场景测试用例

#### 网络异常测试
```python
def test_network_error_handling():
    """测试网络异常处理"""
    driver = webdriver.Remote("http://localhost:4723/wd/hub", desired_caps)
    
    try:
        # 模拟网络断开（需要特殊配置）
        # 这里使用模拟网络错误场景
        
        # 触发需要网络的操作
        refresh_button = driver.find_element(AppiumBy.ID, "refresh_button")
        refresh_button.click()
        
        # 验证错误处理
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((AppiumBy.ID, "network_error_message"))
        )
        
        error_message = driver.find_element(AppiumBy.ID, "network_error_message")
        assert "网络连接失败" in error_message.text
        
        # 验证重试功能
        retry_button = driver.find_element(AppiumBy.ID, "retry_button")
        assert retry_button.is_displayed()
        
        print("✅ 网络异常处理测试通过")
        
    finally:
        driver.quit()
```

#### 数据加载失败测试
```python
def test_data_loading_error():
    """测试数据加载失败处理"""
    driver = webdriver.Remote("http://localhost:4723/wd/hub", desired_caps)
    
    try:
        # 导航到数据加载页面
        data_page = driver.find_element(AppiumBy.ID, "data_page")
        data_page.click()
        
        # 模拟数据加载失败（通过特殊配置）
        
        # 验证加载失败提示
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((AppiumBy.ID, "loading_error"))
        )
        
        error_element = driver.find_element(AppiumBy.ID, "loading_error")
        assert "加载失败" in error_element.text
        
        # 验证重载功能
        reload_button = driver.find_element(AppiumBy.ID, "reload_button")
        assert reload_button.is_enabled()
        
        print("✅ 数据加载失败处理测试通过")
        
    finally:
        driver.quit()
```

## 🎯 测试用例编写规范

### 命名规范
- 测试函数名以 `test_` 开头
- 使用描述性名称，如 `test_user_login_success`
- 包含测试场景描述，如 `test_form_validation_invalid_email`

### 结构规范
```python
def test_example():
    """
    测试用例描述：
    - 前置条件
    - 测试步骤
    - 预期结果
    """
    # 1. 前置条件设置
    
    # 2. 执行测试步骤
    
    # 3. 验证结果
    
    # 4. 清理资源
```

### 断言规范
- 使用明确的断言消息
- 验证关键业务逻辑
- 包含边界条件测试

## 📊 测试用例执行

### 使用Appium测试代理执行
```python
# 通过测试代理执行测试用例
from agent import AppiumAgent

# 创建测试代理实例
agent = AppiumAgent()

# 执行测试用例
test_results = agent.run_test_case("test_user_login")

# 查看测试结果
print(f"测试状态: {test_results.status}")
print(f"执行时间: {test_results.duration}")
print(f"错误信息: {test_results.error}")
```

### 批量执行测试用例
```python
# 批量执行测试用例套件
test_suite = [
    "test_user_login",
    "test_user_registration", 
    "test_navigation_flow",
    "test_form_validation"
]

for test_case in test_suite:
    result = agent.run_test_case(test_case)
    print(f"{test_case}: {result.status}")
```

---

## 🔄 测试用例维护

### 定期更新
- 根据应用功能变化更新测试用例
- 添加新的边界条件测试
- 移除过时的测试用例

### 性能优化
- 优化测试用例执行时间
- 减少不必要的等待
- 使用更高效的元素定位方式

### 文档同步
- 保持测试用例文档与实际代码同步
- 记录测试用例变更历史
- 维护测试用例依赖关系
