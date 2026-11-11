# ch02-llm-prompt · 第 02 章配套示例

三个脚本分别对应：基础调用与参数、结构化输出、Prompt 模板化。

## 环境准备

```bash
export OPENAI_API_KEY=sk-你的key
# 兼容 OpenAI 协议的国产服务另设：
# export OPENAI_BASE_URL=https://your-endpoint/v1

pip install -r requirements.txt
```

模型名默认 `gpt-4o-mini`，可在脚本中替换为兼容服务提供的通用模型名。

## 运行

```bash
python basic_call.py          # messages 结构、关键参数、超时/限流重试与 token 统计
python structured_output.py    # json_object 与 json_schema 两种结构化输出
python prompt_template.py      # 模板插值、few-shot 示例、分隔符防注入、Prompt 版本号
```

## 预期输出说明

- `basic_call.py`：先打印模型对「缓存击穿」的一句话解释，末尾一行 `[token 使用] 输入 … / 输出 … / 合计 …`；无 Key 时会在重试后抛出 `RuntimeError`，属预期行为。
- `structured_output.py`：两段 JSON，分别为 `topic` + `keywords` 字段；`json_schema` 模式下字段与类型被 Schema 约束。
- `prompt_template.py`：先打印 Prompt 版本号，再输出一个 `{"category": ..., "reason": ...}` 的 JSON 分类结果。

## 练习参考答案

### 练习 1：参数调优对照

把 `basic_call.py` 中同一问题分别用 `temperature=0` 与 `temperature=1` 各跑三次：
`temperature=0` 回答措辞基本一致；`temperature=1` 细节与用词开始发散。再把 `frequency_penalty` 调到 `1.0`，重复用词会明显减少，但偶尔也会出现生僻替代词。

### 练习 2：为抽取结果补一个字段

在 `structured_output.py` 的 `EXTRACTION_SCHEMA` 中增加 `sentiment`（枚举 `positive / neutral / negative`）：

```python
"sentiment": {"type": "string", "enum": ["positive", "neutral", "negative"]},
```

同时把它加入 `required` 列表。`strict=True` 模式下新增字段必须显式声明，否则校验不通过。

### 练习 3：把 Prompt 抽成独立配置

把 `prompt_template.py` 中的 `ROLE`、`CONSTRAINTS`、`FEW_SHOT_EXAMPLES` 移到一个 `prompt_config.json`（或 YAML）中，启动时读取；`PROMPT_VERSION` 写入配置文件。这样调整 Prompt 不必改代码，也便于按版本记录线上效果。注意：模板里的 `{category}` 等占位符在配置文件中要与代码插值逻辑保持一致。
