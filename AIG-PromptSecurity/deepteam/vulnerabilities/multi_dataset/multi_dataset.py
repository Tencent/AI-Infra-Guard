import os
import json
import pandas as pd
import random
from typing import List, Optional, Union, Dict, Any

from deepteam.vulnerabilities.custom import CustomVulnerability
from deepteam.vulnerabilities.multi_dataset import MultiDatasetVulnerabilityType

class MultiDatasetVulnerability(CustomVulnerability):
    """
    多数据集漏洞类，从CSV文件中读取prompt并随机筛选
    使用pandas实现，支持更多高级功能
    """
    
    def __init__(self, csv_file: str = "jb-top100.csv", num_prompts: int = 10, random_seed: Optional[int] = None, 
                 prompt_column: Optional[str] = None, filter_conditions: Optional[Dict[str, Any]] = None):
        """
        初始化多数据集漏洞
        
        Args:
            csv_file: CSV文件路径，默认为同目录下的 jb-top100.csv
            num_prompts: 要筛选的prompt数量，默认为10
            random_seed: 随机种子，用于可重现的结果
            prompt_column: 指定prompt列名，如果为None则自动检测
            filter_conditions: 过滤条件字典，如{"category": "harmful", "language": "zh"}
        """
        # 设置随机种子
        if random_seed is not None:
            random.seed(random_seed)
            # 同时设置pandas的随机种子
            pd.util.hash_pandas_object = lambda obj: hash(tuple(obj))
        
        # 获取CSV文件的完整路径
        if not os.path.isabs(csv_file):
            csv_file = os.path.join(os.path.dirname(__file__), csv_file)
        
        # 加载prompts和元数据
        self.prompts, self.metadata = self._load_from_csv(csv_file, num_prompts, prompt_column, filter_conditions)
        # print(f"DEBUG: MultiDatasetVulnerability loaded {len(self.prompts)} prompts from {csv_file}")
        
        # 调用父类初始化
        super().__init__(
            name="Multi Dataset Vulnerability",
            types=[type for type in MultiDatasetVulnerabilityType],
            custom_prompt=self.prompts
        )
    
    def _load_from_csv(self, csv_file: str, num_prompts: int, prompt_column: Optional[str], 
                       filter_conditions: Optional[Dict[str, Any]]) -> tuple[List[str], List[Dict[str, Any]]]:
        """从CSV文件加载prompt列表和元数据，使用pandas实现"""
        try:
            if not os.path.exists(csv_file):
                raise FileNotFoundError(f"CSV file not found: {csv_file}")
            
            # 使用pandas读取CSV文件
            df = pd.read_csv(csv_file, encoding='utf-8')
            
            if df.empty:
                raise ValueError(f"No data found in CSV file: {csv_file}")
            
            # 应用过滤条件
            if filter_conditions:
                for column, value in filter_conditions.items():
                    if column in df.columns:
                        if isinstance(value, (list, tuple)):
                            df = df[df[column].isin(value)]
                        else:
                            df = df[df[column] == value]
                        # print(f"DEBUG: Applied filter {column}={value}, remaining rows: {len(df)}")
            
            if df.empty:
                raise ValueError(f"No data remaining after applying filters")
            
            # 确定prompt列
            if prompt_column:
                if prompt_column not in df.columns:
                    raise ValueError(f"Specified prompt column '{prompt_column}' not found in CSV")
                prompt_col = prompt_column
            else:
                # 自动检测prompt列
                prompt_col = self._detect_prompt_column(df)
            
            # 清理数据：移除空值和重复值
            df = df.dropna(subset=[prompt_col])
            df = df.drop_duplicates(subset=[prompt_col])
            
            if df.empty:
                raise ValueError(f"No valid prompts found after cleaning")
            
            # 随机筛选指定数量的prompt
            if len(df) <= num_prompts:
                selected_df = df
                print(f"WARNING: Requested {num_prompts} prompts but only {len(df)} available")
            else:
                selected_df = df.sample(n=num_prompts, random_state=random.seed() if random.getstate()[1] else None)
            
            prompts = []
            metadata = []
            
            for _, row in selected_df.iterrows():
                prompt = str(row[prompt_col]).strip()
                
                if prompt:
                    prompts.append(prompt)
                    
                    # 构建元数据，包含所有列
                    meta = {
                        "prompt": prompt,
                        "category": "multi_dataset",
                        "language": "unknown",
                        "description": "Loaded from CSV dataset using pandas",
                        "source_file": os.path.basename(csv_file),
                        "row_index": row.name  # pandas的索引
                    }
                    
                    # 添加CSV中的所有列作为元数据
                    for col in df.columns:
                        if col != prompt_col and pd.notna(row[col]):
                            meta[col] = str(row[col])
                    
                    metadata.append(meta)
            
            if not prompts:
                raise ValueError(f"No valid prompts found in CSV file: {csv_file}")
                
            return prompts, metadata
                
        except Exception as e:
            raise ValueError(f"Error loading prompts from CSV file {csv_file}: {e}")
    
    def _detect_prompt_column(self, df: pd.DataFrame) -> str:
        """自动检测prompt列"""
        # 优先检查常见的prompt列名
        prompt_keywords = ['prompt', 'text', 'content', 'question', 'input', 'message']
        
        for keyword in prompt_keywords:
            for col in df.columns:
                if keyword.lower() in col.lower():
                    # print(f"DEBUG: Auto-detected prompt column: {col}")
                    return col
        
        # 如果没有找到匹配的列名，使用第一列
        first_col = df.columns[0]
        # print(f"DEBUG: Using first column as prompt column: {first_col}")
        return first_col
    
    def get_prompts(self) -> List[str]:
        """获取所有prompt"""
        return self.prompts
    
    def get_custom_prompt(self) -> Optional[str]:
        """获取第一个prompt（兼容性方法）"""
        return self.prompts[0] if self.prompts else None
    
    def get_dataframe_info(self) -> Dict[str, Any]:
        """获取数据集信息"""
        if not self.metadata:
            return {"error": "No metadata available"}
        
        # 统计信息
        info = {
            "total_prompts": len(self.prompts),
            "source_file": self.metadata[0].get("source_file", "unknown"),
            "available_columns": list(self.metadata[0].keys()) if self.metadata else []
        }
        
        # 如果有category列，统计类别分布
        categories = [meta.get("category") for meta in self.metadata if meta.get("category")]
        if categories:
            info["category_distribution"] = pd.Series(categories).value_counts().to_dict()
        
        # 如果有language列，统计语言分布
        languages = [meta.get("language") for meta in self.metadata if meta.get("language")]
        if languages:
            info["language_distribution"] = pd.Series(languages).value_counts().to_dict()
        
        return info

