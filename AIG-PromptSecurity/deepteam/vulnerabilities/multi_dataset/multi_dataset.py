import os
import json
import pandas as pd
import random
from typing import List, Optional, Union, Dict, Any

from deepteam.vulnerabilities.custom import CustomVulnerability
from deepteam.vulnerabilities.multi_dataset import MultiDatasetVulnerabilityType

import os
import json
import random
import pandas as pd
from typing import List, Dict, Any, Optional, Tuple

class PromptLoader:
    def __init__(self):
        # 定义可能的prompt列名，按优先级排序
        self.PROMPT_COLUMN_CANDIDATES = [
            'prompt', 'question', 'query', 'text', 
            'input', 'content', 'instruction', 'message'
        ]
    
    def load_prompts(self, file_path: str, num_prompts: int = -1, 
                    prompt_key: Optional[str] = None,
                    filter_conditions: Optional[Dict[str, Any]] = None) -> Tuple[List[str], List[Dict[str, Any]]]:
        """从各种文件格式加载prompts
        
        Args:
            file_path: 输入文件路径
            num_prompts: 要提取的prompt数量，-1表示全部
            prompt_key: 指定作为prompt的列名
            filter_conditions: 过滤条件字典 {列名: 值}
            
        Returns:
            tuple: (prompts列表, 元数据列表)
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")
        
        ext = os.path.splitext(file_path)[1].lower()
        
        if ext == '.json':
            return self._load_from_json(file_path, num_prompts, prompt_key, filter_conditions)
        elif ext == '.jsonl':
            return self._load_from_jsonlines(file_path, num_prompts, prompt_key, filter_conditions)
        elif ext in ('.csv', '.tsv'):
            return self._load_from_csv(file_path, num_prompts, prompt_key, filter_conditions)
        elif ext == '.parquet':
            return self._load_from_parquet(file_path, num_prompts, prompt_key, filter_conditions)
        elif ext in ('.xlsx', '.xls'):
            return self._load_from_excel(file_path, num_prompts, prompt_key, filter_conditions)
        elif ext == '.txt':
            return self._load_from_txt(file_path, num_prompts, filter_conditions)
        else:
            raise ValueError(f"Unsupported file format: {ext}")
    
    def _detect_prompt_column(self, df: pd.DataFrame) -> str:
        """自动检测DataFrame中最可能是prompt的列"""
        for col in self.PROMPT_COLUMN_CANDIDATES:
            if col in df.columns:
                return col
        
        # 如果没有匹配的列名，尝试基于内容识别
        for col in df.columns:
            sample = str(df[col].iloc[0]) if len(df) > 0 else ""
            if len(sample.split()) >= 5:  # 假设prompt通常有较多单词
                return col
        
        # 最后返回第一列
        return df.columns[0]
    
    def _apply_filters(self, df: pd.DataFrame, filter_conditions: Optional[Dict[str, Any]]) -> pd.DataFrame:
        """应用过滤条件到DataFrame"""
        if not filter_conditions:
            return df
        
        for column, value in filter_conditions.items():
            if column in df.columns:
                if isinstance(value, (list, tuple)):
                    df = df[df[column].isin(value)]
                else:
                    df = df[df[column] == value]
        
        return df
    
    def _process_dataframe(self, df: pd.DataFrame, num_prompts: int, 
                         prompt_key: Optional[str], source_file: str) -> Tuple[List[str], List[Dict[str, Any]]]:
        """处理DataFrame提取prompts和元数据"""
        # 确定prompt列
        prompt_col = prompt_key if prompt_key else self._detect_prompt_column(df)
        
        if prompt_col not in df.columns:
            raise ValueError(f"Prompt column '{prompt_col}' not found in data")
        
        # 清理数据
        df = df.dropna(subset=[prompt_col])
        df = df.drop_duplicates(subset=[prompt_col])
        
        if df.empty:
            raise ValueError("No valid prompts found after cleaning")
        
        # 随机筛选指定数量的prompt
        if len(df) <= num_prompts or num_prompts == -1:
            selected_df = df
            if num_prompts != -1:
                print(f"WARNING: Requested {num_prompts} prompts but only {len(df)} available")
        else:
            selected_df = df.sample(n=num_prompts, random_state=random.seed() if random.getstate()[1] else None)
        
        prompts = []
        metadata = []
        
        for _, row in selected_df.iterrows():
            prompt = str(row[prompt_col]).strip()
            
            if prompt:
                prompts.append(prompt)
                
                # 构建元数据
                meta = {
                    "prompt": prompt,
                    "source_file": os.path.basename(source_file),
                    "row_index": row.name
                }
                
                # 添加所有其他字段作为元数据
                for col in df.columns:
                    if col != prompt_col and pd.notna(row[col]):
                        meta[col] = str(row[col])
                
                metadata.append(meta)
        
        if not prompts:
            raise ValueError("No valid prompts found in file")
            
        return prompts, metadata
    
    def _load_from_json(self, json_file: str, num_prompts: int, 
                       prompt_key: Optional[str], filter_conditions: Optional[Dict[str, Any]]) -> Tuple[List[str], List[Dict[str, Any]]]:
        """从JSON文件加载prompt列表和元数据"""
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # 处理不同JSON结构
            if isinstance(data, dict):
                prob_item = []
                for k, v in data.items():
                    if isinstance(v, list):
                        if k in ['data', 'examples']:
                            items = v
                            break
                        elif len(v) > len(prob_item):
                            prob_item = v
                else:
                    # 如果没有匹配，找最长的列表
                    if prob_item:
                        items = prob_item
                    # 整个字典就是数据
                    else:  
                        items = [data]
            elif isinstance(data, list):
                items = data
            else:
                raise ValueError(f"Invalid JSON format in {json_file}")
            
            df = pd.DataFrame(items)
            df = self._apply_filters(df, filter_conditions)
            
            return self._process_dataframe(df, num_prompts, prompt_key, json_file)
            
        except Exception as e:
            raise ValueError(f"Error loading prompts from JSON file {json_file}: {e}")
    
    def _load_from_jsonlines(self, jsonl_file: str, num_prompts: int, 
                           prompt_key: Optional[str], filter_conditions: Optional[Dict[str, Any]]) -> Tuple[List[str], List[Dict[str, Any]]]:
        """从JSON Lines文件加载prompt列表和元数据"""
        try:
            items = []
            with open(jsonl_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line:
                        items.append(json.loads(line))
            
            if not items:
                raise ValueError(f"No data found in JSON Lines file: {jsonl_file}")
            
            df = pd.DataFrame(items)
            df = self._apply_filters(df, filter_conditions)
            
            return self._process_dataframe(df, num_prompts, prompt_key, jsonl_file)
            
        except Exception as e:
            raise ValueError(f"Error loading prompts from JSON Lines file {jsonl_file}: {e}")
    
    def _load_from_csv(self, csv_file: str, num_prompts: int, 
                      prompt_key: Optional[str], filter_conditions: Optional[Dict[str, Any]]) -> Tuple[List[str], List[Dict[str, Any]]]:
        """从CSV/TSV文件加载prompt列表和元数据"""
        try:
            # 自动检测分隔符
            sep = ',' if csv_file.endswith('.csv') else '\t'
            
            df = pd.read_csv(csv_file, sep=sep, encoding='utf-8')
            df = self._apply_filters(df, filter_conditions)
            
            return self._process_dataframe(df, num_prompts, prompt_key, csv_file)
            
        except Exception as e:
            raise ValueError(f"Error loading prompts from CSV file {csv_file}: {e}")
    
    def _load_from_parquet(self, parquet_file: str, num_prompts: int,
                         prompt_key: Optional[str], filter_conditions: Optional[Dict[str, Any]]) -> Tuple[List[str], List[Dict[str, Any]]]:
        """从Parquet文件加载prompt列表和元数据"""
        try:
            df = pd.read_parquet(parquet_file)
            df = self._apply_filters(df, filter_conditions)
            
            return self._process_dataframe(df, num_prompts, prompt_key, parquet_file)
            
        except Exception as e:
            raise ValueError(f"Error loading prompts from Parquet file {parquet_file}: {e}")

    def _load_from_excel(self, excel_file: str, num_prompts: int, 
                        prompt_key: Optional[str], filter_conditions: Optional[Dict[str, Any]]) -> Tuple[List[str], List[Dict[str, Any]]]:
        """从Excel文件加载prompt列表和元数据"""
        try:
            df = pd.read_excel(excel_file)
            df = self._apply_filters(df, filter_conditions)
            
            return self._process_dataframe(df, num_prompts, prompt_key, excel_file)
            
        except Exception as e:
            raise ValueError(f"Error loading prompts from Excel file {excel_file}: {e}")
    
    def _load_from_txt(self, txt_file: str, num_prompts: int, 
                      filter_conditions: Optional[Dict[str, Any]]) -> Tuple[List[str], List[Dict[str, Any]]]:
        """从文本文件加载prompt列表和元数据"""
        try:
            prompts = []
            with open(txt_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith(('#', '//')):  # 跳过注释行
                        prompts.append(line)
            
            if not prompts:
                raise ValueError(f"No valid prompts found in text file: {txt_file}")
            
            # 随机筛选指定数量的prompt
            if len(prompts) <= num_prompts or num_prompts == -1:
                selected_prompts = prompts
                if num_prompts != -1:
                    print(f"WARNING: Requested {num_prompts} prompts but only {len(prompts)} available")
            else:
                selected_prompts = random.sample(prompts, num_prompts)
            
            # 为文本文件创建简单元数据
            metadata = [{
                "prompt": prompt,
                "source_file": os.path.basename(txt_file),
                "description": "Loaded from text file"
            } for prompt in selected_prompts]
            
            return selected_prompts, metadata
            
        except Exception as e:
            raise ValueError(f"Error loading prompts from text file {txt_file}: {e}")

class MultiDatasetVulnerability(CustomVulnerability):
    """
    多数据集漏洞类，从CSV文件中读取prompt并随机筛选
    使用pandas实现，支持更多高级功能
    """
    
    def __init__(self, prompt = None, dataset_file: str = "jb-top100.csv", num_prompts: int = 10, random_seed: Optional[int] = None, 
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
        if not os.path.isabs(dataset_file):
            dataset_file = os.path.join(os.path.dirname(__file__), dataset_file)
        
        # 加载prompts和元数据
        self.loader = PromptLoader()
        if prompt is not None:
            self.prompts = [prompt]
            self.metadata = [{
                "prompt": prompt,
                "category": "multi_dataset",
                "language": "unknown",
                "description": "Loaded from single prompt",
                "source_file": "Single prompt",
                "row_index": "prompt"  # pandas的索引
            }]
        else:
            self.prompts, self.metadata = self.loader.load_prompts(dataset_file, num_prompts, prompt_column, filter_conditions)
        
        # 调用父类初始化
        super().__init__(
            name="Multi Dataset Vulnerability",
            types=[type for type in MultiDatasetVulnerabilityType],
            custom_prompt=self.prompts
        )
    
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
