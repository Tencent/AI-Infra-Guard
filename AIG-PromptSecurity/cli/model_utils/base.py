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

from abc import abstractmethod
from typing import Tuple
from deepeval.models.base_model import DeepEvalBaseLLM
import asyncio

class BaseLLM(DeepEvalBaseLLM):
    def __init__(self, model_name: str, base_url: str, api_key: str, max_concurrent: int):
        self.model_name = model_name
        self.base_url = base_url
        self.api_key = api_key
        self.max_concurrent = max_concurrent
        self.semaphore = asyncio.Semaphore(max_concurrent)

    @abstractmethod
    def load_model(self, *args, **kwargs):
        """Loads a model, that will be responsible for scoring.

        Returns:
            A model object
        """
        pass
    
    @abstractmethod
    def test_model_connection(self) -> Tuple[bool, str]:
        """
        Check if the specified model is properly connected and responsive.

        Returns:
            Tuple[bool, str]: 
                - bool: True if the model is successfully connected, False otherwise.
                - str: Success message if connected, or detailed error information if connection failed.
        
        Example:
            >>> is_connected, message = test_model_connection(model)
            >>> print(f"Connected: {is_connected}, Message: {message}")
            Connected: True, Message: Model responded successfully in 200ms
        """
        pass

    @abstractmethod
    def generate(self, prompt: str = None, messages: list = None, *args, **kwargs) -> str:
        """Runs the model to output LLM response.

        Returns:
            A string.
        """
        pass

    @abstractmethod
    async def a_generate(self, prompt: str = None, messages: list = None, *args, **kwargs) -> str:
        """Runs the model to output LLM response.

        Returns:
            A string.
        """
        async with self.semaphore:
            pass

    @abstractmethod
    def get_model_name(self, *args, **kwargs) -> str:
        pass