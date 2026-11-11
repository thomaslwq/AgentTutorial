# AI Agent 全栈工程师教程

> 面向有编程基础的工程师，从一次真实的 LLM 调用，走到能上线的全栈 Agent 产品。
> 每一章都讲清「为什么」，并给出**可运行的真实源码**与**动手练习**，不堆概念、不虚构 API。

![构建状态](https://github.com/thomaslwq/AgentTutorial/actions/workflows/docs.yml/badge.svg)

## 这套教程解决什么问题

市面上的 Agent 教程常停留在两段代码：调一次 OpenAI、套一个 LangChain 的 `AgentExecutor`，跑通 demo 就结束。
但真实岗位要求你能回答：

- 为什么我的 Agent 偶尔「一本正经地胡说八道」？如何定位是 Prompt、记忆还是工具的问题？
- RAG 的召回质量差，到底是切分、Embedding、检索还是重排的问题？
- 多智能体看起来很酷，什么场景真的需要、什么场景只是增加复杂度？
- 写好的 Agent 怎么变成 FastAPI 服务、怎么接前端对话界面、怎么控制成本和安全？

这套教程按**工程师真实学习路径**组织：先把单 Agent 的认知部件（LLM、Prompt、记忆、工具、推理循环）拆透，再讲检索增强、规划与多智能体，最后进入工程化与全栈落地。

## 你需要的前置基础

| 能力 | 要求 |
|---|---|
| 编程 | 熟练 Python（3.10+）；前端章节要求基础 React/TypeScript |
| 概念 | 了解 HTTP、JSON、命令行；用过任意一个大模型产品（ChatGPT / Claude / 豆包等）即可 |
| 环境 | 一台可联网的电脑、一个 LLM API Key（OpenAI / Anthropic / 兼容 OpenAI 协议的国产模型均可） |

> 没有 API Key 也能先读：所有示例代码均在本地可完成语法与结构理解，关键处会标注哪些步骤需要真实 Key。

## 课程地图

### 模块一 · 认知基础：从 LLM 到 Agent
把 Agent 拆开看：一次调用里到底发生了什么。

1. [第 01 章 什么是 Agent](module-01-basics/ch01-what-is-agent.md) —— Agent 与普通聊天机器人的边界、Agent 的三要素、演进脉络
2. [第 02 章 LLM 调用与 Prompt 工程](module-01-basics/ch02-llm-prompt.md) —— 官方 SDK 直连、消息结构、参数调优、结构化输出、Prompt 模板化
3. [第 03 章 记忆系统](module-01-basics/ch03-memory.md) —— 对话历史管理、上下文压缩、长期记忆的三种落法
4. [第 04 章 工具调用 Function Calling](module-01-basics/ch04-function-calling.md) —— 工具协议、手写工具循环、Schema 设计与错误处理
5. [第 05 章 ReAct 推理与行动](module-01-basics/ch05-react.md) —— Thought-Action-Observation 循环、手写 ReAct、与直接调用的取舍

### 模块二 · RAG 全链路
让 Agent 基于你的私有知识回答，而不是凭空编。

6. [第 06 章 RAG 原理与整体架构](module-02-rag/ch06-rag-overview.md) —— 检索-生成范式、端到端流程图、选型
7. [第 07 章 文档解析与切分](module-02-rag/ch07-parse-chunk.md) —— PDF/网页/Markdown 解析、递归切分、元数据
8. [第 08 章 Embedding 与向量检索](module-02-rag/ch08-embedding-retrieval.md) —— Embedding 模型、向量库、混合检索与重排
9. [第 09 章 RAG 增强技术与评测](module-02-rag/ch09-rag-advanced-eval.md) —— 查询改写、HyDE、引用溯源、RAGAS 式评测

### 模块三 · 规划与多智能体
从「一问一答」走向「自己把大事拆成小事做完」。

10. [第 10 章 任务规划与自我反思](module-03-planning-multiagent/ch10-planning-reflection.md) —— Plan-and-Execute、反思修正
11. [第 11 章 多智能体协作](module-03-planning-multiagent/ch11-multi-agent.md) —— CrewAI / AutoGen、角色分工、协作模式
12. [第 12 章 LangGraph 状态图编排](module-03-planning-multiagent/ch12-langgraph.md) —— 节点/边/条件路由、持久化、人机协同

### 模块四 · Agent 工程化
能 demo 不等于能上线：可观测、评测、安全、成本、部署。

13. [第 13 章 可观测性与评测](module-04-engineering/ch13-observability-eval.md) —— Trace 链路、评测集、回归测试、Token 成本统计
14. [第 14 章 安全与成本控制](module-04-engineering/ch14-security-cost.md) —— Prompt 注入防护、权限边界、缓存、预算熔断
15. [第 15 章 部署与运维](module-04-engineering/ch15-deployment-ops.md) —— 服务化、并发、队列、监控告警、故障恢复

### 模块五 · 全栈落地
把 Agent 做成一个别人能打开用的产品。

16. [第 16 章 FastAPI 后端服务化与流式输出](module-05-fullstack/ch16-fastapi-service.md) —— SSE 流式、会话管理、接口设计
17. [第 17 章 前端对话 UI](module-05-fullstack/ch17-frontend-chat-ui.md) —— React 流式渲染、工具过程展示
18. [第 18 章 端到端实战：知识库客服 Agent](module-05-fullstack/ch18-end-to-end-project.md) —— 前后端 + RAG + 工具的完整项目串联

## 每一章的固定结构

- **本章目标**：读完你能做到什么
- **概念讲解**：先讲清楚原理与边界，再上代码
- **可运行源码**：代码块内嵌全文，同时在仓库 `examples/` 目录提供完整最小工程
- **动手练习**：由浅入深的 2~3 个练习，附参考答案位置
- **本章小结 + 思考题**：巩固与延伸

## 在线阅读与本地预览

- 在线版本由 GitHub Pages 自动发布，每次 push `main` 即重建（见 [如何参与与新增章节](appendix/contributing.md)）。
- 本地预览：

```bash
pip install -r requirements.txt
mkdocs serve          # 默认 http://127.0.0.1:8000
```

## 仓库结构速览

```
AgentTutorial/
├── docs/                 # 教程 Markdown 源文件（MkDocs 站点内容）
├── examples/             # 每章配套的最小可运行代码工程
├── .github/workflows/    # 自动构建部署 GitHub Pages 的工作流
├── mkdocs.yml            # MkDocs / 站点导航配置
└── requirements.txt      # 文档站点依赖
```

> 开源协议：[MIT](https://github.com/thomaslwq/AgentTutorial/blob/main/LICENSE)。欢迎 Star 与贡献。
