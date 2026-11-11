# ch16-fastapi-service · 第 16 章配套示例

一个最小 FastAPI 聊天服务：非流式 `POST /chat`、SSE 流式 `POST /chat/stream`、内存会话管理，底层调用 OpenAI 兼容的流式接口。

## 环境准备

```bash
export OPENAI_API_KEY=sk-你的key
# 兼容 OpenAI 协议的国产服务另设：
# export OPENAI_BASE_URL=https://your-endpoint/v1
# 可选：export CHAT_MODEL=gpt-4o-mini

pip install -r requirements.txt
```

可选环境变量：

| 变量 | 默认值 | 说明 |
|---|---|---|
| `CHAT_MODEL` | `gpt-4o-mini` | 调用的模型名 |
| `MAX_HISTORY` | `20` | 每个会话保留的最近消息条数 |
| `CORS_ORIGINS` | `*` | 逗号分隔的允许来源，生产环境必须指定具体域名 |

## 运行

```bash
uvicorn main:app --host 0.0.0.0 --port 8000
```

启动后打开交互式文档：<http://localhost:8000/docs>。

## 测试命令

### 健康检查

```bash
curl http://localhost:8000/healthz
```

### 非流式问答

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "用一句话介绍 RAG", "session_id": "demo-1"}'
```

返回完整 JSON：`session_id`、`reply`、`model`。沿用同一个 `session_id` 再问一轮，模型可以参考上一轮内容。

### SSE 流式问答

```bash
curl -N -X POST http://localhost:8000/chat/stream \
  -H "Content-Type: application/json" \
  -d '{"message": "写三句关于向量检索的要点", "session_id": "demo-1"}'
```

`-N` 关闭 curl 缓冲，可看到响应按 `data: {...}` 逐段到达：

- `event: token`：每段增量文本在 `token` 字段；
- `event: done`：回答结束，`reply` 为完整文本；
- `event: error`：上游失败，带错误码与信息。

## 代码结构

| 组件 | 职责 |
|---|---|
| `ChatRequest` / `ChatResponse` | Pydantic 请求/响应契约，参数校验由框架完成 |
| `get_or_create_session` / `append_message` | 会话历史存取与窗口裁剪 |
| `call_model` | 非流式模型调用，统一捕获上游错误并转成 502 |
| `stream_generator` | 异步生成器，逐 token 产出 SSE 报文，结束后回写历史 |
| `/chat` | 非流式端点，一次性返回完整回答 |
| `/chat/stream` | SSE 流式端点，`StreamingResponse` 承载异步生成器 |

## 练习参考答案

### 练习 1：对比两种端点的体感

先调 `/chat`：请求发出后要等整段回答生成完，响应一次性到达；再调 `/chat/stream`：首段文字几乎立即出现，后续内容随模型生成逐段到达。流式的价值在于降低首字等待时间，长回答场景下体感差异明显；代价是客户端要处理增量拼接与断线重连。

### 练习 2：验证会话延续与历史裁剪

用同一个 `session_id` 连问两轮：第一轮问「记住我喜欢简洁风格」，第二轮问「我喜欢什么风格」。第二轮请求携带的历史里包含第一轮的问答，模型能答出简洁风格。把 `MAX_HISTORY` 调到 2，连续追问多轮后观察：早期消息被裁剪掉，模型不再记得最开始说过的内容——这就是窗口记忆的边界，更早的长期信息需要摘要记忆或外部存储（第 03 章）。

### 练习 3：把内存会话换成 Redis

替换思路：保持 `get_or_create_session` 与 `append_message` 的函数签名不变，内部从 `dict` 改为 `redis.asyncio` 客户端。key 设计为 `session:{session_id}`，值存 JSON 消息列表；写入时设置 TTL（如 24 小时），避免冷会话堆积。需要注意：Redis 读写要走异步客户端，不能在协程里用同步驱动阻塞事件循环；多副本部署下所有实例共享同一份会话，用户请求打到哪个实例都能拿到历史。
