import time

import openai
from typing import List
from utils.loging import logger


class LLM:
    def __init__(self, model, api_key, base_url):
        self.model = model
        self.api_key = api_key
        self.base_url = base_url
        self.client = openai.OpenAI(api_key=self.api_key, base_url=self.base_url, timeout=60)
        self.temperature = 0.7

    def chat(self, message: List[dict], p=False):
        ret = ''
        retry = 0
        while True:
            for word in self.chat_stream(message):
                # if p:
                #     print(word, end='', flush=True)
                ret += word
            if ret != '':
                break
            else:
                retry += 1
                logger.error(f'LLM chat error, retry {retry}')
                time.sleep(1.3)
                if retry > 5:
                    logger.error('LLM chat error, retry 5 times, exit')
                    return '连接LLM失败，已重试5次，模型输出为空,请等待1分钟后再试'
        if p:
            print(ret)
        return ret


    def chat_stream(self, message: List[dict]):
        response = self.client.chat.completions.create(
            model=self.model,
            messages=message,
            temperature=self.temperature,
            stream=True
        )

        for chunk in response:
            choices = getattr(chunk, "choices", None)

            # Ensure choices is a non-empty list
            if not isinstance(choices, list) or not choices:
                continue
            choice = choices[0]

            delta = getattr(choice, "delta", None)
            if not delta:
                continue

            content = getattr(delta, "content", None)
            if content:
                yield content
