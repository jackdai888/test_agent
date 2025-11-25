#!/usr/bin/env python3
"""
回归测试功能验证脚本
"""

import sys
import os

# 添加项目路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_planner_regression():
    """测试回归测试计划生成"""
    print("🧪 测试回归测试计划生成...")
    
    try:
        from planner import TestPlanner
        
        # 创建测试规划器
        planner = TestPlanner()
        
        # 测试初始测试计划（无bug）
        print("\n📋 测试初始测试计划（无bug）...")
        plan_no_bugs = planner.create_test_plan(
            requirements="测试应用启动功能",
            previous_bugs=None
        )
        print(f"✅ 初始测试计划生成成功")
        print(f"   计划名称: {plan_no_bugs.name}")
        print(f"   任务阶段: {list(plan_no_bugs.tasks.keys())}")
        
        # 测试回归测试计划（有bug）
        print("\n🔄 测试回归测试计划（有bug）...")
        bugs = "插屏广告关闭按钮有时无法点击\n应用启动时间超过3秒"
        plan_with_bugs = planner.create_test_plan(
            requirements="执行回归测试",
            previous_bugs=bugs
        )
        print(f"✅ 回归测试计划生成成功")
        print(f"   计划名称: {plan_with_bugs.name}")
        print(f"   任务阶段: {list(plan_with_bugs.tasks.keys())}")
        
        return True
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        return False

def test_orchestrator_regression():
    """测试回归测试编排器"""
    print("\n🧪 测试回归测试编排器...")
    
    try:
        from orchestrator import WorkflowOrchestrator
        from planner import TestPlanner
        
        # 创建编排器
        orchestrator = WorkflowOrchestrator()
        
        # 创建回归测试计划
        planner = TestPlanner()
        bugs = "插屏广告关闭按钮有时无法点击"
        test_plan = planner.create_test_plan(
            requirements="回归测试验证",
            previous_bugs=bugs
        )
        
        # 测试回归测试执行
        print("\n▶️  执行回归测试工作流...")
        result = orchestrator.execute_workflow(test_plan, is_regression=True)
        
        print(f"✅ 回归测试执行成功")
        print(f"   最终状态: {result.status.value}")
        print(f"   总任务数: {result.total_tasks}")
        print(f"   成功任务: {result.success_tasks}")
        
        return True
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        return False

def test_agent_tool():
    """测试Agent中的回归测试工具"""
    print("\n🧪 测试Agent回归测试工具...")
    
    try:
        from agent import run_regression_test
        
        # 测试回归测试工具
        bugs = "插屏广告关闭按钮有时无法点击\n应用启动时间超过3秒"
        
        print("\n🔧 调用run_regression_test工具...")
        # 正确调用工具函数
        result = run_regression_test.func(bugs)
        
        print(f"✅ 回归测试工具执行成功")
        print(f"   结果长度: {len(result)} 字符")
        print(f"   结果预览: {result[:200]}...")
        
        return True
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        return False

def main():
    """主测试函数"""
    print("🚀 回归测试功能验证")
    print("=" * 50)
    
    # 运行测试
    tests = [
        ("测试规划器", test_planner_regression),
        ("测试编排器", test_orchestrator_regression),
        ("测试Agent工具", test_agent_tool)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        try:
            if test_func():
                print(f"✅ {test_name} - 通过")
                passed += 1
            else:
                print(f"❌ {test_name} - 失败")
        except Exception as e:
            print(f"❌ {test_name} - 异常: {e}")
    
    print("\n" + "=" * 50)
    print(f"📊 测试结果: {passed}/{total} 通过")
    
    if passed == total:
        print("🎉 所有测试通过！回归测试功能正常工作。")
    else:
        print("⚠️  部分测试失败，请检查代码。")

if __name__ == "__main__":
    main()