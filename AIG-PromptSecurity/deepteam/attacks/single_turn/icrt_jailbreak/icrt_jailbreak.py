from pydantic import BaseModel
from tqdm import tqdm

from deepeval.models import DeepEvalBaseLLM
from deepteam.attacks import BaseAttack
from deepteam.attacks.attack_simulator.utils import (
    generate_schema,
    a_generate_schema,
)

from deepteam.attacks.single_turn.icrt_jailbreak.schema import (
    IntentData, 
    ConceptDecompositionData, 
    SafeConstraintData,
    ConceptReassemblyData
)
from deepteam.attacks.single_turn.icrt_jailbreak.template import (
    ICRTJailbreakTemplate
)

from string import Template
import random



class ICRTJailbreak(BaseAttack):
    def __init__(
            self, 
            weight: int = 1, 
            max_retries: int = 5
        ) -> None:
        self.weight = weight
        self.max_retries = max_retries
        self.template: dict = {}
        self._load_ICRT_template()

    def _load_ICRT_template(self) -> None:
        self.template['intent_recognition'] = ICRTJailbreakTemplate.intent_recognition()
        self.template['concept_decomposition'] = ICRTJailbreakTemplate.concept_decomposition()
        self.template['safety_constraint'] = ICRTJailbreakTemplate.safety_constraint()
        self.template['concept_reassembly'] = ICRTJailbreakTemplate.concept_reassembly()
        self.template['prompt_generation'] = ICRTJailbreakTemplate.prompt_generation()

    def enhance(
        self,
        attack: str,
        simulator_model: DeepEvalBaseLLM,
    ) -> str:
        self.simulator_model = simulator_model

        for _ in tqdm(
            range(self.max_retries),
            desc="...... ☠️ ICRT Jailbreak Enhancement: Retries",
            leave=False,
        ):
            try:
                with tqdm(
                    total=5,
                    desc="...... ☠️ ICRT Jailbreak Enhancement: Jailbreaking",
                    unit="step",
                    leave=False,
                ) as pbar_jailbreak:
                    intent_recognition_template = Template(self.template['intent_recognition'])
                    intent_prompt = intent_recognition_template.substitute(user_input_here=attack)
                    intent_response: IntentData = self._generate_schema(intent_prompt, IntentData)
                    pbar_jailbreak.update(1)

                    if (intent_response.structural_intent is None) or (intent_response.harmful_behavior is None):
                        continue

                    concept_decomposition_template = Template(self.template['concept_decomposition'])
                    concept_decomposition_prompt = concept_decomposition_template.substitute(harmful_behavior=intent_response.harmful_behavior,
                                                                                            structural_intent=intent_response.structural_intent,
                                                                                            N=random.randint(7, 10))
                    concept_decomposition_response: ConceptDecompositionData = self._generate_schema(concept_decomposition_prompt, ConceptDecompositionData)
                    pbar_jailbreak.update(1)
                    if concept_decomposition_response.sub_concepts is None:
                        continue

                    safe_constraint_template = Template(self.template['safety_constraint'])
                    safe_constraint_prompt = safe_constraint_template.substitute(sub_concepts=concept_decomposition_response.sub_concepts,
                                                                                epsilon=random.randint(1, 3))
                    safe_constraint_response: SafeConstraintData = self._generate_schema(safe_constraint_prompt, SafeConstraintData)
                    pbar_jailbreak.update(1)
                    if safe_constraint_response.filtered_sub_concepts is None:
                        continue

                    concept_reassembly_template = Template(self.template['concept_reassembly'])
                    concept_reassembly_prompt = concept_reassembly_template.substitute(structural_intent=intent_response.structural_intent,
                                                                                    harmful_behavior=intent_response.harmful_behavior,
                                                                                    sub_concepts=safe_constraint_response.filtered_sub_concepts,
                                                                                    K=random.randint(min(3, len(safe_constraint_response.filtered_sub_concepts)), len(safe_constraint_response.filtered_sub_concepts)))
                    concept_reassembly_response: ConceptReassemblyData = self._generate_schema(concept_reassembly_prompt, ConceptReassemblyData)
                    pbar_jailbreak.update(1)
                    if len(concept_reassembly_response.selected_sub_concepts) < 3:
                        continue

                    goal_prompts = f'Goal: {concept_reassembly_response.selected_sub_concepts[0]}\n'
                    for i, concepts in enumerate(concept_reassembly_response.selected_sub_concepts[1:]):
                        goal_prompts += f'Additional Goal {i + 1}: {concepts}\n'
                    evil_scenario_template = Template(self.template['prompt_generation'])
                    evil_scenario_prompt = evil_scenario_template.substitute(goal_prompt=goal_prompts)
                    pbar_jailbreak.update(1)
                    return evil_scenario_prompt
            except Exception as e:
                continue

        # If all retries fail, return the original attack
        return attack

    async def a_enhance(
        self,
        attack: str,
        simulator_model: DeepEvalBaseLLM,
    ) -> str:
        self.simulator_model = simulator_model

        for _ in tqdm(
            range(self.max_retries),
            desc="...... ☠️ ICRT Jailbreak Enhancement: Retries",
            leave=False,
        ):
            try:
                with tqdm(
                    total=5,
                    desc="...... ☠️ ICRT Jailbreak Enhancement: Jailbreaking",
                    unit="step",
                    leave=False,
                ) as pbar_jailbreak:
                    intent_recognition_template = Template(self.template['intent_recognition'])
                    intent_prompt = intent_recognition_template.substitute(user_input_here=attack)
                    intent_response: IntentData = await self._a_generate_schema(intent_prompt, IntentData)
                    pbar_jailbreak.update(1)

                    if (intent_response.structural_intent is None) or (intent_response.harmful_behavior is None):
                        continue

                    concept_decomposition_template = Template(self.template['concept_decomposition'])
                    concept_decomposition_prompt = concept_decomposition_template.substitute(harmful_behavior=intent_response.harmful_behavior,
                                                                                            structural_intent=intent_response.structural_intent,
                                                                                            N=random.randint(7, 10))
                    concept_decomposition_response: ConceptDecompositionData = await self._a_generate_schema(concept_decomposition_prompt, ConceptDecompositionData)
                    pbar_jailbreak.update(1)
                    if concept_decomposition_response.sub_concepts is None:
                        continue

                    safe_constraint_template = Template(self.template['safety_constraint'])
                    safe_constraint_prompt = safe_constraint_template.substitute(sub_concepts=concept_decomposition_response.sub_concepts,
                                                                                epsilon=random.randint(1, 3))
                    safe_constraint_response: SafeConstraintData = await self._a_generate_schema(safe_constraint_prompt, SafeConstraintData)
                    pbar_jailbreak.update(1)
                    if safe_constraint_response.filtered_sub_concepts is None:
                        continue

                    concept_reassembly_template = Template(self.template['concept_reassembly'])
                    concept_reassembly_prompt = concept_reassembly_template.substitute(structural_intent=intent_response.structural_intent,
                                                                                    harmful_behavior=intent_response.harmful_behavior,
                                                                                    sub_concepts=safe_constraint_response.filtered_sub_concepts,
                                                                                    K=random.randint(min(3, len(safe_constraint_response.filtered_sub_concepts)), len(safe_constraint_response.filtered_sub_concepts)))
                    concept_reassembly_response: ConceptReassemblyData = await self._a_generate_schema(concept_reassembly_prompt, ConceptReassemblyData)
                    pbar_jailbreak.update(1)
                    if len(concept_reassembly_response.selected_sub_concepts) < 3:
                        continue

                    goal_prompts = f'Goal: {concept_reassembly_response.selected_sub_concepts[0]}\n'
                    for i, concepts in enumerate(concept_reassembly_response.selected_sub_concepts[1:]):
                        goal_prompts += f'Additional Goal {i + 1}: {concepts}\n'
                    evil_scenario_template = Template(self.template['prompt_generation'])
                    evil_scenario_prompt = evil_scenario_template.substitute(goal_prompt=goal_prompts)
                    pbar_jailbreak.update(1)
                    return evil_scenario_prompt
            except Exception as e:
                continue

        # If all retries fail, return the original attack
        return attack
        
    def _generate_schema(self, prompt: str, schema: BaseModel):
        return generate_schema(prompt, schema, self.simulator_model)

    async def _a_generate_schema(self, prompt: str, schema: BaseModel):
        return await a_generate_schema(prompt, schema, self.simulator_model)

    def get_name(self) -> str:
        return "ICRT Jailbreak"
