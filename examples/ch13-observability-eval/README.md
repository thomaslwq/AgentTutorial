# ch13-observability-eval · 第 13 章配套示例

两个纯标准库脚本：本地 JSONL Trace 记录器，以及评测集打分脚本。离线即可跑通，
接入真实 Agent 时只需替换执行器。

## 环境准备

```bash
# 纯标准库脚本无需安装依赖；接入真实模型时再配置：
export OPENAI_API_KEY=sk-你的key
# 兼容 OpenAI 协议的服务另设：
# export OPENAI_BASE_URL=https://your-endpoint/v1

pip install -r requirements.txt
```

## 运行

```bash
python local_tracer.py     # 写 traces.jsonl，打印单条 trace 汇总
python eval_runner.py       # 内置样例数据集打分，打印指标汇总
python eval_runner.py dataset.json --output report.json
```

## 预期输出

`local_tracer.py` 打印一条 trace 汇总（span 数、prompt/completion token、总耗时），
并在同目录生成 `traces.jsonl`，每行一个 Span，可用 `cat traces.jsonl` 查看。

`eval_runner.py` 逐行打印每条用例的成功与否、关键词命中率、工具匹配、延迟与 token，
末尾输出汇总：任务成功率、工具匹配率、平均 / P50 延迟、总 token 与平均 token。
内置样例中 `case-04` 故意未调用预期工具，可观察到工具匹配率低于成功率。

## 评测集 JSON 格式

外部数据集是一个 JSON 数组，字段如下：

```json
[
  {
    "case_id": "case-05",
    "question": "杭州明天会下雨吗？",
    "expected_tools": ["weather"],
    "expected_keywords": ["杭州", "雨"],
    "notes": "可选备注"
  }
]
```

## 练习参考答案

### 练习 1：把真实模型调用接入 tracer

在模型调用前后用 `tracer.span(...)` 包裹，从 `response.usage` 回填 token：

```python
with tracer.span(trace_id, "llm:gpt-4o-mini", "llm") as sid:
    resp = client.chat.completions.create(model="gpt-4o-mini", messages=messages)
    tracer.end_span(sid, token={
        "prompt": resp.usage.prompt_tokens,
        "completion": resp.usage.completion_tokens,
    })
```

工具调用同理，用 `record_tool_call` 记录工具名、入参与结果预览。

### 练习 2：为评测集增加「多轮一致性」指标

对同一用例重复跑 3 次，统计回答关键词命中是否稳定；在 `summarize` 中新增
`consistency_rate`：3 次都成功记为一致。口径上注意区分「答案措辞波动」与
「任务结果错误」，低温采样更利于复现。

### 练习 3：回归测试门禁

把 `eval_runner.py` 的汇总指标接入 CI：任务成功率低于基线、或工具匹配率下降时退出码非 0。
可在 `main()` 末尾读取基线 JSON，比较 `task_success_rate`，不达标则 `sys.exit(1)`。
每次发版前跑同一套固定评测集，防止 Prompt 或模型升级引入回退。
