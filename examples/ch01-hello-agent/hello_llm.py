"""第01章 · 最基础的一次 LLM 调用（聊天机器人形态）

前置环境变量：
    export OPENAI_API_KEY=sk-...
    # 使用兼容 OpenAI 协议的国产服务时另设：
    # export OPENAI_BASE_URL=https://your-endpoint/v1

运行：
    pip install -r requirements.txt
    python hello_llm.py
"""
import os

from openai import OpenAI

# OpenAI 客户端自动读取 OPENAI_API_KEY 与 OPENAI_BASE_URL
client = OpenAI()

# messages：system 定义角色与规则，user 给出本次任务
messages = [
    {"role": "system", "content": "你是一名严谨的技术讲师，回答简洁直接。"},
    {"role": "user", "content": "用一句话说明：Agent 和聊天机器人的区别是什么？"},
]

response = client.chat.completions.create(
    model="gpt-4o-mini",
    messages=messages,
    temperature=0.3,
)

answer = response.choices[0].message.content
print(answer)

# usage 记录本次 token 消耗，工程化阶段用于成本统计（第13章）
print("\n[token 使用] 输入:", response.usage.prompt_tokens,
      "输出:", response.usage.completion_tokens)
