# ==================== 结果验证器模块 ====================
"""
ResultValidator - 结果验证器
负责验证测试结果的正确性，基于规则和AI进行结果分析
"""

import logging
import re
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from orchestrator import TaskResult

logger = logging.getLogger(__name__)


# ==================== 枚举定义 ====================
class ValidationStatus(Enum):
    """验证状态"""
    PASS = "pass"  # 通过
    FAIL = "fail"  # 失败
    PARTIAL = "partial"  # 部分通过
    UNKNOWN = "unknown"  # 未知


class ValidationType(Enum):
    """验证类型"""
    RULE_BASED = "rule_based"  # 基于规则
    AI_BASED = "ai_based"  # 基于AI
    HYBRID = "hybrid"  # 混合


# ==================== 数据模型 ====================
@dataclass
class ValidationRule:
    """验证规则"""
    name: str
    description: str
    pattern: Optional[str] = None  # 正则表达式
    expected_value: Optional[Any] = None
    comparator: str = "equals"  # equals, contains, regex, greater_than, less_than
    
    def validate(self, actual_value: Any) -> bool:
        """执行验证"""
        try:
            if self.comparator == "equals":
                return actual_value == self.expected_value
            elif self.comparator == "contains":
                return str(self.expected_value) in str(actual_value)
            elif self.comparator == "regex":
                return bool(re.search(self.pattern, str(actual_value)))
            elif self.comparator == "greater_than":
                return float(actual_value) > float(self.expected_value)
            elif self.comparator == "less_than":
                return float(actual_value) < float(self.expected_value)
            else:
                return False
        except Exception as e:
            logger.error(f"规则验证失败: {str(e)}")
            return False


@dataclass
class ValidationResult:
    """验证结果"""
    task_result: TaskResult
    status: ValidationStatus
    passed_checks: List[str] = field(default_factory=list)
    failed_checks: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    details: str = ""
    confidence: float = 1.0  # 置信度 0-1
    timestamp: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "task_id": self.task_result.task_id,
            "status": self.status.value,
            "passed_checks": self.passed_checks,
            "failed_checks": self.failed_checks,
            "warnings": self.warnings,
            "details": self.details,
            "confidence": self.confidence,
            "timestamp": self.timestamp.isoformat()
        }


