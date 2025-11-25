"""
自适应测试用例生成器 - 基于AI的智能测试用例生成系统
"""
import torch
import torch.nn as nn
from transformers import AutoTokenizer, AutoModel
import numpy as np
from typing import List, Dict, Any
import json
import re

class TestCaseGenerator(nn.Module):
    """测试用例生成神经网络"""
    
    def __init__(self, vocab_size=10000, embedding_dim=256, hidden_dim=512):
        super(TestCaseGenerator, self).__init__()
        
        # 文本编码器
        self.embedding = nn.Embedding(vocab_size, embedding_dim)
        self.encoder = nn.LSTM(embedding_dim, hidden_dim, batch_first=True, bidirectional=True)
        
        # 测试用例生成器
        self.test_case_decoder = nn.LSTM(hidden_dim * 2, hidden_dim, batch_first=True)
        self.test_case_output = nn.Linear(hidden_dim, vocab_size)
        
        # 测试数据生成器
        self.test_data_generator = nn.Sequential(
            nn.Linear(hidden_dim * 2, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, hidden_dim // 2),
            nn.ReLU(),
            nn.Linear(hidden_dim // 2, 100)  # 测试数据特征维度
        )
    
    def forward(self, input_ids, max_length=200):
        """生成测试用例"""
        # 编码输入
        embedded = self.embedding(input_ids)
        encoded, (hidden, cell) = self.encoder(embedded)
        
        # 使用编码后的隐藏状态生成测试用例
        decoder_input = encoded[:, -1:, :]  # 使用最后一个时间步
        
        # 生成测试用例序列
        test_cases = []
        for _ in range(max_length):
            decoder_output, (hidden, cell) = self.test_case_decoder(decoder_input, (hidden, cell))
            output = self.test_case_output(decoder_output.squeeze(1))
            test_cases.append(output)
            
            # 使用预测结果作为下一个输入
            _, top_idx = torch.topk(output, 1)
            decoder_input = self.embedding(top_idx).unsqueeze(1)
        
        # 生成测试数据
        test_data = self.test_data_generator(encoded.mean(dim=1))
        
        return torch.stack(test_cases, dim=1), test_data

class AdaptiveTestGenerator:
    """自适应测试生成器主类"""
    
    def __init__(self):
        # 初始化模型
        self.model = TestCaseGenerator()
        
        # 加载预训练语言模型用于文本理解
        try:
            self.tokenizer = AutoTokenizer.from_pretrained("microsoft/codebert-base")
            self.language_model = AutoModel.from_pretrained("microsoft/codebert-base")
        except:
            print("⚠️ 无法加载预训练模型，使用简化版本")
            self.tokenizer = None
            self.language_model = None
        
        # 测试用例模板库
        self.test_templates = self._load_test_templates()
        
        # 历史测试用例库
        self.test_case_history = []
    
    def _load_test_templates(self) -> Dict[str, List[str]]:
        """加载测试用例模板"""
        return {
            "ui_test": [
                "验证{元素}的{属性}是否正确",
                "测试{功能}的{操作}流程",
                "检查{页面}的{布局}是否正常"
            ],
            "api_test": [
                "测试{接口}的{方法}请求",
                "验证{接口}的{参数}校验",
                "检查{接口}的{响应}格式"
            ],
            "performance_test": [
                "测试{功能}的{性能}指标",
                "验证{操作}的{响应}时间",
                "检查{场景}的{资源}消耗"
            ],
            "security_test": [
                "验证{功能}的{安全}防护",
                "测试{接口}的{认证}机制",
                "检查{数据}的{加密}处理"
            ]
        }
    
    def analyze_app_structure(self, app_info: Dict[str, Any]) -> Dict[str, Any]:
        """分析应用结构，识别测试重点"""
        analysis = {
            'ui_elements': [],
            'api_endpoints': [],
            'critical_features': [],
            'performance_bottlenecks': [],
            'security_concerns': []
        }
        
        # 分析UI元素
        if 'screens' in app_info:
            for screen in app_info['screens']:
                analysis['ui_elements'].extend(screen.get('elements', []))
        
        # 分析API端点
        if 'apis' in app_info:
            analysis['api_endpoints'] = app_info['apis']
        
        # 识别关键功能
        if 'features' in app_info:
            analysis['critical_features'] = [
                feature for feature in app_info['features'] 
                if feature.get('importance', 0) > 0.7
            ]
        
        return analysis
    
    def generate_test_cases(self, app_info: Dict[str, Any], 
                          test_type: str = "ui_test", 
                          count: int = 5) -> List[Dict[str, Any]]:
        """生成自适应测试用例"""
        
        # 分析应用结构
        analysis = self.analyze_app_structure(app_info)
        
        # 选择测试模板
        templates = self.test_templates.get(test_type, [])
        
        test_cases = []
        
        for i in range(count):
            if templates:
                # 使用模板生成测试用例
                template = templates[i % len(templates)]
                test_case = self._fill_template(template, analysis, app_info)
            else:
                # 智能生成测试用例
                test_case = self._intelligent_generation(analysis, test_type)
            
            # 添加测试数据
            test_data = self._generate_test_data(test_case, analysis)
            
            test_cases.append({
                'id': f"test_{test_type}_{i+1}",
                'title': test_case,
                'type': test_type,
                'priority': self._calculate_priority(test_case, analysis),
                'test_steps': self._generate_test_steps(test_case),
                'expected_result': self._generate_expected_result(test_case),
                'test_data': test_data,
                'tags': self._extract_tags(test_case)
            })
        
        # 记录到历史
        self.test_case_history.extend(test_cases)
        
        return test_cases
    
    def _fill_template(self, template: str, analysis: Dict[str, Any], 
                      app_info: Dict[str, Any]) -> str:
        """填充测试模板"""
        # 简单的模板填充逻辑
        filled = template
        
        # 替换占位符
        if '{元素}' in filled and analysis['ui_elements']:
            element = np.random.choice(analysis['ui_elements'])
            filled = filled.replace('{元素}', element)
        
        if '{功能}' in filled and analysis['critical_features']:
            feature = np.random.choice(analysis['critical_features'])
            filled = filled.replace('{功能}', feature.get('name', '功能'))
        
        # 更多占位符替换...
        
        return filled
    
    def _intelligent_generation(self, analysis: Dict[str, Any], 
                              test_type: str) -> str:
        """智能生成测试用例"""
        # 基于分析结果智能生成
        if test_type == "ui_test" and analysis['ui_elements']:
            element = np.random.choice(analysis['ui_elements'])
            return f"验证{element}的显示和交互功能"
        
        elif test_type == "api_test" and analysis['api_endpoints']:
            endpoint = np.random.choice(analysis['api_endpoints'])
            return f"测试{endpoint}接口的完整流程"
        
        return f"执行{test_type}的基本验证"
    
    def _generate_test_steps(self, test_case: str) -> List[str]:
        """生成测试步骤"""
        steps = []
        
        if "验证" in test_case or "检查" in test_case:
            steps = [
                "启动应用",
                "导航到相关页面",
                "执行验证操作",
                "检查结果"
            ]
        elif "测试" in test_case:
            steps = [
                "准备测试环境",
                "执行测试操作",
                "验证响应结果",
                "清理测试数据"
            ]
        
        return steps
    
    def _generate_expected_result(self, test_case: str) -> str:
        """生成预期结果"""
        if "验证" in test_case:
            return "功能正常，符合预期"
        elif "测试" in test_case:
            return "操作成功，响应正确"
        elif "检查" in test_case:
            return "检查通过，无异常"
        
        return "测试通过"
    
    def _generate_test_data(self, test_case: str, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """生成测试数据"""
        return {
            'input_data': self._create_test_input(test_case),
            'validation_rules': self._create_validation_rules(test_case),
            'environment_config': self._create_environment_config()
        }
    
    def _calculate_priority(self, test_case: str, analysis: Dict[str, Any]) -> str:
        """计算测试用例优先级"""
        critical_keywords = ['登录', '支付', '核心', '重要']
        
        for keyword in critical_keywords:
            if keyword in test_case:
                return "高"
        
        return "中"
    
    def _extract_tags(self, test_case: str) -> List[str]:
        """提取测试标签"""
        tags = []
        
        if "UI" in test_case or "界面" in test_case:
            tags.append("ui")
        if "API" in test_case or "接口" in test_case:
            tags.append("api")
        if "性能" in test_case:
            tags.append("performance")
        if "安全" in test_case:
            tags.append("security")
        
        return tags

# 集成到Agent的工具函数
def generate_adaptive_tests(app_info: Dict[str, Any], 
                          test_types: List[str] = None,
                          count_per_type: int = 3) -> Dict[str, Any]:
    """生成自适应测试用例"""
    
    if test_types is None:
        test_types = ["ui_test", "api_test", "performance_test", "security_test"]
    
    generator = AdaptiveTestGenerator()
    
    all_test_cases = {}
    
    for test_type in test_types:
        test_cases = generator.generate_test_cases(
            app_info, test_type, count_per_type
        )
        all_test_cases[test_type] = test_cases
    
    return {
        'total_cases': sum(len(cases) for cases in all_test_cases.values()),
        'test_cases': all_test_cases,
        'generation_time': '2024-01-01T00:00:00',  # 实际应该使用当前时间
        'analysis_summary': generator.analyze_app_structure(app_info)
    }

if __name__ == "__main__":
    # 测试示例
    sample_app_info = {
        'name': '示例应用',
        'screens': [
            {'name': '登录页', 'elements': ['用户名输入框', '密码输入框', '登录按钮']},
            {'name': '主页', 'elements': ['导航栏', '内容区域', '设置按钮']}
        ],
        'apis': ['/api/login', '/api/user/info', '/api/data/list'],
        'features': [
            {'name': '用户登录', 'importance': 0.9},
            {'name': '数据展示', 'importance': 0.7},
            {'name': '设置管理', 'importance': 0.5}
        ]
    }
    
    result = generate_adaptive_tests(sample_app_info)
    print("生成的测试用例:")
    print(json.dumps(result, indent=2, ensure_ascii=False))