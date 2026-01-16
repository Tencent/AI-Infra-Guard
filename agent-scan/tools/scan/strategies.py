"""
Test case generation strategies for security scanning.

This module provides different strategies for generating test cases,
including static prompts from files and dynamic generation using LLMs.
"""

import os
import uuid
import yaml
from abc import ABC, abstractmethod
from typing import Generator, List, Optional, Dict, Any

from .models import TestCase


class BaseStrategy(ABC):
    """
    Abstract base class for test case generation strategies.
    
    Strategies generate test cases that will be executed against target agents
    to detect security vulnerabilities.
    """
    
    @abstractmethod
    def generate(self) -> Generator[TestCase, None, None]:
        """
        Generate test cases.
        
        Yields:
            TestCase objects ready for execution
        """
        pass


class StaticDatasetStrategy(BaseStrategy):
    """
    Generates test cases from a static list of prompts.
    
    This strategy loads prompts from either an explicit list or a YAML file
    containing categorized attack prompts. It's useful for reproducible
    testing with known attack vectors.
    """
    
    def __init__(
        self,
        prompts: Optional[List[str]] = None,
        prompts_file: Optional[str] = None,
        category_filter: Optional[List[str]] = None
    ):
        """
        Initialize the strategy with static prompts.
        
        Args:
            prompts: Explicit list of prompt strings (highest priority)
            prompts_file: Path to YAML file with prompts or categories
            category_filter: Optional list of category names to include
        
        The YAML file can have two formats:
            1. Legacy format: prompts: [string, ...]
            2. Categorized format: categories: {name: [string, ...]}
        
        Raises:
            FileNotFoundError: If prompts_file doesn't exist
            ValueError: If no valid prompts are found or file format is invalid
        """
        if prompts is not None:
            self.prompts = prompts
            self.categories = {}
            return
        
        if prompts_file:
            if not os.path.exists(prompts_file):
                raise FileNotFoundError(f"Static prompts file not found: {prompts_file}")
            
            with open(prompts_file, "r", encoding="utf-8") as f:
                try:
                    data = yaml.safe_load(f) or {}
                except yaml.YAMLError as e:
                    raise ValueError(f"Invalid YAML in prompts_file: {prompts_file}: {e}") from e
            
            file_prompts: List[str] = []
            self.categories: Dict[str, List[str]] = {}
            
            # Backward compatible: prompts: [ ... ]
            raw_prompts = data.get("prompts", [])
            if raw_prompts:
                if not isinstance(raw_prompts, list) or not all(isinstance(p, str) for p in raw_prompts):
                    raise ValueError(f"Invalid prompts format in {prompts_file}, expected: prompts: [str, ...]")
                file_prompts.extend(raw_prompts)
            
            # New schema: categories: { <risk_type>: [ ... ] }
            categories = data.get("categories")
            if categories is not None:
                if not isinstance(categories, dict):
                    raise ValueError(f"Invalid categories format in {prompts_file}, expected: categories: {{name: [str, ...]}}")
                
                for category_name, items in categories.items():
                    if not isinstance(items, list) or not all(isinstance(p, str) for p in items):
                        raise ValueError(f"Invalid categories item format in {prompts_file}, expected list[str]")
                    
                    # Apply category filter if specified
                    if category_filter is None or category_name in category_filter:
                        self.categories[category_name] = items
                        file_prompts.extend(items)
            
            # Normalize and deduplicate (preserve order)
            seen = set()
            normalized: List[str] = []
            for raw_prompt in file_prompts:
                stripped_prompt = (raw_prompt or "").strip()
                if not stripped_prompt or stripped_prompt in seen:
                    continue
                seen.add(stripped_prompt)
                normalized.append(stripped_prompt)
            
            if not normalized:
                raise ValueError(f"No prompts found in {prompts_file}. Provide prompts: [...] or categories: {{...}}")
            
            self.prompts = normalized
            return
        
        # No fallback prompts: explicit configuration required
        raise ValueError(
            "No prompts provided. Either supply static prompts via 'prompts', or set a valid 'prompts_file' path."
        )
    
    def generate(self) -> Generator[TestCase, None, None]:
        """
        Generate test cases from static prompts.
        
        Yields:
            TestCase objects with unique IDs and metadata
        """
        for prompt in self.prompts:
            # Try to determine category from prompts
            category = "general"
            for cat_name, cat_prompts in self.categories.items():
                if prompt in cat_prompts:
                    category = cat_name
                    break
            
            yield TestCase(
                id=str(uuid.uuid4()),
                prompt=prompt,
                metadata={
                    "strategy": "static",
                    "category": category
                }
            )


class DynamicGenerationStrategy(BaseStrategy):
    """
    Generates test cases dynamically using an attacker LLM.
    
    This strategy uses an LLM to generate context-aware attack prompts
    based on a target topic or vulnerability type. It's useful for
    discovering novel attack vectors.
    """
    
    def __init__(
        self,
        topic: str = "data leakage",
        count: int = 5,
        attacker_config: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize the dynamic generation strategy.
        
        Args:
            topic: Topic or vulnerability type to generate tests for
            count: Number of test cases to generate
            attacker_config: Configuration for the attacker LLM (to be integrated)
        """
        self.topic = topic
        self.count = count
        self.attacker_config = attacker_config or {}
        # TODO: Integrate with agent interaction layer when available
    
    def generate(self) -> Generator[TestCase, None, None]:
        """
        Generate test cases dynamically using an LLM.
        
        Yields:
            TestCase objects generated by the attacker LLM
        """
        # TODO: Implement when agent interaction layer is ready
        yield from []  # Empty generator until integration is ready


class HybridStrategy(BaseStrategy):
    """
    Combines multiple strategies for comprehensive testing.
    
    This strategy executes multiple sub-strategies in sequence,
    allowing you to combine static prompts with dynamic generation.
    """
    
    def __init__(self, strategies: List[BaseStrategy]):
        """
        Initialize with a list of strategies to execute.
        
        Args:
            strategies: List of strategy instances to combine
        """
        self.strategies = strategies
    
    def generate(self) -> Generator[TestCase, None, None]:
        """
        Generate test cases from all sub-strategies.
        
        Yields:
            TestCase objects from each strategy in sequence
        """
        for strategy in self.strategies:
            yield from strategy.generate()
