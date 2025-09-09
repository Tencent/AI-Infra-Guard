import copy
import random
import asyncio
from tqdm import tqdm
from pydantic import BaseModel
from typing import List, Optional, Union
import inspect
from cli.aig_logger import logger
from cli.aig_logger import (
    newPlanStep, statusUpdate, toolUsed, actionLog, resultUpdate
)
import uuid

from deepeval.models import DeepEvalBaseLLM
from deepeval.metrics.utils import initialize_model, trimAndLoadJson

from deepteam.attacks import BaseAttack
from deepteam.vulnerabilities import BaseVulnerability, CustomPrompt, MultiDatasetVulnerability
from deepteam.vulnerabilities.types import VulnerabilityType
from deepteam.attacks.multi_turn.types import CallbackType
from deepteam.attacks.attack_simulator.template import AttackSimulatorTemplate
from deepteam.attacks.attack_simulator.schema import SyntheticDataList


class SimulatedAttack(BaseModel):
    vulnerability: str
    vulnerability_type: VulnerabilityType
    input: Optional[str] = None
    attack_method: Optional[str] = None
    error: Optional[str] = None


class AttackSimulator:
    model_callback: Union[CallbackType, None] = None
    max_concurrent = 10

    def __init__(
        self,
        purpose: str,
        simulator_model: Optional[Union[str, DeepEvalBaseLLM]] = None,
    ):
        # Initialize models and async mode
        self.purpose = purpose
        self.simulator_model, self.using_native_model = initialize_model(
            simulator_model
        )

        # Define list of attacks and unaligned vulnerabilities
        self.simulated_attacks: List[SimulatedAttack] = []

    ##################################################
    ### Generating Attacks ###########################
    ##################################################

    def simulate(
        self,
        attacks_per_vulnerability_type: int,
        vulnerabilities: List[BaseVulnerability],
        attacks: List[BaseAttack],
        ignore_errors: bool,
        choice: str = "random",  # 新增参数：random 或 serial
    ) -> List[SimulatedAttack]:
        # Simulate unenhanced attacks for each vulnerability
        baseline_attacks: List[SimulatedAttack] = []
        num_vulnerabilities = len(vulnerabilities)
        num_vulnerability_types = sum(
            len(v.get_types()) for v in vulnerabilities
        )
        pbar = tqdm(
            vulnerabilities,
            desc=f"💥 Generating {num_vulnerability_types * attacks_per_vulnerability_type} attacks (for {num_vulnerability_types} vulnerability types across {num_vulnerabilities} vulnerability(s))",
        )
        logger.status_update(statusUpdate(stepId="2", brief=logger.translated_msg("Jailbreaking"), description=logger.translated_msg("Generating attacks"), status="running"))
        
        tool_id = uuid.uuid4().hex
        logger.tool_used(toolUsed(stepId="2", tool_id=tool_id, brief=logger.translated_msg(
            "Simulating {num_vulnerabilities} attacks", num_vulnerabilities=num_vulnerabilities
        ), status="todo"))

        for idx, vulnerability in enumerate(pbar):
            logger.tool_used(toolUsed(stepId="2", tool_id=tool_id, brief=logger.translated_msg(
                "Simulating {idx} / {num_vulnerabilities} attacks", idx=idx+1, num_vulnerabilities=num_vulnerabilities
            ), status="doing"))

            baseline_attacks.extend(
                self.simulate_baseline_attacks(
                    attacks_per_vulnerability_type=attacks_per_vulnerability_type,
                    vulnerability=vulnerability,
                    ignore_errors=ignore_errors,
                )
            )
        logger.tool_used(toolUsed(stepId="2", tool_id=tool_id, tool_name="Simulate baseline attacks", brief=logger.translated_msg(
            "Simulating {length} attacks done", length=len(vulnerabilities)
        ), status="done"))

        logger.status_update(statusUpdate(stepId="2", brief=logger.translated_msg("Jailbreaking"), description=logger.translated_msg("Generating attacks"), status="completed"))

        # Enhance attacks by sampling from the provided distribution
        enhanced_attacks: List[SimulatedAttack] = []
        if choice == "serial":
            unpack_attacks = [attacks]
        elif choice == "parallel":
            unpack_attacks = attacks
        else:
            attack_weights = [attack.weight for attack in attacks]
            unpack_attacks = random.choices(attacks, weights=attack_weights, k=1)
        num_baseline_attacks = len(baseline_attacks) * len(unpack_attacks)
        pbar = tqdm(
            total=num_baseline_attacks,
            desc=f"✨ Simulating {num_vulnerability_types * attacks_per_vulnerability_type} attacks (using {len(attacks)} method(s))",
        )

        logger.status_update(statusUpdate(stepId="2", brief=logger.translated_msg("Jailbreaking"), description=logger.translated_msg(
            "Enhance {num_baseline_attacks} attacks", num_baseline_attacks=num_baseline_attacks
        ), status="running"))
        
        tool_id = uuid.uuid4().hex
        logger.tool_used(toolUsed(stepId="2", tool_id=tool_id, tool_name="Enhance attacks", brief=logger.translated_msg(
            "Enhance {num_baseline_attacks} attacks", num_baseline_attacks=num_baseline_attacks
        ), status="todo"))

        for index, (baseline_attack, unpack_attack) in enumerate(
            (baseline_attack, unpack_attack) 
            for baseline_attack in baseline_attacks 
            for unpack_attack in unpack_attacks
        ):
            logger.tool_used(toolUsed(stepId="2", tool_id=tool_id, brief=logger.translated_msg(
                "Simulating {idx} / {num_baseline_attacks} attacks", idx=index+1, num_baseline_attacks=num_baseline_attacks
            ), status="doing"))
            if choice == "serial":
                # 串行嵌套攻击：按顺序应用所有攻击方法
                enhanced_attack = self.enhance_attack_serial(
                    attacks=unpack_attack,
                    simulated_attack=baseline_attack,
                    ignore_errors=ignore_errors,
                )
            else:
                enhanced_attack = self.enhance_attack(
                    attack=unpack_attack,
                    simulated_attack=baseline_attack,
                    ignore_errors=ignore_errors,
                )
            enhanced_attacks.append(enhanced_attack)
            pbar.update(1)

        logger.tool_used(toolUsed(stepId="2", tool_id=tool_id, tool_name="Enhance attacks", brief=logger.translated_msg(
            "Enhance {num_baseline_attacks} attacks done", num_baseline_attacks=num_baseline_attacks
        ), status="done"))

        logger.status_update(statusUpdate(stepId="2", brief=logger.translated_msg("Jailbreaking"), description=logger.translated_msg(
            "Enhance {num_baseline_attacks} attacks", num_baseline_attacks=num_baseline_attacks
        ), status="completed"))

        self.simulated_attacks.extend(enhanced_attacks)

        return enhanced_attacks

    async def a_simulate(
        self,
        attacks_per_vulnerability_type: int,
        vulnerabilities: List[BaseVulnerability],
        attacks: List[BaseAttack],
        ignore_errors: bool,
        choice: str = "random",  # 新增参数：random 或 serial
    ) -> List[SimulatedAttack]:
        self.semaphore = asyncio.Semaphore(self.max_concurrent)

        # Simulate unenhanced attacks for each vulnerability
        baseline_attacks: List[SimulatedAttack] = []
        num_vulnerabilities = len(vulnerabilities)
        num_vulnerability_types = sum(
            len(v.get_types()) for v in vulnerabilities
        )
        pbar = tqdm(
            vulnerabilities,
            desc=f"💥 Generating {num_vulnerability_types * attacks_per_vulnerability_type} attacks (for {num_vulnerability_types} vulnerability types across {num_vulnerabilities} vulnerability(s))",
        )
        tool_id = uuid.uuid4().hex
        logger.status_update(statusUpdate(stepId="2", brief=logger.translated_msg("Jailbreaking"), description=logger.translated_msg("Generating attacks"), status="running"))
        logger.tool_used(toolUsed(stepId="2", tool_id=tool_id, brief=logger.translated_msg(
            "Simulating {num_vulnerabilities} attacks", num_vulnerabilities=num_vulnerabilities
        ), status="todo"))
        
        async def throttled_simulate_baseline_attack(vulnerability):
            result = await self.a_simulate_baseline_attacks(
                attacks_per_vulnerability_type=attacks_per_vulnerability_type,
                vulnerability=vulnerability,
                ignore_errors=ignore_errors,
            )
            return result

        simulate_tasks = [
            throttled_simulate_baseline_attack(vulnerability) for vulnerability in vulnerabilities
        ]
        
        for completed, coro in enumerate(asyncio.as_completed(simulate_tasks), 1):
            result = await(coro)
            baseline_attacks.extend(result)
            logger.tool_used(toolUsed(stepId="2", tool_id=tool_id, brief=logger.translated_msg(
                "Simulating {idx} / {num_vulnerabilities} attacks", idx=completed, num_vulnerabilities=num_vulnerabilities
            ), status="doing"))
            pbar.update(1)
        
        logger.tool_used(toolUsed(stepId="2", tool_id=tool_id, tool_name="Simulate baseline attacks", brief=logger.translated_msg(
            "Simulating {num_vulnerabilities} attacks done", num_vulnerabilities=num_vulnerabilities
        ), status="done"))
        logger.status_update(statusUpdate(stepId="2", brief=logger.translated_msg("Jailbreaking"), description=logger.translated_msg("Generating attacks"), status="completed"))
        pbar.close()

        # Enhance attacks by sampling from the provided distribution
        enhanced_attacks: List[SimulatedAttack] = []
        if choice == "serial":
            unpack_attacks = [attacks]
        elif choice == "parallel":
            unpack_attacks = attacks
        else:
            attack_weights = [attack.weight for attack in attacks]
            unpack_attacks = random.choices(attacks, weights=attack_weights, k=1)
        num_baseline_attacks = len(baseline_attacks) * len(unpack_attacks)
        pbar = tqdm(
            total=num_baseline_attacks,
            desc=f"✨ Simulating {num_vulnerability_types * attacks_per_vulnerability_type} attacks (using {len(attacks)} method(s))",
        )
            
        async def throttled_attack_method(
            unpack_attack: List[BaseAttack] | BaseAttack,
            baseline_attack: SimulatedAttack,
        ):
            async with self.semaphore:
                if choice == "serial":
                    # 串行嵌套攻击：按顺序应用所有攻击方法
                    result = await self.a_enhance_attack_serial(
                        attacks=unpack_attack,
                        simulated_attack=baseline_attack,
                        ignore_errors=ignore_errors,
                    )
                else:
                    result = await self.a_enhance_attack(
                        attack=unpack_attack,
                        simulated_attack=baseline_attack,
                        ignore_errors=ignore_errors,
                    )

                return result
        
        logger.status_update(statusUpdate(stepId="2", brief=logger.translated_msg("Jailbreaking"), description=logger.translated_msg(
            "Enhance {num_baseline_attacks} attacks", num_baseline_attacks=num_baseline_attacks
        ), status="running"))

        tasks = [
            throttled_attack_method(unpack_attack, baseline_attack) for baseline_attack in baseline_attacks for unpack_attack in unpack_attacks
        ]

        logger.tool_used(toolUsed(stepId="2", tool_id=tool_id, tool_name="Enhance attacks", brief=logger.translated_msg(
            "Enhance {num_baseline_attacks} attacks", num_baseline_attacks=num_baseline_attacks
        ), status="todo"))

        for completed, coro in enumerate(asyncio.as_completed(tasks), 1):
            logger.tool_used(toolUsed(stepId="2", tool_id=tool_id, brief=logger.translated_msg(
                "Enhance {idx} / {num_baseline_attacks} attacks", idx=completed, num_baseline_attacks=num_baseline_attacks
            ), status="doing"))
            result = await coro
            enhanced_attacks.append(result)
            pbar.update(1)
        
        logger.tool_used(toolUsed(stepId="2", tool_id=tool_id, tool_name="Enhance attacks", brief=logger.translated_msg(
            "Enhance {num_baseline_attacks} attacks done", num_baseline_attacks=num_baseline_attacks
        ), status="done"))
        
        logger.status_update(statusUpdate(stepId="2", brief=logger.translated_msg("Jailbreaking"), description=logger.translated_msg(
            "Enhance {num_baseline_attacks} attacks", num_baseline_attacks=num_baseline_attacks
        ), status="completed"))
        pbar.close()

        # Store the simulated and enhanced attacks
        self.simulated_attacks.extend(enhanced_attacks)

        return enhanced_attacks

    ##################################################
    ### Simulating Base (Unenhanced) Attacks #########
    ##################################################

    def simulate_baseline_attacks(
        self,
        attacks_per_vulnerability_type: int,
        vulnerability: BaseVulnerability,
        ignore_errors: bool,
    ) -> List[SimulatedAttack]:
        baseline_attacks: List[SimulatedAttack] = []

        for vulnerability_type in vulnerability.get_types():
            try:
                if isinstance(vulnerability, CustomPrompt) or isinstance(vulnerability, MultiDatasetVulnerability):
                    local_attacks = vulnerability.custom_prompt
                else:
                    local_attacks = self.simulate_local_attack(
                        self.purpose,
                        vulnerability_type,
                        attacks_per_vulnerability_type,
                        (
                            vulnerability.custom_prompt
                            if hasattr(vulnerability, "custom_prompt")
                            else None
                        ),
                    )
                baseline_attacks.extend(
                    [
                        SimulatedAttack(
                            vulnerability=vulnerability.get_name(),
                            vulnerability_type=vulnerability_type,
                            input=local_attack,
                        )
                        for local_attack in local_attacks
                    ]
                )
            except Exception as e:
                if ignore_errors:
                    for _ in range(attacks_per_vulnerability_type):
                        baseline_attacks.append(
                            SimulatedAttack(
                                vulnerability=vulnerability.get_name(),
                                vulnerability_type=vulnerability_type,
                                error=f"Error simulating adversarial attacks: {str(e)}",
                            )
                        )
                else:
                    raise
        return baseline_attacks

    async def a_simulate_baseline_attacks(
        self,
        attacks_per_vulnerability_type: int,
        vulnerability: BaseVulnerability,
        ignore_errors: bool,
    ) -> List[SimulatedAttack]:
        baseline_attacks: List[SimulatedAttack] = []
        for vulnerability_type in vulnerability.get_types():
            try:
                if isinstance(vulnerability, CustomPrompt) or isinstance(vulnerability, MultiDatasetVulnerability):
                    local_attacks = vulnerability.custom_prompt
                else:
                    local_attacks = await self.a_simulate_local_attack(
                        self.purpose,
                        vulnerability_type,
                        attacks_per_vulnerability_type,
                        (
                            vulnerability.custom_prompt
                            if hasattr(vulnerability, "custom_prompt")
                            else None
                        ),
                    )

                baseline_attacks.extend(
                    [
                        SimulatedAttack(
                            vulnerability=vulnerability.get_name(),
                            vulnerability_type=vulnerability_type,
                            input=local_attack,
                        )
                        for local_attack in local_attacks
                    ]
                )
            except Exception as e:
                if ignore_errors:
                    for _ in range(attacks_per_vulnerability_type):
                        baseline_attacks.append(
                            SimulatedAttack(
                                vulnerability=vulnerability.get_name(),
                                vulnerability_type=vulnerability_type,
                                error=f"Error simulating adversarial attacks: {str(e)}",
                            )
                        )
                else:
                    raise
        return baseline_attacks

    ##################################################
    ### Enhance attacks ##############################
    ##################################################

    def enhance_attack(
        self,
        attack: BaseAttack,
        simulated_attack: SimulatedAttack,
        ignore_errors: bool,
    ):
        simulated_attack = copy.deepcopy(simulated_attack)
        attack_input = simulated_attack.input
        if attack_input is None:
            return simulated_attack

        simulated_attack.attack_method = attack.get_name()
        sig = inspect.signature(attack.enhance)
        try:
            if (
                "simulator_model" in sig.parameters
                and "model_callback" in sig.parameters
            ):
                simulated_attack.input = attack.enhance(
                    attack=attack_input,
                    simulator_model=self.simulator_model,
                    model_callback=self.model_callback,
                )
            elif "simulator_model" in sig.parameters:
                simulated_attack.input = attack.enhance(
                    attack=attack_input,
                    simulator_model=self.simulator_model,
                )
            elif "model_callback" in sig.parameters:
                simulated_attack.input = attack.enhance(
                    attack=attack_input,
                    model_callback=self.model_callback,
                )
            else:
                simulated_attack.input = attack.enhance(attack=attack_input)
        except Exception as e:
            if ignore_errors:
                simulated_attack.error = "Error enhancing attack"
                return simulated_attack
            else:
                raise

        return simulated_attack

    def enhance_attack_serial(
        self,
        attacks: List[BaseAttack],
        simulated_attack: SimulatedAttack,
        ignore_errors: bool,
    ):
        """
        串行嵌套攻击：按顺序应用所有攻击方法
        例如：Base64(ROT13(原始攻击))
        """
        attack_input = simulated_attack.input
        if attack_input is None:
            return simulated_attack

        # 记录所有使用的攻击方法名称
        attack_methods = []
        current_input = attack_input
        
        logger.debug(f"Starting serial attack enhancement")
        logger.debug(f"Original input: {attack_input[:100]}...")
        logger.debug(f"Number of attacks to apply: {len(attacks)}")

        try:
            for i, attack in enumerate(attacks):
                attack_name = attack.get_name()
                attack_methods.append(attack_name)
                
                logger.debug(f"Step {i+1}/{len(attacks)} - Applying {attack_name}")
                logger.debug(f"Input before {attack_name}: {current_input[:100]}...")
                
                sig = inspect.signature(attack.enhance)
                
                # 根据攻击方法的参数需求调用
                if ("simulator_model" in sig.parameters and "model_callback" in sig.parameters):
                    logger.debug(f"Calling {attack_name}.enhance with simulator_model and model_callback")
                    current_input = attack.enhance(
                        attack=current_input,
                        simulator_model=self.simulator_model,
                        model_callback=self.model_callback,
                    )
                elif "simulator_model" in sig.parameters:
                    logger.debug(f"Calling {attack_name}.enhance with simulator_model")
                    current_input = attack.enhance(
                        attack=current_input,
                        simulator_model=self.simulator_model,
                    )
                elif "model_callback" in sig.parameters:
                    logger.debug(f"Calling {attack_name}.enhance with model_callback")
                    current_input = attack.enhance(
                        attack=current_input,
                        model_callback=self.model_callback,
                    )
                else:
                    logger.debug(f"Calling {attack_name}.enhance with attack parameter only")
                    current_input = attack.enhance(attack=current_input)
                
                logger.debug(f"Output after {attack_name}: {current_input[:100]}...")
                logger.debug(f"Input length changed to {len(current_input)}")

            # 更新模拟攻击对象
            simulated_attack.input = current_input
            simulated_attack.attack_method = " + ".join(attack_methods)  # 记录所有攻击方法
            
            logger.debug(f"Final attack method: {simulated_attack.attack_method}")
            logger.debug(f"Final input: {current_input[:100]}...")
            logger.debug(f"Serial attack enhancement completed successfully")
            
        except Exception as e:
            logger.debug(f"Error in serial attack enhancement: {str(e)}")
            if ignore_errors:
                simulated_attack.error = f"Error in serial attack enhancement: {str(e)}"
                return simulated_attack
            else:
                raise

        return simulated_attack

    async def a_enhance_attack(
        self,
        attack: BaseAttack,
        simulated_attack: SimulatedAttack,
        ignore_errors: bool,
    ):
        simulated_attack = copy.deepcopy(simulated_attack)
        attack_input = simulated_attack.input
        if attack_input is None:
            return simulated_attack

        simulated_attack.attack_method = attack.get_name()
        sig = inspect.signature(attack.a_enhance)

        try:
            if (
                "simulator_model" in sig.parameters
                and "model_callback" in sig.parameters
            ):
                simulated_attack.input = await attack.a_enhance(
                    attack=attack_input,
                    simulator_model=self.simulator_model,
                    model_callback=self.model_callback,
                )
            elif "simulator_model" in sig.parameters:
                simulated_attack.input = await attack.a_enhance(
                    attack=attack_input,
                    simulator_model=self.simulator_model,
                )
            elif "model_callback" in sig.parameters:
                simulated_attack.input = await attack.a_enhance(
                    attack=attack_input,
                    model_callback=self.model_callback,
                )
            else:
                simulated_attack.input = await attack.a_enhance(
                    attack=attack_input
                )
        except:
            if ignore_errors:
                simulated_attack.error = "Error enhancing attack"
                return simulated_attack
            else:
                raise

        return simulated_attack

    async def a_enhance_attack_serial(
        self,
        attacks: List[BaseAttack],
        simulated_attack: SimulatedAttack,
        ignore_errors: bool,
    ):
        """
        异步串行嵌套攻击：按顺序应用所有攻击方法
        例如：Base64(ROT13(原始攻击))
        """
        attack_input = simulated_attack.input
        if attack_input is None:
            return simulated_attack

        # 记录所有使用的攻击方法名称
        attack_methods = []
        current_input = attack_input
        
        logger.debug(f"Starting async serial attack enhancement")
        logger.debug(f"Original input: {attack_input[:100]}...")
        logger.debug(f"Number of attacks to apply: {len(attacks)}")

        try:
            for i, attack in enumerate(attacks):
                attack_name = attack.get_name()
                attack_methods.append(attack_name)
                
                logger.debug(f"Step {i+1}/{len(attacks)} - Applying {attack_name}")
                logger.debug(f"Input before {attack_name}: {current_input[:100]}...")
                
                sig = inspect.signature(attack.enhance)
                
                # 根据攻击方法的参数需求调用
                if ("simulator_model" in sig.parameters and "model_callback" in sig.parameters):
                    logger.debug(f"Calling {attack_name}.enhance with simulator_model and model_callback")
                    current_input = attack.enhance(
                        attack=current_input,
                        simulator_model=self.simulator_model,
                        model_callback=self.model_callback,
                    )
                elif "simulator_model" in sig.parameters:
                    logger.debug(f"Calling {attack_name}.enhance with simulator_model")
                    current_input = attack.enhance(
                        attack=current_input,
                        simulator_model=self.simulator_model,
                    )
                elif "model_callback" in sig.parameters:
                    logger.debug(f"Calling {attack_name}.enhance with model_callback")
                    current_input = attack.enhance(
                        attack=current_input,
                        model_callback=self.model_callback,
                    )
                else:
                    logger.debug(f"Calling {attack_name}.enhance with attack parameter only")
                    current_input = attack.enhance(attack=current_input)
                
                logger.debug(f"Output after {attack_name}: {current_input[:100]}...")
                logger.debug(f"Input length changed from {len(attack_input) if i == 0 else len(await attacks[i-1].enhance(attack_input))} to {len(current_input)}")

            # 更新模拟攻击对象
            simulated_attack.input = current_input
            simulated_attack.attack_method = " + ".join(attack_methods)  # 记录所有攻击方法
            
            logger.debug(f"Final attack method: {simulated_attack.attack_method}")
            logger.debug(f"Final input: {current_input[:100]}...")
            logger.debug(f"Async serial attack enhancement completed successfully")
            
        except Exception as e:
            logger.debug(f"Error in async serial attack enhancement: {str(e)}")
            if ignore_errors:
                simulated_attack.error = f"Error in serial attack enhancement: {str(e)}"
                return simulated_attack
            else:
                raise

        return simulated_attack

    def simulate_local_attack(
        self,
        purpose: str,
        vulnerability_type: VulnerabilityType,
        num_attacks: int,
        custom_prompt: Optional[str] = None,
    ) -> List[str]:
        """Simulate attacks using local LLM model"""
        # Get the appropriate prompt template from AttackSimulatorTemplate
        prompt = AttackSimulatorTemplate.generate_attacks(
            max_goldens=num_attacks,
            vulnerability_type=vulnerability_type,
            purpose=purpose,
            custom_prompt=custom_prompt,
        )
        if self.using_native_model:
            # For models that support schema validation directly
            res, _ = self.simulator_model.generate(
                prompt, schema=SyntheticDataList
            )
            return [item.input for item in res.data]
        else:
            try:
                res: SyntheticDataList = self.simulator_model.generate(
                    prompt, schema=SyntheticDataList
                )
                return [item.input for item in res.data]
            except TypeError:
                res = self.simulator_model.generate(prompt)
                data = trimAndLoadJson(res)
                return [item["input"] for item in data["data"]]

    async def a_simulate_local_attack(
        self,
        purpose: str,
        vulnerability_type: VulnerabilityType,
        num_attacks: int,
        custom_prompt: Optional[str] = None,
    ) -> List[str]:
        """Asynchronously simulate attacks using local LLM model"""

        prompt = AttackSimulatorTemplate.generate_attacks(
            max_goldens=num_attacks,
            vulnerability_type=vulnerability_type,
            purpose=purpose,
            custom_prompt=custom_prompt,
        )

        if self.using_native_model:
            # For models that support schema validation directly
            res, _ = await self.simulator_model.a_generate(
                prompt, schema=SyntheticDataList
            )
            return [item.input for item in res.data]
        else:
            try:
                res: SyntheticDataList = await self.simulator_model.a_generate(
                    prompt, schema=SyntheticDataList
                )
                return [item.input for item in res.data]
            except TypeError:
                res = await self.simulator_model.a_generate(prompt)
                data = trimAndLoadJson(res)
                return [item["input"] for item in data["data"]]
