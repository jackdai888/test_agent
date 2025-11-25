"""
智能测试策略优化器 - 基于PyTorch的深度学习测试优化系统
"""
import torch
import torch.nn as nn
import torch.optim as optim
import numpy as np
from typing import Dict, List, Any
import json
from datetime import datetime

class TestStrategyOptimizer(nn.Module):
    """测试策略优化神经网络"""
    
    def __init__(self, input_dim=50, hidden_dim=128, output_dim=10):
        super(TestStrategyOptimizer, self).__init__()
        
        # 特征编码层
        self.feature_encoder = nn.Sequential(
            nn.Linear(input_dim, hidden_dim),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(hidden_dim, hidden_dim),
            nn.ReLU(),
            nn.Dropout(0.2)
        )
        
        # 策略输出层
        self.strategy_predictor = nn.Sequential(
            nn.Linear(hidden_dim, hidden_dim // 2),
            nn.ReLU(),
            nn.Linear(hidden_dim // 2, output_dim),
            nn.Softmax(dim=-1)
        )
        
        # 效率预测层
        self.efficiency_predictor = nn.Sequential(
            nn.Linear(hidden_dim, 1),
            nn.Sigmoid()
        )
    
    def forward(self, x):
        """前向传播"""
        encoded = self.feature_encoder(x)
        strategy = self.strategy_predictor(encoded)
        efficiency = self.efficiency_predictor(encoded)
        return strategy, efficiency

class StrategyOptimizer:
    """策略优化器主类"""
    
    def __init__(self, model_path="models/test_strategy_model.pth"):
        self.model = TestStrategyOptimizer()
        self.optimizer = optim.Adam(self.model.parameters(), lr=0.001)
        self.criterion = nn.CrossEntropyLoss()
        self.model_path = model_path
        self.history = []
        
        # 加载已有模型
        self.load_model()
    
    def extract_features(self, test_context: Dict[str, Any]) -> torch.Tensor:
        """从测试上下文中提取特征"""
        features = []
        
        # 应用特征
        features.extend([
            test_context.get('app_complexity', 0.5),  # 应用复杂度
            test_context.get('test_coverage', 0.3),    # 测试覆盖率
            test_context.get('defect_density', 0.1),   # 缺陷密度
            test_context.get('code_churn', 0.2),       # 代码变更频率
            test_context.get('team_experience', 0.7),  # 团队经验
        ])
        
        # 历史成功率特征
        history = test_context.get('test_history', [])
        if history:
            success_rate = sum(1 for h in history if h.get('success', False)) / len(history)
            avg_duration = np.mean([h.get('duration', 0) for h in history])
            features.extend([success_rate, avg_duration])
        else:
            features.extend([0.5, 0])  # 默认值
        
        # 填充到固定维度
        while len(features) < 50:
            features.append(0.0)
        
        return torch.tensor(features[:50], dtype=torch.float32)
    
    def recommend_strategy(self, test_context: Dict[str, Any]) -> Dict[str, Any]:
        """推荐最优测试策略"""
        self.model.eval()
        
        with torch.no_grad():
            features = self.extract_features(test_context)
            strategy_probs, efficiency = self.model(features.unsqueeze(0))
            
            # 选择最优策略
            strategy_idx = torch.argmax(strategy_probs).item()
            
            # 策略映射
            strategies = [
                "探索性测试优先", "回归测试优先", "性能测试优先", 
                "安全测试优先", "兼容性测试优先", "UI测试优先",
                "API测试优先", "单元测试优先", "集成测试优先", "端到端测试优先"
            ]
            
            return {
                'recommended_strategy': strategies[strategy_idx],
                'strategy_confidence': strategy_probs[0][strategy_idx].item(),
                'expected_efficiency': efficiency.item(),
                'alternative_strategies': [
                    {'strategy': strategies[i], 'confidence': prob.item()}
                    for i, prob in enumerate(strategy_probs[0])
                    if i != strategy_idx and prob.item() > 0.1
                ]
            }
    
    def update_model(self, test_result: Dict[str, Any]):
        """根据测试结果更新模型"""
        self.model.train()
        
        features = self.extract_features(test_result['context'])
        
        # 创建目标标签（基于实际效果）
        actual_efficiency = test_result.get('efficiency_score', 0.5)
        strategy_used = test_result.get('strategy_used', 0)
        
        # 计算损失并更新
        strategy_probs, predicted_efficiency = self.model(features.unsqueeze(0))
        
        # 策略损失
        strategy_loss = self.criterion(strategy_probs, torch.tensor([strategy_used]))
        
        # 效率损失
        efficiency_loss = nn.MSELoss()(predicted_efficiency, torch.tensor([[actual_efficiency]]))
        
        # 总损失
        total_loss = strategy_loss + efficiency_loss
        
        self.optimizer.zero_grad()
        total_loss.backward()
        self.optimizer.step()
        
        # 记录历史
        self.history.append({
            'timestamp': datetime.now().isoformat(),
            'context': test_result['context'],
            'result': test_result,
            'loss': total_loss.item()
        })
        
        # 定期保存模型
        if len(self.history) % 10 == 0:
            self.save_model()
    
    def save_model(self):
        """保存模型"""
        torch.save({
            'model_state_dict': self.model.state_dict(),
            'optimizer_state_dict': self.optimizer.state_dict(),
            'history': self.history
        }, self.model_path)
    
    def load_model(self):
        """加载模型"""
        try:
            checkpoint = torch.load(self.model_path)
            self.model.load_state_dict(checkpoint['model_state_dict'])
            self.optimizer.load_state_dict(checkpoint['optimizer_state_dict'])
            self.history = checkpoint.get('history', [])
            print("✅ 测试策略模型加载成功")
        except FileNotFoundError:
            print("⚠️ 未找到已有模型，使用初始模型")
        except Exception as e:
            print(f"❌ 模型加载失败: {e}")

# 集成到现有Agent的工具函数
def get_optimized_test_strategy(app_info: Dict[str, Any]) -> Dict[str, Any]:
    """获取优化后的测试策略"""
    optimizer = StrategyOptimizer()
    
    # 构建测试上下文
    test_context = {
        'app_complexity': app_info.get('complexity', 0.5),
        'test_coverage': app_info.get('coverage', 0.3),
        'defect_density': app_info.get('defect_rate', 0.1),
        'code_churn': app_info.get('churn_rate', 0.2),
        'team_experience': app_info.get('team_exp', 0.7),
        'test_history': app_info.get('history', [])
    }
    
    return optimizer.recommend_strategy(test_context)

if __name__ == "__main__":
    # 测试示例
    test_app_info = {
        'complexity': 0.8,
        'coverage': 0.4,
        'defect_rate': 0.15,
        'churn_rate': 0.3,
        'team_exp': 0.6,
        'history': [
            {'success': True, 'duration': 120, 'strategy': 0},
            {'success': False, 'duration': 180, 'strategy': 1}
        ]
    }
    
    strategy = get_optimized_test_strategy(test_app_info)
    print("推荐策略:", json.dumps(strategy, indent=2, ensure_ascii=False))