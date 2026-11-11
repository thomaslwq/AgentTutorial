# ch04-function-calling · 第 04 章配套示例

手写 OpenAI 原生 Function Calling 工具循环，不依赖 LangChain。

## 文件

- `tools.py`：两个演示工具（`get_weather`、`calculate`）的实现 + JSON Schema 注册 + 统一 `dispatch`
- `handrolled_loop.py`：主循环——注册工具 → 模型决策 → 执行 → 回喂观察 → 直到最终回答

## 环境准备

```bash
export OPENAI_API_KEY=sk-你的key
# 兼容 OpenAI 协议的国产服务另设：
# export OPENAI_BASE_URL=https://your-endpoint/v1

pip install -r requirements.txt
```

## 运行

```bash
python handrolled_loop.py
```

默认任务：「北京和上海今天的天气如何？把两地温差算出来，用摄氏度回答我。」

预期 trace：

1. 第 1 轮模型并行发起两个 `get_weather`（北京、上海）；
2. 第 2 轮模型发起一次 `calculate("14 - 8")` 之类的算式；
3. 第 3 轮输出最终中文回答，`tool_calls` 为空，循环结束。

> 模型可能选择直接心算温差而不调 `calculate`——这是正常的；把 Prompt 里
> 「不要心算数值」那句话强化一下，它就会调。

## 练习参考答案

### 练习 1：未知城市的处理

把任务改成「广州今天天气怎么样？」。模型第一次调用 `get_weather(city="广州")`，
`dispatch` 捕获 `ValueError`，回喂：

```
[工具执行失败] ValueError: 未知城市：广州，目前支持 ['北京', '上海', '深圳']
```

下一轮模型通常会基于这条观察直接回答「暂不支持广州，目前可查北京/上海/深圳」，
而不是反复重试同一个城市。

### 练习 2：新增 convert_temperature 工具

在 `tools.py` 中追加：

```python
def convert_temperature(celsius: float, to_unit: str = "fahrenheit") -> Dict[str, Any]:
    if to_unit == "fahrenheit":
        return {"celsius": celsius, "fahrenheit": round(celsius * 9 / 5 + 32, 1)}
    return {"celsius": celsius}

TOOLS["convert_temperature"] = {
    "function": convert_temperature,
    "schema": {
        "type": "function",
        "function": {
            "name": "convert_temperature",
            "description": "把摄氏温度换算成华氏度。当用户要求华氏度时使用。",
            "parameters": {
                "type": "object",
                "properties": {
                    "celsius": {"type": "number", "description": "摄氏温度数值"},
                    "to_unit": {"type": "string", "enum": ["fahrenheit"]},
                },
                "required": ["celsius"],
            },
        },
    },
}
```

然后把用户问题改成「北京今天多少华氏度？」。模型应先 `get_weather`，再
`convert_temperature`，最后回答。

### 练习 3：强制工具选择

把 `tool_choice="auto"` 改成：

```python
tool_choice={"type": "function", "function": {"name": "calculate"}},
```

此时**每次**调用模型都被强制走 `calculate`，哪怕任务是查天气。你会看到模型
用 `calculate` 去算一个本来不需要算的表达式，或者直接在 arguments 里塞奇怪
的东西——这直观说明了为什么生产上通常用 `auto`，只在「必须经过某一步」的
流水线里才强制。
