# Copyright (c) 2024-2026 Tencent Zhuque Lab. All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# Requirement: Any integration or derivative work must explicitly attribute
# Tencent Zhuque Lab (https://github.com/Tencent/AI-Infra-Guard) in its
# documentation or user interface, as detailed in the NOTICE file.

from pydantic import BaseModel
from .schema import SyntheticData, SyntheticDataList

from deepeval.metrics.utils import trimAndLoadJson, initialize_model
from deepeval.models import DeepEvalBaseLLM


def generate_schema(
    prompt: str,
    schema: BaseModel,
    model: DeepEvalBaseLLM = None,
) -> BaseModel:
    """
    Generate schema using the provided model.

    Args:
        prompt: The prompt to send to the model
        schema: The schema to validate the response against
        model: The model to use

    Returns:
        The validated schema object
    """
    _, using_native_model = initialize_model(model=model)

    if using_native_model:
        res, _ = model.generate(prompt, schema=schema)
        return res
    else:
        try:
            res = model.generate(prompt, schema=schema)
            return res
        except TypeError:
            res = model.generate(prompt)
            data = trimAndLoadJson(res)
            if schema == SyntheticDataList:
                data_list = [SyntheticData(**item) for item in data["data"]]
                return SyntheticDataList(data=data_list)
            else:
                return schema(**data)


async def a_generate_schema(
    prompt: str,
    schema: BaseModel,
    model: DeepEvalBaseLLM = None,
) -> BaseModel:
    """
    Asynchronously generate schema using the provided model.

    Args:
        prompt: The prompt to send to the model
        schema: The schema to validate the response against
        model: The model to use

    Returns:
        The validated schema object
    """
    _, using_native_model = initialize_model(model=model)

    if using_native_model:
        res, _ = await model.a_generate(prompt, schema=schema)
        return res
    else:
        try:
            res = await model.a_generate(prompt, schema=schema)
            return res
        except TypeError:
            res = await model.a_generate(prompt)
            data = trimAndLoadJson(res)
            if schema == SyntheticDataList:
                data_list = [SyntheticData(**item) for item in data["data"]]
                return SyntheticDataList(data=data_list)
            else:
                return schema(**data)
