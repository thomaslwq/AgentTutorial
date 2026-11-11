"""第04章 · 工具定义与 Schema 注册。

两个演示工具：
- get_weather: 查天气（本地模拟数据，不依赖外网）
- calculate:   安全计算算术表达式（基于 ast，不用 eval）

每个工具同时登记两件事：
1. 一个 Python 可调用对象，程序用它真正执行；
2. 一份 JSON Schema，模型用它知道「有这个工具、参数长什么样」。
"""
from __future__ import annotations

import ast
import json
import operator
from typing import Any, Callable, Dict

# ---------------------------------------------------------------- 工具实现


_MOCK_WEATHER = {
    "北京": {"temp_c": 8, "condition": "晴", "humidity": 30},
    "上海": {"temp_c": 14, "condition": "多云", "humidity": 65},
    "深圳": {"temp_c": 22, "condition": "小雨", "humidity": 80},
}


def get_weather(city: str, unit: str = "celsius") -> Dict[str, Any]:
    """查询指定城市的天气。未知城市抛错，由上层循环捕获回喂给模型。"""
    if city not in _MOCK_WEATHER:
        raise ValueError(f"未知城市：{city}，目前支持 {list(_MOCK_WEATHER)}")
    info = _MOCK_WEATHER[city]
    temp = info["temp_c"]
    if unit == "fahrenheit":
        temp = round(temp * 9 / 5 + 32, 1)
    return {
        "city": city,
        "temp": temp,
        "unit": unit,
        "condition": info["condition"],
        "humidity": info["humidity"],
    }


# 安全计算器：白名单运算符，只允许数字与加减乘除取幂
_BIN_OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
}
_UNARY_OPS = {ast.UAdd: operator.pos, ast.USub: operator.neg}


def _eval_node(node: ast.AST) -> float:
    if isinstance(node, ast.Constant):
        if isinstance(node.value, (int, float)):
            return node.value
        raise ValueError(f"不支持的常量：{node.value!r}")
    if isinstance(node, ast.BinOp) and type(node.op) in _BIN_OPS:
        return _BIN_OPS[type(node.op)](_eval_node(node.left), _eval_node(node.right))
    if isinstance(node, ast.UnaryOp) and type(node.op) in _UNARY_OPS:
        return _UNARY_OPS[type(node.op)](_eval_node(node.operand))
    raise ValueError(f"不支持的表达式节点：{type(node).__name__}")


def calculate(expression: str) -> Dict[str, Any]:
    """对一个算术表达式求值，例如 (3 + 4) * 2。"""
    tree = ast.parse(expression, mode="eval")
    return {"expression": expression, "result": _eval_node(tree.body)}


# ---------------------------------------------------------------- 注册表

# name -> {"function": callable, "schema": OpenAI tools 数组里的一项}
TOOLS: Dict[str, Dict[str, Any]] = {
    "get_weather": {
        "function": get_weather,
        "schema": {
            "type": "function",
            "function": {
                "name": "get_weather",
                "description": "查询指定城市的当前天气。城市不在支持列表时会报错，模型应据此告知用户而不是编造数字。",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "city": {
                            "type": "string",
                            "description": "城市名，例如 北京 / 上海 / 深圳",
                        },
                        "unit": {
                            "type": "string",
                            "enum": ["celsius", "fahrenheit"],
                            "description": "温度单位，默认摄氏度；用户要求华氏度时传 fahrenheit",
                        },
                    },
                    "required": ["city"],
                },
            },
        },
    },
    "calculate": {
        "function": calculate,
        "schema": {
            "type": "function",
            "function": {
                "name": "calculate",
                "description": "对算术表达式求值。支持 + - * / % ** 与括号，不支持变量、函数调用。涉及数值运算时优先调用本工具，不要心算。",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "expression": {
                            "type": "string",
                            "description": "待计算的算术表达式，例如 (3 + 4) * 2 / 5",
                        },
                    },
                    "required": ["expression"],
                },
            },
        },
    },
}


def dispatch(name: str, arguments: Dict[str, Any]) -> str:
    """按名调用工具，统一把结果或异常转成字符串回喂模型。

    关键约定：工具内部怎么错都行，**不要让异常抛出循环**——
    异常本身就是给模型的观察信号。
    """
    entry = TOOLS.get(name)
    if entry is None:
        return f"[错误] 不存在的工具：{name}，可用工具：{list(TOOLS)}"
    try:
        result = entry["function"](**arguments)
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:  # noqa: BLE001
        return f"[工具执行失败] {type(e).__name__}: {e}"
