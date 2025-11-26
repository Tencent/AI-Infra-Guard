import openai
from typing import List


class LLM:
    def __init__(self, model, api_key, base_url):
        self.model = model
        self.api_key = api_key
        self.base_url = base_url
        self.client = openai.OpenAI(api_key=self.api_key, base_url=self.base_url)
        self.temperature = 0.7

    def chat(self, message: List[dict]):
        response = self.client.chat.completions.create(
            model=self.model,
            messages=message,
            temperature=self.temperature
        )
        return response.choices[0].message.content

    def chat_stream(self, message: List[dict]):
        response = self.client.chat.completions.create(
            model=self.model,
            messages=message,
            temperature=self.temperature,
            stream=True
        )
        return response


if __name__ == '__main__':
    import os
    # 测试代码 - 需要设置环境变量 OPENROUTER_API_KEY
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        print("请设置环境变量 OPENROUTER_API_KEY")
        exit(1)
    
    llm = LLM('google/gemini-2.5-flash', api_key, 'https://openrouter.ai/api/v1')
    print(llm.chat([{'role': 'user', 'content': 'Hello, how are you?'}]))
