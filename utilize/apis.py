import json
import sys
from openai import OpenAI
import time
import random

api_keys_list = [
    # 'sk-ZmVeKnYDii42NZzVD245Af89F04b469dB9Db08C9B85aCf30',
    # 'sk-XzKw9F2UJXQZFFuOF60d7b69Ac834bF8Bf23D4E1A21a7b8e',
    'sk-ht342hixoVzvJUAEB8E8D90d729e4b9e93B751F69a5d79C0',
    # 'sk-0M4dkdvElRZX5oWe46D234D67d6b4409Bd9dF12dF997De19',
]


def get_from_openai(model_name='gpt-3.5-turbo', base_url=None, api_key=None,
                    messages=None, prompt=None, stop=None, max_len=1000, temp=1, n=1,
                    json_mode=False, usage=False):
    """
    :param model_name: text-davinci-003, gpt-3.5-turbo, gpt-3.5-turbo-0613
    """
    for i in range(10):
        # try:
            client = OpenAI(api_key=api_keys_list[random.randint(0, 100000) % len(api_keys_list)] if api_key is None else api_key,
                            base_url='https://api.aiguoguo199.com/v1' if base_url is None else base_url)
            kwargs = {
                "model": model_name, 'max_tokens': max_len, "temperature": temp,
                "n": n, 'stop': stop, 'messages': messages,
            }
            if json_mode == True:
                kwargs['response_format'] = {"type": "json_object"}
            if 'instruct' in model_name:

                assert prompt != None
                kwargs['prompt'] = prompt
                response = client.completions.create(**kwargs)
            else:
                assert messages is not None
                kwargs['messages'] = messages
                response = client.chat.completions.create(**kwargs)

            content = response.choices[0].message.content if n == 1 else [res.message.content for res in response.choices]
            results = {"content": content}
            if usage == True:
                results['usage'] = [response.usage.completion_tokens, response.usage.prompt_tokens,response.usage.total_tokens]
            return results
        # except:
        #     error = sys.exc_info()[0]
        #     print("API error:", error)
        #     time.sleep(1)
    return 'no response from openai model...'


import requests


def get_chat_gpt_response(model_name, prompt):
    url = "https://api.gptgod.online/v1/chat/completions"
    headers = {
        "Authorization": "sk-41wq3GeidiDwTGEA5i6UeOR3dySo83OlMmrn2qfAmUagr7Gg",
        "Content-Type": "application/json"
    }
    data = {
        "model": model_name,
        "messages": [{"role": "system", "content": "You are a helpful assistant."},
                     {"role": "user", "content": prompt}]
    }

    response = requests.post(url, headers=headers, json=data)
    return response.json()['choices'][0]['message']['content']

# 使用示例
# response = get_chat_gpt_response(model_name='gpt-4-turbo-preview',prompt="Hello, how are you?").choices[0]['messages']['content']
# print(response)

#
# if __name__ == '__main__':
#     answer = get_from_openai(model_name='gpt-4-turbo-preview', messages=[{"role": "user", 'content':  "shandong university is what"}],  # self.model_name
#                              api_key='', base_url='https://api.gptgod.online/')['content']
#
#     print(answer)
