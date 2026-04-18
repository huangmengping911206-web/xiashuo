# Please install OpenAI SDK first: `pip3 install openai`
import os
from openai import OpenAI


client = OpenAI(
    api_key='sk-54ffd688a7e540ed88465627718165ce',
    base_url="https://api.deepseek.com/v3.1_terminus_expires_on_20251015")

response = client.chat.completions.create(
    model="deepseek-chat",
    messages=[
        {"role": "system", "content": "You are a helpful assistant"},
        {"role": "user", "content": "Hello"},
    ],
    stream=False
)

print(f"Model is: {response.model}")
print(f"Output is: {response.choices[0].message.content}")