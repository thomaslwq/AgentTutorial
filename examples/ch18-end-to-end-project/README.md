# ch18-end-to-end-project · 第 18 章配套示例

一个精简但完整的知识库客服 Agent 骨架：FastAPI 后端 + 内存 RAG 检索 + 工具调用 + SSE 流式 + 最小前端页面。目的是把前序各章的能力拼到一条链路上，而不是提供生产代码。

## 各章能力拼装地图

| 本骨架中的部分 | 对应章节 | 生产替换方向 |
|---|---|---|
| FastAPI 应用、`/api/chat` SSE 流式响应 | 第 16 章 FastAPI 后端服务化 | 会话管理、鉴权、请求限流 |
| `retrieve()` 关键词重叠检索 | 第 08/09 章 Embedding 与向量检索、混合检索 | 向量库 + BM25 混合召回 + 重排 |
| `search_kb` 工具轨迹上报 | 第 04 章 Function Calling | 原生工具调用协议、多工具注册 |
| 后端循环与终止条件 | 第 05 章 ReAct、第 12 章 LangGraph | 状态图编排、反思与重试 |
| `frontend/index.html` 流式接收与轨迹折叠 | 第 17 章 React + SSE 前端 | React 工程、状态管理、会话历史 |
| 错误事件、成本与可观测性 | 第 13/14 章 | 日志追踪、token 统计、越权防护 |

## 目录结构

```
ch18-end-to-end-project/
├── backend/
│   ├── main.py            # FastAPI 应用：检索工具 + SSE 流式回答
│   ├── requirements.txt
│   └── .env.example       # 环境变量样例（Key 走环境变量，不硬编码）
├── frontend/
│   └── index.html         # 最小页面：发送问题、逐字渲染、折叠工具轨迹
└── README.md
```

## 环境准备

```bash
cd backend
pip install -r requirements.txt

# 可选：配置模型 Key；不配置则后端走本地兜底回答，链路照样跑通
cp .env.example .env
export OPENAI_API_KEY=sk-你的key
# 兼容 OpenAI 协议的国产服务另设：
# export OPENAI_BASE_URL=https://your-endpoint/v1
# export LLM_MODEL=gpt-4o-mini
```

> 未配置 `OPENAI_API_KEY` 时，后端基于召回条目拼一段兜底文案并逐片吐出，用于在没有模型访问权限时验证前后端链路。兜底回答不经过模型，措辞固定，不能代表模型效果。

## 启动顺序

先起后端，再开前端：

```bash
# 终端 1：后端，监听 8000 端口
cd backend
uvicorn main:app --reload --port 8000
```

```bash
# 终端 2：前端，直接用浏览器打开即可
# 也可以用任意静态服务器托管 frontend/ 目录
#   python3 -m http.server 5173 --directory frontend
# 然后访问 http://localhost:5173/index.html
```

前端页面默认连接 `http://localhost:8000`，打开后先点页面上的状态检查（页面加载时会自动请求 `/health`），确认后端可达再提问。

## 测试清单

### 1. 健康检查

```bash
curl http://localhost:8000/health
# 预期：{"status":"ok"}
```

### 2. 流式对话（不带 Key 的兜底模式）

```bash
curl -N -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message":"退货流程是什么？"}'
```

预期输出按 SSE 帧依次出现：

1. `tool_start`：工具 `search_kb` 启动；
2. `tool_end`：召回「退货政策」等条目，带观察结果；
3. 若干 `token` 帧拼出回答；
4. `done` 结束。

`-N`（no buffer）让 curl 不缓冲，便于观察逐帧到达。

### 3. 召回不命中的问题

```bash
curl -N -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message":"怎么申请发票报销差旅？"}'
```

兜底模式下应返回「知识库中没有找到相关条目」类提示；接模型后，系统提示词要求模型在资料不足时明确说明，不得编造条款。

### 4. 前端链路

浏览器打开 `frontend/index.html`，输入「退款多久到账？」：回答逐字出现，下方折叠面板显示 `search_kb` 一步轨迹；点「停止」可中断当前请求。

## 从骨架到生产的扩展点

- **检索**：把 `retrieve()` 换成第 08 章的向量检索，接入真实 Embedding 模型与向量库；按第 09 章做混合召回、重排与召回评测。
- **工具**：`search_kb` 目前是后端内部函数直接调用。扩展为第 04 章的 Function Calling 协议，注册多个工具（查订单、查物流），由模型决定调用顺序。
- **会话**：当前每次请求独立，不带历史。接入第 03 章的记忆方案，后端按 `session_id` 存取对话历史。
- **工程化**：按第 13 章补日志、trace 与 token 成本统计；按第 14 章做输入输出校验、越权工具隔离与速率限制。
- **前端**：把 `index.html` 的逻辑迁入第 17 章的 React 组件，补会话历史、重新生成与错误重试。

## 部署 Checklist

- [ ] 后端 CORS 的 `allow_origins` 从 `*` 收敛到具体前端域名；
- [ ] `OPENAI_API_KEY`、`OPENAI_BASE_URL` 等密钥通过部署环境变量注入，不进代码仓库；
- [ ] 模型名、`top_k`、温度等参数走配置，不在代码里写死；
- [ ] 流式响应设置合理的超时与最大生成长度，避免挂死连接；
- [ ] 后端加鉴权（登录态 / API Key），`/api/chat` 不裸奔；
- [ ] 记录请求日志与 token 用量，设置成本与频率上限；
- [ ] 前端静态资源由 CDN 或反向代理托管，后端通过网关统一暴露；
- [ ] 对知识库条目更新流程化：解析、切分、入库、回滚（第 07 章）。

## 练习参考答案

### 练习 1：观察检索召回对回答的影响

**题目**：分别提问「退货流程」「退款时效」「会员折扣」，对照 `KB_DOCS` 看每条问题命中了哪些条目；再问一个知识库完全没有的话题（如「怎么修改收货地址」），观察兜底行为。

**参考答案**：关键词重叠打分下，问题里的汉字与标题/正文重合越多得分越高。「退货流程」命中「退货政策」，「退款时效」命中「退款时效」，「会员折扣」命中「会员权益」。未命中时 `retrieve()` 返回空列表，兜底回答提示换个说法或转人工；接模型后应在系统提示词约束下明确告知资料不足，而不是编造条款。

### 练习 2：把检索换成向量检索

**题目**：参考第 08 章示例，用 Embedding + 余弦相似度替换 `retrieve()` 的关键词打分，保留相同的函数签名（入参 query、top_k，返回文档列表）。

**参考答案**：替换点只在 `retrieve()` 内部：先对 `KB_DOCS` 批量向量化并缓存，查询时向量化后算余弦相似度取 top-k。`main.py` 的工具轨迹上报、SSE 帧格式、前端解析都不需要改动——这正是把检索层隔离成独立函数的好处。注意离线兜底向量只记录词项出现与否，语义改写类问题需要真实 Embedding 模型才能召回。

### 练习 3：补一个查订单工具

**题目**：仿照 `search_kb` 再注册一个 `get_order` 工具（入参订单号，返回模拟状态），在事件流里上报第二条工具轨迹。

**参考答案**：在后端加一个 `get_order(order_id: str)` 函数与模拟订单表；在 `event_stream` 里按问题需要先调检索、再调订单工具，分别推 `tool_start` / `tool_end` 帧。前端第 17 章的轨迹渲染是按条目追加的，两条工具轨迹会各自折叠展示。进一步可按第 04 章把工具改为模型原生 Function Calling，由模型决定是否调用、调用哪个。
