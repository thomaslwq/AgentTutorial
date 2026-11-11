# 术语表

| 术语 | 英文 | 简明解释 |
|---|---|---|
| LLM | Large Language Model | 大语言模型，本教程中 Agent 的「大脑」 |
| Token | Token | 模型计费与上下文的最小单位，约等于汉字的 0.5–1 个、英文的 0.75 个单词 |
| Prompt | Prompt | 发给模型的指令与上下文文本；Prompt 工程是设计它的方法学 |
| System Prompt | System Message | 对话首条、定义角色与规则的系统消息 |
| Function Calling | Tool Calling | 模型按约定 Schema 输出「要调用哪个函数、参数是什么」，由程序执行后把结果回喂模型 |
| ReAct | Reasoning + Acting | 推理-行动交替循环：思考 → 调工具 → 观察结果 → 再思考 |
| Memory | Memory | Agent 保存和复用历史信息的机制，分短期（对话窗口）与长期（持久化存储） |
| RAG | Retrieval-Augmented Generation | 检索增强生成：先检索相关资料，再让模型基于资料生成回答 |
| Embedding | Embedding | 把文本映射为稠密向量，用于语义相似度计算 |
| Chunking | Chunking | 把长文档切成适合检索的小块 |
| Vector DB | Vector Database | 存储向量并支持相似度检索的数据库（如 Chroma、Qdrant、pgvector） |
| Rerank | Reranking | 初筛后用更强模型对候选结果重新排序，提升 top-k 精度 |
| Agent | Agent | 能自主感知目标、选择工具、循环行动直到完成任务的 LLM 应用 |
| Multi-Agent | Multi-Agent System | 多个分工不同的 Agent 协作完成任务的系统 |
| Plan-and-Execute | Plan-and-Execute | 先整体规划步骤清单，再逐步执行、动态修订的范式 |
| LangGraph | LangGraph | LangChain 出品的有状态图编排框架，用节点与边描述 Agent 流程 |
| CrewAI / AutoGen | — | 两类主流多智能体框架：前者角色任务驱动，后者会话协商驱动 |
| SSE | Server-Sent Events | 服务端单向流式推送协议，用于把模型逐 token 输出实时推给前端 |
| Trace / Span | Trace / Span | 一次 Agent 运行及其内部各步骤的可观测性记录单元 |
| Hallucination | 幻觉 | 模型生成看似合理但不符合事实的内容 |
| Context Window | 上下文窗口 | 模型一次能看到的最大 token 数，超出需截断或压缩 |
