import time
import json
import asyncio
import aiohttp
import requests
from typing import Dict, Any, Optional
from deepeval.models.base_model import DeepEvalBaseLLM


class HTTPEndpointModel(DeepEvalBaseLLM):
    """HTTP REST端点模型，支持自定义HTTP请求"""
    max_trial = 3
    base_wait_seconds = 0.5

    def __init__(self, 
                 model_name: str, 
                 http_endpoint: str, 
                 http_method: str = "POST",
                 http_headers: Optional[Dict[str, str]] = None,
                 http_request_body: Optional[str] = None,
                 http_response_transform: Optional[str] = None,
                 max_concurrent: int = 10,
                 request_interval: int = 0):
        print(f"[DEBUG] HTTPEndpointModel __init__: model={model_name}, request_interval={request_interval}")
        self.model_name = model_name
        self.http_endpoint = http_endpoint
        self.http_method = http_method.upper()
        self.http_headers = http_headers or {}
        self.http_request_body = http_request_body or '{"message": "{{.Prompt}}"}'
        self.http_response_transform = http_response_transform
        self.max_concurrent = max_concurrent
        self.request_interval = request_interval  # 请求间隔（毫秒）
        self.semaphore = asyncio.Semaphore(max_concurrent)
        print(f"[DEBUG] HTTPEndpointModel 初始化完成: request_interval={self.request_interval}")
        
        # 确保 Content-Type 存在
        if 'Content-Type' not in self.http_headers:
            self.http_headers['Content-Type'] = 'application/json'
    
    def load_model(self):
        return self
    
    def _format_request_body(self, prompt: str, system_message: Optional[str] = None) -> str:
        """格式化请求体，支持模板变量替换"""
        body = self.http_request_body
        
        # 支持多种变量格式
        body = body.replace('{{.Prompt}}', prompt)
        body = body.replace('{{prompt}}', prompt)
        body = body.replace('{{user_message}}', prompt)
        
        if system_message:
            body = body.replace('{{.SystemMessage}}', system_message)
            body = body.replace('{{system_message}}', system_message)
        
        return body
    
    def _transform_response(self, response_data: Any) -> str:
        """转换HTTP响应为文本"""
        if not self.http_response_transform:
            # 默认转换逻辑
            if isinstance(response_data, dict):
                # 尝试常见的响应字段
                for field in ['content', 'text', 'message', 'response', 'output']:
                    if field in response_data:
                        return str(response_data[field])
                # 如果没有找到，返回JSON字符串
                return json.dumps(response_data, ensure_ascii=False)
            return str(response_data)
        
        try:
            # 执行自定义转换逻辑
            transform_path = self.http_response_transform.strip()
            
            # 支持特殊转换逻辑
            if transform_path.startswith("smart_extract:"):
                return self._apply_smart_extraction(response_data, transform_path[14:])
            
            # 处理以json.开头的路径
            if transform_path.startswith("json."):
                transform_path = transform_path[5:]  # 移除"json."前缀
            
            if transform_path.startswith('('):
                # JavaScript函数格式：(body) => { ... }
                return self._parse_javascript_function(response_data, transform_path)
            else:
                # 简单的JSON路径：data.messageList[0].content[0].text
                return self._parse_json_path(response_data, transform_path)
        except Exception as e:
            # 如果转换失败，返回原始数据的JSON字符串
            return json.dumps(response_data, ensure_ascii=False)
    
    def _parse_javascript_function(self, data: Any, js_function: str) -> str:
        """解析JavaScript函数格式的转换逻辑"""
        try:
            # 简单的JavaScript函数处理
            if 'return' in js_function:
                # 提取return语句
                return_start = js_function.find('return') + 6
                return_end = js_function.find(';', return_start)
                if return_end == -1:
                    return_end = js_function.rfind('}')
                path_expr = js_function[return_start:return_end].strip()
                return self._parse_json_path(data, path_expr)
            else:
                return json.dumps(data, ensure_ascii=False)
        except Exception:
            return json.dumps(data, ensure_ascii=False)
    
    def _apply_smart_extraction(self, response_data: dict, extract_type: str) -> str:
        """智能提取响应内容"""
        if extract_type == "alipay_message":
            return self._extract_alipay_message(response_data)
        elif extract_type == "antom_copilot":
            return self._extract_antom_copilot_message(response_data)
        elif extract_type == "best_text_content":
            return self._extract_best_text_content(response_data)
        else:
            return json.dumps(response_data, ensure_ascii=False)
    
    def _extract_alipay_message(self, response_data: dict) -> str:
        """提取支付宝API消息内容"""
        try:
            # 尝试获取 data.messageList 数组
            if "data" in response_data and "messageList" in response_data["data"]:
                message_list = response_data["data"]["messageList"]
                if isinstance(message_list, list) and len(message_list) > 0:
                    # 遍历消息列表，寻找最佳回复
                    for msg in message_list:
                        if isinstance(msg, dict):
                            # 检查消息类型是否为输出
                            if msg.get("ioType") == "OUTPUT":
                                # 检查内容数组
                                content = msg.get("content", [])
                                if isinstance(content, list) and len(content) > 0:
                                    content_item = content[0]
                                    if isinstance(content_item, dict):
                                        text = content_item.get("text", "")
                                        if text and not text.startswith("{") and '"status"' not in text:
                                            return text
                    
                    # 如果没找到合适的消息，返回第一个文本消息
                    for msg in message_list:
                        if isinstance(msg, dict):
                            content = msg.get("content", [])
                            if isinstance(content, list) and len(content) > 0:
                                content_item = content[0]
                                if isinstance(content_item, dict):
                                    text = content_item.get("text", "")
                                    if text:
                                        return text
        except Exception:
            pass
        return json.dumps(response_data, ensure_ascii=False)
    
    def _extract_antom_copilot_message(self, response_data: dict) -> str:
        """提取Antom Copilot API消息内容"""
        try:
            print(f"[DEBUG] 开始Antom Copilot智能提取")
            # 尝试获取 data.messageList 数组
            if "data" in response_data and "messageList" in response_data["data"]:
                message_list = response_data["data"]["messageList"]
                if isinstance(message_list, list) and len(message_list) > 0:
                    print(f"[DEBUG] 找到 {len(message_list)} 个消息")
                    
                    # 策略1: 查找包含实际用户回复的消息（非JSON结构）
                    for i, message in enumerate(message_list):
                        if isinstance(message, dict) and "content" in message:
                            content = message["content"]
                            if isinstance(content, list) and len(content) > 0:
                                content_item = content[0]
                                if isinstance(content_item, dict):
                                    text = content_item.get("text", "")
                                    if text and not text.strip().startswith("{") and len(text) > 50:
                                        print(f"[DEBUG] 策略1成功: 消息{i}, 长度{len(text)}")
                                        # 这是一个实际的用户回复，不是JSON结构
                                        return text
                    
                    # 策略2: 查找agentResult类型的消息，提取agentAnswer
                    for i, message in enumerate(message_list):
                        if isinstance(message, dict) and "content" in message:
                            content = message["content"]
                            if isinstance(content, list) and len(content) > 0:
                                content_item = content[0]
                                if isinstance(content_item, dict):
                                    text = content_item.get("text", "")
                                    if text and "agentAnswer" in text:
                                        try:
                                            # 解析JSON格式的agentResult
                                            agent_data = json.loads(text)
                                            if isinstance(agent_data, dict) and "agentAnswer" in agent_data:
                                                agent_answer = agent_data["agentAnswer"]
                                                if agent_answer and len(agent_answer) > 10:
                                                    print(f"[DEBUG] 策略2成功: 消息{i}, agentAnswer长度{len(agent_answer)}")
                                                    return agent_answer
                                        except json.JSONDecodeError:
                                            continue
                    
                    # 策略3: 使用现有的默认逻辑，但跳过纯JSON消息
                    for i, message in enumerate(message_list):
                        if isinstance(message, dict) and "content" in message:
                            content = message["content"]
                            if isinstance(content, list) and len(content) > 0:
                                content_item = content[0]
                                if isinstance(content_item, dict):
                                    text = content_item.get("text", "")
                                    if text and not text.strip().startswith("{"):
                                        print(f"[DEBUG] 策略3成功: 消息{i}, 文本内容")
                                        return text
                    
                    print("[DEBUG] 所有策略失败，返回第一个消息")
                    # 如果都失败了，返回第一个消息的内容
                    first_message = message_list[0]
                    if isinstance(first_message, dict) and "content" in first_message:
                        content = first_message["content"]
                        if isinstance(content, list) and len(content) > 0:
                            content_item = content[0]
                            if isinstance(content_item, dict):
                                text = content_item.get("text", "")
                                return text
        except Exception as e:
            print(f"[DEBUG] 提取异常: {str(e)}")
            pass
        print("[DEBUG] 返回原始JSON")
        return json.dumps(response_data, ensure_ascii=False)
    
    def _extract_best_text_content(self, response_data: dict) -> str:
        """提取最佳文本内容（通用）"""
        return self._find_best_text_in_response(response_data, 0)
    
    def _find_best_text_in_response(self, data: Any, depth: int) -> str:
        """在响应中递归查找最佳文本内容"""
        if depth > 5:  # 防止无限递归
            return ""
        
        if isinstance(data, dict):
            # 优先查找常见的文本字段
            priorities = ["text", "content", "message", "answer", "response", "reply"]
            for key in priorities:
                if key in data:
                    value = data[key]
                    if isinstance(value, str) and len(value) > 10 and not value.startswith("{"):
                        return value
            
            # 递归搜索所有字段
            for value in data.values():
                result = self._find_best_text_in_response(value, depth + 1)
                if result:
                    return result
        elif isinstance(data, list):
            # 搜索数组中的每个元素
            for item in data:
                result = self._find_best_text_in_response(item, depth + 1)
                if result:
                    return result
        elif isinstance(data, str):
            # 如果是字符串且长度合适，检查是否为有效内容
            if len(data) > 10 and not data.startswith("{") and '"status"' not in data:
                return data
        
        return ""

    def _parse_json_path(self, data: Any, path: str) -> str:
        """解析JSON路径表达式"""        
        # 简单的JSON路径解析
        try:
            current = data
            parts = path.split('.')
            
            for part in parts:
                if '[' in part and ']' in part:
                    # 处理数组索引：messageList[0]
                    field = part.split('[')[0]
                    index_str = part.split('[')[1].split(']')[0]
                    index = int(index_str)
                    
                    if field:  # 如果有字段名
                        current = current[field]
                    current = current[index]
                else:
                    # 普通字段访问
                    current = current[part]
            
            return str(current)
        except (KeyError, IndexError, TypeError, ValueError) as e:
            # 如果路径解析失败，尝试智能提取
            if "messageList" in path and "content" in path:
                return self._extract_alipay_message(data)
            return json.dumps(data, ensure_ascii=False)
    
    def test_model_connection(self) -> tuple[bool, str]:
        """测试模型连接"""
        try:
            test_prompt = "Hello, this is a test."
            response = self.generate(test_prompt)
            return True, response
        except Exception as e:
            return False, str(e)
    
    def generate(self, prompt: str, system_message: Optional[str] = None) -> str:
        # 请求前的频率控制
        if self.request_interval > 0:
            time.sleep(self.request_interval / 1000.0)  # 转换毫秒到秒
            
        for i in range(self.max_trial):
            try:
                body = self._format_request_body(prompt, system_message)
                print(f"[DEBUG] HTTP请求体: {body}")
                
                if self.http_method == "GET":
                    response = requests.get(
                        self.http_endpoint,
                        headers=self.http_headers,
                        timeout=30
                    )
                else:
                    response = requests.request(
                        method=self.http_method,
                        url=self.http_endpoint,
                        headers=self.http_headers,
                        data=body,
                        timeout=30
                    )
                
                print(f"[DEBUG] HTTP响应状态码: {response.status_code}")
                response.raise_for_status()
                
                # 解析响应
                try:
                    response_data = response.json()
                    print(f"[DEBUG] 原始响应数据: {json.dumps(response_data, ensure_ascii=False)[:500]}...")
                except json.JSONDecodeError:
                    response_data = response.text
                    print(f"[DEBUG] 文本响应数据: {response_data[:500]}...")
                
                # 转换响应
                result = self._transform_response(response_data)
                print(f"[DEBUG] 转换后结果: {result[:200]}...")
                if result:
                    return result
                else:
                    print("[DEBUG] 转换结果为空")
                    raise ValueError("Empty response from API")
                    
            except Exception as e:
                print(f"[DEBUG] 异常: {str(e)}")
                if i == self.max_trial - 1:
                    raise e
                wait_time = self.base_wait_seconds * (2 ** i)
                time.sleep(wait_time)
        
        return ""
    
    async def a_generate(self, prompt: str, system_message: Optional[str] = None) -> str:
        async with self.semaphore:
            # 请求前的频率控制 - 移到semaphore内部确保真正的串行执行
            if self.request_interval > 0:
                print(f"[DEBUG] 等待请求间隔: {self.request_interval}ms")
                await asyncio.sleep(self.request_interval / 1000.0)  # 转换毫秒到秒
                print(f"[DEBUG] 请求间隔等待完成")
            for i in range(self.max_trial):
                try:
                    body = self._format_request_body(prompt, system_message)
                    
                    async with aiohttp.ClientSession() as session:
                        if self.http_method == "GET":
                            async with session.get(
                                self.http_endpoint,
                                headers=self.http_headers,
                                timeout=aiohttp.ClientTimeout(total=30)
                            ) as response:
                                response.raise_for_status()
                                response_data = await response.json()
                        else:
                            async with session.request(
                                method=self.http_method,
                                url=self.http_endpoint,
                                headers=self.http_headers,
                                data=body,
                                timeout=aiohttp.ClientTimeout(total=30)
                            ) as response:
                                response.raise_for_status()
                                try:
                                    response_data = await response.json()
                                except json.JSONDecodeError:
                                    response_data = await response.text()
                    
                    # 转换响应
                    result = self._transform_response(response_data)
                    if result:
                        return result
                    else:
                        raise ValueError("Empty response from API")
                        
                except Exception as e:
                    if i == self.max_trial - 1:
                        raise e
                    wait_time = self.base_wait_seconds * (2 ** i)
                    await asyncio.sleep(wait_time)
            
            return ""
    
    def get_model_name(self):
        return self.model_name


def create_http_endpoint_model(
    model_name: str,
    http_endpoint: str,
    http_method: str = "POST",
    http_headers: Optional[Dict[str, str]] = None,
    http_request_body: Optional[str] = None,
    http_response_transform: Optional[str] = None,
    max_concurrent: int = 10
) -> HTTPEndpointModel:
    """创建HTTP端点模型实例"""
    return HTTPEndpointModel(
        model_name=model_name,
        http_endpoint=http_endpoint,
        http_method=http_method,
        http_headers=http_headers,
        http_request_body=http_request_body,
        http_response_transform=http_response_transform,
        max_concurrent=max_concurrent
    )
