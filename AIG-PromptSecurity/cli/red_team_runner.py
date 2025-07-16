from cli.aig_logger import logger
from cli.aig_logger import (
    newPlanStep, statusUpdate, toolUsed, actionLog, resultUpdate
)

from typing import List, Any, Optional
from deepteam.red_teamer import RedTeamer
from deepteam.plugin_system import PluginManager
from .models import OpenaiAlikeModel
from .parsers import parse_attack, parse_vulnerability, parse_metric_class, dynamic_import


class RedTeamRunner:
    """红队测试运行器"""
    
    def __init__(self, plugin_manager: PluginManager):
        self.plugin_manager = plugin_manager
    
    def run_red_team(
        self,
        model: OpenaiAlikeModel,
        simulator_model: OpenaiAlikeModel,
        evaulate_model: OpenaiAlikeModel,
        scenarios: List[str],
        techniques: List[str],
        async_mode: bool = False,
        choice: str = "random",
        metric: Optional[str] = None,
        report_path: Optional[str] = None
    ) -> str:
        """运行红队测试"""
        logger.new_plan_step(newPlanStep(stepId="1", title="Pre-Jailbreak Parameter Parsing"))
        logger.status_update(statusUpdate(stepId="1", brief="Pre-Jailbreak Parameter Parsing", description=f"Create model {model.get_model_name()}"))

        # 解析漏洞
        logger.status_update(statusUpdate(stepId="1", brief="Pre-Jailbreak Parameter Parsing", description="Create scenarios"))
        vulnerabilities = []
        for arg in scenarios:
            vs = parse_vulnerability(arg, self.plugin_manager)
            vulnerabilities.extend(vs)
        
        # logger.debug(f"Total vulnerabilities created: {len(vulnerabilities)}")
        for i, v in enumerate(vulnerabilities):
            logger.debug(f"Vulnerability {i+1}: {v.get_name()}")
            if hasattr(v, 'prompts'):
                logger.debug(f"Vulnerability {i+1} prompts: {v.prompts}")

        # 解析攻击手法
        logger.status_update(statusUpdate(stepId="1", brief="Pre-Jailbreak Parameter Parsing", description=f"Create attacks"))
        attacks = [parse_attack(a, self.plugin_manager) for a in techniques]
        # logger.debug(f"Total attacks created: {len(attacks)}")

        # 获取攻击策略
        logger.debug(f"Attack selection strategy: {choice}")

        # 类型转换
        vulnerabilities = list(vulnerabilities)
        attacks = list(attacks)

        # 运行红队测试
        red_teamer = RedTeamer(simulator_model=simulator_model, evaluation_model=evaulate_model, async_mode=async_mode)
        
        # 如果指定了自定义metric，则对所有vulnerability类型使用该metric
        metric_class_path = parse_metric_class(metric) if metric else None
        if metric_class_path:
            logger.debug(f"Using metric: {metric_class_path}")
            
            # 首先检查是否是自定义插件
            custom_metric = self.plugin_manager.create_metric_instance(metric_class_path, model=evaulate_model, async_mode=async_mode)
            if custom_metric:
                red_teamer.custom_metric = custom_metric  # type: ignore
            else:
                # 如果不是自定义插件，使用内置映射
                custom_metric_class = dynamic_import(metric_class_path)
                
                # 尝试不同的初始化方式
                try:
                    # 首先尝试使用model和async_mode参数
                    custom_metric = custom_metric_class(model=evaulate_model, async_mode=async_mode)
                except TypeError:
                    try:
                        # 如果失败，尝试只使用model参数
                        custom_metric = custom_metric_class(model=evaulate_model)
                    except TypeError:
                        try:
                            # 如果还是失败，尝试使用async_mode参数
                            custom_metric = custom_metric_class(async_mode=async_mode)
                        except TypeError:
                            # 最后尝试无参数初始化
                            custom_metric = custom_metric_class()
                
                red_teamer.custom_metric = custom_metric  # type: ignore
        
        model_callback = model.a_generate if async_mode else model.generate
        red_teamer.red_team(
            model_callback=model_callback,
            vulnerabilities=vulnerabilities,
            attacks=attacks,
            choice=choice  # 传递攻击选择策略
        )
        content, status = red_teamer.get_risk_assessment_markdown()
        with open(report_path, "w", encoding="utf-8") as fw:
            fw.write(content)
        logger.result_update(resultUpdate(msgType="file", content=report_path, status=status))

        return red_teamer.save_risk_assessment_report() 