# ==================== 验证器类 ====================
class ResultValidator:
    """结果验证器"""
    
    def __init__(self, llm_model=None, validation_type: ValidationType = ValidationType.HYBRID):
        """
        初始化验证器
        
        参数:
            llm_model: LLM模型实例（可选）
            validation_type: 验证类型
        """
        self.llm_model = llm_model
        self.validation_type = validation_type
        self.validation_rules = {}  # 规则库
        logger.info(f"ResultValidator 已初始化，验证类型: {validation_type.value}")
    
    def validate(self, task_result: TaskResult, expected_result: str = None) -> ValidationResult:
        """
        验证任务结果
        
        参数:
            task_result: 任务执行结果
            expected_result: 预期结果（可选）
        
        返回:
            ValidationResult: 验证结果
        """
        try:
            logger.info(f"验证任务结果: {task_result.task_id}")
            
            # 如果任务本身就失败了
            if task_result.error:
                return ValidationResult(
                    task_result=task_result,
                    status=ValidationStatus.FAIL,
                    failed_checks=["任务执行失败"],
                    details=f"任务执行错误: {task_result.error}"
                )
            
            # 根据验证类型选择验证方法
            if self.validation_type == ValidationType.RULE_BASED:
                return self._rule_based_validation(task_result, expected_result)
            elif self.validation_type == ValidationType.AI_BASED and self.llm_model:
                return self._ai_based_validation(task_result, expected_result)
            elif self.validation_type == ValidationType.HYBRID:
                # 先规则验证，再AI验证
                rule_result = self._rule_based_validation(task_result, expected_result)
                if rule_result.status == ValidationStatus.UNKNOWN and self.llm_model:
                    return self._ai_based_validation(task_result, expected_result)
                return rule_result
            else:
                logger.warning("未配置有效的验证方法")
                return self._default_validation(task_result)
                
        except Exception as e:
            logger.error(f"验证过程失败: {str(e)}")
            return ValidationResult(
                task_result=task_result,
                status=ValidationStatus.UNKNOWN,
                details=f"验证失败: {str(e)}"
            )
    
    def _rule_based_validation(self, task_result: TaskResult, expected_result: str = None) -> ValidationResult:
        """
        基于规则的验证
        
        参数:
            task_result: 任务结果
            expected_result: 预期结果
        
        返回:
            ValidationResult
        """
        passed_checks = []
        failed_checks = []
        warnings = []
        
        output = str(task_result.output)
        
        # 检查是否包含错误标识
        if "❌" in output or "错误" in output or "失败" in output or "Error" in output:
            failed_checks.append("输出中包含错误标识")
        else:
            passed_checks.append("无明显错误标识")
        
        # 检查是否包含成功标识
        if "✅" in output or "成功" in output or "完成" in output or "Success" in output:
            passed_checks.append("包含成功标识")
        
        # 如果有预期结果，进行匹配
        if expected_result:
            if expected_result.lower() in output.lower():
                passed_checks.append(f"包含预期内容: {expected_result}")
            else:
                failed_checks.append(f"未包含预期内容: {expected_result}")
        
        # 检查执行时间
        if task_result.duration > 60:
            warnings.append(f"执行时间较长: {task_result.duration:.2f}秒")
        
        # 判断最终状态
        if failed_checks:
            status = ValidationStatus.FAIL
        elif passed_checks:
            status = ValidationStatus.PASS
        else:
            status = ValidationStatus.UNKNOWN
        
        return ValidationResult(
            task_result=task_result,
            status=status,
            passed_checks=passed_checks,
            failed_checks=failed_checks,
            warnings=warnings,
            details=f"规则验证完成，通过 {len(passed_checks)} 项检查，失败 {len(failed_checks)} 项",
            confidence=0.7  # 规则验证置信度较低
        )
    
    def _ai_based_validation(self, task_result: TaskResult, expected_result: str = None) -> ValidationResult:
        """
        基于AI的验证
        
        参数:
            task_result: 任务结果
            expected_result: 预期结果
        
        返回:
            ValidationResult
        """
        try:
            from langchain_core.messages import HumanMessage
            
            prompt = f"""请验证以下测试结果是否符合预期。

任务ID: {task_result.task_id}
执行时长: {task_result.duration:.2f}秒
实际输出:
{task_result.output}

{f'预期结果: {expected_result}' if expected_result else ''}

请分析:
1. 测试结果是否正常 (PASS/FAIL/PARTIAL)
2. 如果失败，具体问题在哪里
3. 置信度 (0-1之间的数值)
4. 相关建议

请按以下格式回复:
STATUS: PASS/FAIL/PARTIAL
CONFIDENCE: 0.0-1.0
DETAILS: 详细分析
"""
            
            response = self.llm_model.invoke([HumanMessage(content=prompt)])
            ai_output = response.content
            
            # 解析AI响应
            status = ValidationStatus.UNKNOWN
            confidence = 0.8
            details = ai_output
            
            if "STATUS: PASS" in ai_output:
                status = ValidationStatus.PASS
            elif "STATUS: FAIL" in ai_output:
                status = ValidationStatus.FAIL
            elif "STATUS: PARTIAL" in ai_output:
                status = ValidationStatus.PARTIAL
            
            # 提取置信度
            conf_match = re.search(r'CONFIDENCE:\s*(0?\.\d+|1\.0|[01])', ai_output)
            if conf_match:
                confidence = float(conf_match.group(1))
            
            return ValidationResult(
                task_result=task_result,
                status=status,
                details=details,
                confidence=confidence,
                passed_checks=["AI验证完成"] if status == ValidationStatus.PASS else [],
                failed_checks=["AI验证失败"] if status == ValidationStatus.FAIL else []
            )
            
        except Exception as e:
            logger.error(f"AI验证失败: {str(e)}")
            return self._default_validation(task_result)
    
    def _default_validation(self, task_result: TaskResult) -> ValidationResult:
        """默认验证（简单判断）"""
        if task_result.error:
            status = ValidationStatus.FAIL
        else:
            status = ValidationStatus.PASS
        
        return ValidationResult(
            task_result=task_result,
            status=status,
            details="默认验证：基于任务执行状态",
            confidence=0.5
        )
    
    def add_validation_rule(self, task_id: str, rule: ValidationRule):
        """
        添加验证规则
        
        参数:
            task_id: 任务ID
            rule: 验证规则
        """
        if task_id not in self.validation_rules:
            self.validation_rules[task_id] = []
        self.validation_rules[task_id].append(rule)
        logger.info(f"已为任务 {task_id} 添加验证规则: {rule.name}")
    
    def validate_with_custom_rules(self, task_result: TaskResult) -> ValidationResult:
        """
        使用自定义规则验证
        
        参数:
            task_result: 任务结果
        
        返回:
            ValidationResult
        """
        rules = self.validation_rules.get(task_result.task_id, [])
        
        if not rules:
            return self._default_validation(task_result)
        
        passed_checks = []
        failed_checks = []
        
        for rule in rules:
            if rule.validate(task_result.output):
                passed_checks.append(rule.name)
            else:
                failed_checks.append(rule.name)
        
        status = ValidationStatus.PASS if not failed_checks else ValidationStatus.FAIL
        
        return ValidationResult(
            task_result=task_result,
            status=status,
            passed_checks=passed_checks,
            failed_checks=failed_checks,
            details=f"自定义规则验证完成"
        )


if __name__ == "__main__":
    # 测试代码
    logging.basicConfig(level=logging.INFO)
    
    from orchestrator import TaskStatus
    
    validator = ResultValidator()
    
    # 创建测试结果
    test_result = TaskResult(
        task_id="test_1",
        status=TaskStatus.SUCCESS,
        output="✅ 设备连接成功",
        duration=2.5
    )
    
    # 验证
    validation = validator.validate(test_result, expected_result="连接成功")
    
    print(f"\n验证结果:")
    print(f"状态: {validation.status.value}")
    print(f"置信度: {validation.confidence}")
    print(f"通过检查: {validation.passed_checks}")
    print(f"失败检查: {validation.failed_checks}")
