# 常见问题 FAQ

### Q1：没有 OpenAI 官方 Key，能用国产模型吗？
可以。示例基于 OpenAI 兼容协议，设置 `OPENAI_BASE_URL` 指向兼容端点即可，`openai` SDK 调用代码不变。Anthropic 模型在对应章节用 `anthropic` SDK 单独演示。

### Q2：一定要先学 LangChain 吗？
不建议。模块一全部用**官方 SDK 手写** Agent 循环，目的是先理解本质；框架（LangGraph、CrewAI、AutoGen）在模块三才引入，此时你能看懂框架在替你封装什么。

### Q3：示例代码跑不通、报 401 / 429 / 超时？
- 401：检查 `OPENAI_API_KEY` 是否设置、是否完整；
- 429：触发限流或余额不足，退避重试或换模型；
- 超时：检查 `OPENAI_BASE_URL` 与网络；国产兼容端点注意模型名要与其控制台一致。

### Q4：为什么我的回答和教程不一样？
大模型有随机性（`temperature`），且模型版本会更新。教程固定关键行为，措辞差异属正常；重点观察流程与结构是否一致。

### Q5：本地 `mkdocs serve` 报插件找不到？
确认在仓库根目录执行了 `pip install -r requirements.txt`，并使用同一 Python 环境（建议 venv）。

### Q6：push 后站点没更新？
1. 看仓库 **Actions** 页工作流是否绿色；
2. 确认 Settings → Pages 的 Source 是 `gh-pages` 分支；
3. 缓存：强制刷新（Ctrl/Cmd+Shift+R），Pages 有几分钟 CDN 延迟。

### Q7：学习需要 GPU 吗？
不需要。本教程调用云端 API；涉及本地小模型的 roadmap 章节另作说明。

### Q8：前端章节（Ch17/18）零基础能跟吗？
建议先具备基础 React 知识；章节会把每段代码讲透，但不会从零补 React 入门。
