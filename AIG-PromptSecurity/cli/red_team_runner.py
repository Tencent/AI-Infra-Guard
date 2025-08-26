import pandas as pd

from cli.aig_logger import logger
from cli.aig_logger import (
    newPlanStep, statusUpdate, toolUsed, actionLog, resultUpdate
)
import uuid
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
        models: List[OpenaiAlikeModel],
        simulator_model: OpenaiAlikeModel,
        evaluate_model: OpenaiAlikeModel,
        scenarios: List[str],
        techniques: List[str],
        async_mode: bool = False,
        choice: str = "random",
        metric: Optional[str] = None,
        report_path: Optional[str] = None,
    ) -> str:
        """运行红队测试"""
        logger.new_plan_step(newPlanStep(stepId="1", title=logger.translated_msg("Pre-Jailbreak Parameter Parsing")))
        for m in models:
            logger.status_update(statusUpdate(stepId="1", brief=logger.translated_msg("Pre-Jailbreak Parameter Parsing"), description=logger.translated_msg("Load model: {model_name}", model_name=m.get_model_name()), status="running"))
            # 测试连通
            is_connection, msg = m.test_model_connection()
            m_status = "completed" if is_connection else "failed"
            logger.status_update(statusUpdate(stepId="1", brief=logger.translated_msg("Pre-Jailbreak Parameter Parsing"), description=logger.translated_msg("Load model: {model_name}", model_name=m.get_model_name()), status=m_status))
            if m_status == "failed":
                logger.error(msg)
                logger.critical_issue(content=logger.translated_msg("Load model: {model_name} failed", model_name=m.get_model_name()))
                return

        # 解析漏洞
        logger.status_update(statusUpdate(stepId="1", brief=logger.translated_msg("Pre-Jailbreak Parameter Parsing"), description=logger.translated_msg("Load scenarios"), status="completed"))

        vulnerabilities = []
        try:
            for arg in scenarios:
                vs, vs_name = parse_vulnerability(arg, self.plugin_manager)
                if vs_name is not None:
                    logger.status_update(statusUpdate(stepId="1", brief=logger.translated_msg("Pre-Jailbreak Parameter Parsing"), description=logger.translated_msg("Load inputs: {vs_name}", vs_name=vs_name), status="completed"))
                vulnerabilities.extend(vs)
        except Exception as e:
            logger.error(e)
            logger.critical_issue(content=logger.translated_msg("Load scenarios failed"))
            return
       
        logger.status_update(statusUpdate(stepId="1", brief=logger.translated_msg("Pre-Jailbreak Parameter Parsing"), description=logger.translated_msg("Load evaluate model: {model_name}", model_name=evaluate_model.get_model_name()), status="running"))
        # 测试连通
        is_connection, msg = evaluate_model.test_model_connection()
        m_status = "completed" if is_connection else "failed"
        logger.status_update(statusUpdate(stepId="1", brief=logger.translated_msg("Pre-Jailbreak Parameter Parsing"), description=logger.translated_msg("Load evaluate model: {model_name}", model_name=evaluate_model.get_model_name()), status=m_status))
        if m_status == "failed":
            logger.error(msg)
            logger.critical_issue(content=logger.translated_msg("Load evaluate model: {model_name} failed", model_name=evaluate_model.get_model_name()))
            return

        # logger.debug(f"Total vulnerabilities created: {len(vulnerabilities)}")
        for i, v in enumerate(vulnerabilities):
            logger.debug(f"Vulnerability {i+1}: {v.get_name()}")
            if hasattr(v, 'prompts'):
                logger.debug(f"Vulnerability {i+1} prompts: {v.prompts}")

        # 解析攻击手法
        logger.status_update(statusUpdate(stepId="1", brief=logger.translated_msg("Pre-Jailbreak Parameter Parsing"), description=logger.translated_msg("Load attacks"), status="running"))
        attacks = [parse_attack(a, self.plugin_manager) for a in techniques]
        logger.status_update(statusUpdate(stepId="1", brief=logger.translated_msg("Pre-Jailbreak Parameter Parsing"), description=logger.translated_msg("Load attacks"), status="completed"))
        # logger.debug(f"Total attacks created: {len(attacks)}")

        # 获取攻击策略
        logger.debug(f"Attack selection strategy: {choice}")

        # 类型转换
        vulnerabilities = list(vulnerabilities)
        attacks = list(attacks)

        # 运行红队测试
        red_teamer = RedTeamer(simulator_model=simulator_model, evaluation_model=evaluate_model, async_mode=async_mode)
        
        # 如果指定了自定义metric，则对所有vulnerability类型使用该metric
        metric_class_path = parse_metric_class(metric) if metric else None
        if metric_class_path:
            logger.debug(f"Using metric: {metric_class_path}")
            
            # 首先检查是否是自定义插件
            custom_metric = self.plugin_manager.create_metric_instance(metric_class_path, model=evaluate_model, async_mode=async_mode)
            if custom_metric:
                red_teamer.custom_metric = custom_metric  # type: ignore
            else:
                # 如果不是自定义插件，使用内置映射
                custom_metric_class = dynamic_import(metric_class_path)
                
                # 尝试不同的初始化方式
                try:
                    # 首先尝试使用model和async_mode参数
                    custom_metric = custom_metric_class(model=evaluate_model, async_mode=async_mode)
                except TypeError:
                    try:
                        # 如果失败，尝试只使用model参数
                        custom_metric = custom_metric_class(model=evaluate_model)
                    except TypeError:
                        try:
                            # 如果还是失败，尝试使用async_mode参数
                            custom_metric = custom_metric_class(async_mode=async_mode)
                        except TypeError:
                            # 最后尝试无参数初始化
                            custom_metric = custom_metric_class()
                
                red_teamer.custom_metric = custom_metric  # type: ignore
        
        try:
            all_risk_assessments = []
            for model in models:
                model_callback = model.a_generate if async_mode else model.generate
                red_teamer.red_team(
                    model_callback=model_callback,
                    vulnerabilities=vulnerabilities,
                    attacks=attacks,
                    ignore_errors=True,
                    reuse_simulated_attacks=True,
                    choice=choice,
                    model_name=model.get_model_name()
                )
                all_risk_assessments.append((model.get_model_name(), red_teamer.risk_assessment))
        except Exception as e:
            logger.error(e)
            logger.critical_issue(content=logger.translated_msg("An error occurred during {model_name} assessment. Please try again later.", model_name=model.get_model_name()))
            return

        tool_id = uuid.uuid4().hex
        logger.new_plan_step(newPlanStep(stepId="3", title=logger.translated_msg("Generating report")))
        logger.status_update(statusUpdate(stepId="3", brief=logger.translated_msg("A.I.G is working"), description=logger.translated_msg("Generating report"), status="running"))
        logger.tool_used(toolUsed(stepId="3", tool_id=tool_id, brief=logger.translated_msg("Report in progress"), status="todo"))
        
        try:
            # content, status = red_teamer.get_risk_assessment_markdown()
            # with open(report_path, "w", encoding="utf-8") as fw:
            #     fw.write(content)
            # logger.result_update(resultUpdate(msgType="file", content=report_path, status=status))
            contents = []
            final_status = False
            df_list = []
            attachment_path = f"logs/attachment_{uuid.uuid4().hex}.csv"
            for model_name, risk_assessment in all_risk_assessments:
                content, status = red_teamer.get_risk_assessment_json(risk_assessment, model_name)
                final_status = True if final_status else status
                df_list.append(pd.read_csv(content["attachment"]))
                content["attachment"] = attachment_path
                contents.append(content)

            combined_df = pd.concat(df_list, ignore_index=True)
            combined_df.to_csv(attachment_path, index=False)
        except Exception as e:
            logger.error(e)
            logger.critical_issue(content=logger.translated_msg("An error occurred during report generated. Please try again later."))
            return

        logger.tool_used(toolUsed(stepId="3", tool_id=tool_id, tool_name="Report generated", brief=logger.translated_msg("Report generated"), status="done"))
        logger.status_update(statusUpdate(stepId="3", brief=logger.translated_msg("A.I.G is working"), description=logger.translated_msg("Generating report"), status="completed"))
        # save_report_path = red_teamer.save_risk_assessment_report() 
        # logger.info(f'Original {model_name} report save to: {save_report_path}')
        logger.result_update(resultUpdate(msgType="json", content=contents, status=final_status))
        logger.info(f'Get resultUpdate done!')