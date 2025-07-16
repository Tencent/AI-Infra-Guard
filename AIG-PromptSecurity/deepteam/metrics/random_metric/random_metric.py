 #!/usr/bin/env python3
"""
简单的随机Metric：以50%的概率随机判断通过或不通过
"""

import random
from typing import Tuple


class RandomMetric:
    """
    简单的随机评估metric
    以50%的概率随机判断通过或不通过
    """
    
    def __init__(self, category: str = "random_check"):
        """
        初始化随机metric
        
        Args:
            category: 评估类别名称
        """
        self.category = category
        self.score = None
        self.reason = None
        self.success = None
        self.error = None

    def measure(self, test_case) -> float:
        """
        统一入口，做参数检查、日志等，然后调用evaluate
        """
        try:
            score, reason = self.evaluate(test_case)
            self.score = score
            self.reason = reason
            self.success = self.score == 1.0
            self.error = None
            return self.score
        except Exception as e:
            self.error = str(e)
            self.success = False
            self.score = 0.0
            return self.score

    def evaluate(self, test_case) -> tuple[float, str]:
        """
        真正的评估逻辑（这里是50%概率通过/不通过）
        """
        is_pass = random.choice([True, False])
        if is_pass:
            return 1.0, "随机评估：通过"
        else:
            return 0.0, "随机评估：不通过"

    async def a_measure(self, test_case) -> float:
        """
        异步评估方法
        """
        score, reason = await self.a_evaluate(test_case)
        self.score = score
        self.reason = reason
        self.success = self.score == 1.0
        self.error = None
        return self.score

    async def a_evaluate(self, test_case) -> tuple[float, str]:
        # 这里可以实现异步逻辑，当前直接调用同步evaluate
        return self.evaluate(test_case)

    def is_successful(self) -> bool:
        """
        判断评估是否成功
        """
        if self.error is not None:
            return False
        return self.success is True

    @property
    def __name__(self):
        return f"Random Metric ({self.category})"


# 使用示例
class CustomToxicityVulnerability:
    """示例：支持自定义metric的vulnerability"""
    
    def __init__(self, custom_metric, name: str = "Custom Toxicity"):
        self.custom_metric = custom_metric
        self.name = name
    
    def get_name(self) -> str:
        return self.name
    
    def get_custom_metrics_map(self):
        """返回自定义metric映射"""
        from deepteam.vulnerabilities.toxicity import ToxicityType
        return {
            ToxicityType.PROFANITY: self.custom_metric,
            ToxicityType.INSULTS: self.custom_metric,
        }


# 测试代码
if __name__ == "__main__":
    # 创建随机metric
    random_metric = RandomMetric("random_safety_check")
    
    # 创建测试用例
    class TestCase:
        def __init__(self, input_text, output_text):
            self.input = input_text
            self.actual_output = output_text
    
    # 测试用例
    test_cases = [
        TestCase("Hello", "Hi there!"),
        TestCase("How are you?", "I'm doing well, thank you!"),
        TestCase("What's the weather?", "It's sunny today."),
        TestCase("Tell me a joke", "Why did the chicken cross the road?"),
        TestCase("What time is it?", "It's currently 3:30 PM."),
    ]
    
    print("=== 随机Metric测试 ===")
    print("每个测试用例都有50%的概率通过或不通过\n")
    
    for i, test_case in enumerate(test_cases, 1):
        result = random_metric.measure(test_case)
        status = "✓ 通过" if random_metric.success else "✗ 不通过"
        print(f"测试{i}: {status} | Score={random_metric.score} | Reason={random_metric.reason}")
    
    print(f"\n随机metric创建完成！")
    print(f"类别: {random_metric.category}")
    print(f"名称: {random_metric.__name__}") 