# 测试代码
if __name__ == "__main__":
    # 测试1: 默认参数
    try:
        vuln1 = MultiDatasetVulnerability()
        print(f"Test 1: {len(vuln1.prompts)} prompts loaded")
        print(f"Sample prompts: {vuln1.prompts[:3]}")
        print(f"Dataset info: {vuln1.get_dataframe_info()}")
    except Exception as e:
        print(f"Test 1 failed: {e}")
    
    # 测试2: 指定数量和随机种子
    try:
        vuln2 = MultiDatasetVulnerability(num_prompts=5, random_seed=42)
        print(f"Test 2: {len(vuln2.prompts)} prompts loaded")
    except Exception as e:
        print(f"Test 2 failed: {e}")
    
    # 测试3: 指定prompt列名
    try:
        vuln3 = MultiDatasetVulnerability(num_prompts=3, prompt_column="text")
        print(f"Test 3: {len(vuln3.prompts)} prompts loaded with specified column")
    except Exception as e:
        print(f"Test 3 failed: {e}")
    
    # 测试4: 使用过滤条件
    try:
        filter_conditions = {"category": "harmful", "language": "zh"}
        vuln4 = MultiDatasetVulnerability(num_prompts=2, filter_conditions=filter_conditions)
        print(f"Test 4: {len(vuln4.prompts)} prompts loaded with filters")
    except Exception as e:
        print(f"Test 4 failed: {e}")
    
    # 测试5: 元数据
    try:
        vuln5 = MultiDatasetVulnerability(num_prompts=2)
        print(f"Test 5: Metadata sample: {vuln5.metadata[0] if vuln5.metadata else 'No metadata'}")
    except Exception as e:
        print(f"Test 5 failed: {e}") 
