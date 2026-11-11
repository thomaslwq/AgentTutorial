"""第02章 · 结构化输出：json_object 与 json_schema 两种模式。

前置：export OPENAI_API_KEY=sk-你的key
运行：python structured_output.py
"""
import json

from openai import OpenAI

client = OpenAI()

MODEL = "gpt-4o-mini"


def extract_with_json_object(question: str) -> dict:
    """模式一：response_format={"type": "json_object"}。

    约束较弱：只保证输出是合法 JSON 对象，字段由 Prompt 约定。
    注意：使用该模式时，Prompt 中必须明确出现「JSON」字样，否则部分模型会报错。
    """
    messages = [
        {"role": "system", "content": "你是一个信息抽取助手，只输出合法 JSON 对象，不输出多余解释。"},
        {
            "role": "user",
            "content": (
                "从下面用户问题中抽取主题与关键词。\n"
                f"问题：\n######\n{question}\n######\n"
                '输出 JSON，字段为："topic"（字符串）、"keywords"（字符串数组）。'
            ),
        },
    ]
    resp = client.chat.completions.create(
        model=MODEL,
        messages=messages,
        temperature=0,
        response_format={"type": "json_object"},
    )
    return json.loads(resp.choices[0].message.content)


# 模式二：json_schema。用 JSON Schema 显式声明字段、类型与必填项，约束更强。
EXTRACTION_SCHEMA = {
    "type": "object",
    "properties": {
        "topic": {"type": "string", "description": "问题所属的技术主题"},
        "keywords": {
            "type": "array",
            "items": {"type": "string"},
            "description": "抽取到的关键词列表",
        },
    },
    "required": ["topic", "keywords"],
    "additionalProperties": False,
}


def extract_with_json_schema(question: str) -> dict:
    """模式二：response_format={"type": "json_schema", ...}。

    strict=True 时：Schema 中所有字段必须列入 required，且 additionalProperties
    为 false；模型输出会被约束到该结构上，适合下游程序直接消费。
    """
    messages = [
        {"role": "system", "content": "你是一个信息抽取助手，严格按给定 Schema 输出。"},
        {"role": "user", "content": f"抽取下面问题的主题与关键词：\n{question}"},
    ]
    resp = client.chat.completions.create(
        model=MODEL,
        messages=messages,
        temperature=0,
        response_format={
            "type": "json_schema",
            "json_schema": {
                "name": "topic_extraction",
                "schema": EXTRACTION_SCHEMA,
                "strict": True,
            },
        },
    )
    return json.loads(resp.choices[0].message.content)


if __name__ == "__main__":
    q = "怎么用 Redis 解决缓存穿透和缓存雪崩？"

    print("== json_object 模式 ==")
    print(json.dumps(extract_with_json_object(q), ensure_ascii=False, indent=2))

    print("\n== json_schema 模式 ==")
    print(json.dumps(extract_with_json_schema(q), ensure_ascii=False, indent=2))
