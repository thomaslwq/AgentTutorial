# ch17-frontend-chat-ui · 第 17 章配套示例

第 17 章的前端对话界面示例，包含两部分：

| 文件 | 作用 | 是否需要构建 |
|---|---|---|
| `chat.tsx` | React 18 + TypeScript 关键组件：消息列表、SSE 流式追加、工具轨迹折叠、停止请求 | 接入工程后编译；本文件只做逻辑参考 |
| `demo-stream.html` | 纯 HTML/JS 单文件，双击即可在浏览器打开；内置「模拟流式」与「连接后端」两种模式 | 不需要，无任何依赖 |
| `package.json` | React 侧依赖与类型声明，便于把 `chat.tsx` 拷进一个 Vite / CRA 工程 | 仅在接入 React 工程时使用 |

## 后端事件契约

前端与后端按 SSE（`text/event-stream`）通信，每个帧为 `data: <json>\n\n`：

```json
{"type":"tool_start","tool":"search_kb","args":{"query":"退货流程"}}
{"type":"tool_end","tool":"search_kb","observation":"召回 2 条相关条目"}
{"type":"token","delta":"退货需在签收后 7 天内申请"}
{"type":"error","message":"后端返回 500"}
{"type":"done"}
```

请求约定：`POST /api/chat`，body 为 `{"message": string, "session_id"?: string}`。

## 运行方式

### 1. 纯前端演示（无需后端、无需安装）

直接用浏览器打开 `demo-stream.html`：

- 点「模拟流式」：页面在本地拼出标准 SSE 帧，走与真实链路相同的分帧解析与渲染逻辑，可观察到文字逐字出现、工具轨迹先出现「running」再替换为「done」。
- 点「连接后端」：向输入框中的地址（默认 `http://localhost:8000/api/chat`）发 POST，读取真实流式响应。后端可使用第 18 章示例，或第 16 章的 FastAPI 服务。

> 浏览器直接打开本地 HTML（`file://`）时，向 `http://localhost` 发请求一般允许；若浏览器拦截混合内容或 CORS，按页面报错在后端配置允许来源（见章节 17.7）。

### 2. 把 chat.tsx 接入 React 工程

```bash
npm install
# 把 chat.tsx 拷入工程 src/ 目录，在页面中渲染 <ChatPanel />
```

`chat.tsx` 只依赖 React 自带 Hooks（`useState` / `useRef` / `useCallback`）与浏览器标准 API（`fetch`、`ReadableStream`、`TextDecoder`、`AbortController`），没有引入状态管理库或组件库。

## 选型说明：为什么用 fetch + ReadableStream，而不是 EventSource

| 维度 | EventSource | fetch + ReadableStream |
|---|---|---|
| 请求方法 | 只支持 GET | 支持 POST，可携带 JSON body |
| 请求头 | 无法自定义 | 可设置 `Content-Type`、鉴权头 |
| 中断连接 | 只能 `close()`，不能复用 AbortController | 传入 `AbortController.signal`，可随时取消 |
| 响应解析 | 浏览器自动按 SSE 解析，`onmessage` 回调 | 手动分帧，可处理自定义 `event:` 类型与二进制 |
| 兼容性 | 现代浏览器良好 | 现代浏览器良好；旧环境需 polyfill |

Agent 对话通常要把整段对话历史放进 POST body，并需要在用户点「停止」时中断请求，因此本教程统一采用 fetch + ReadableStream。

## 练习参考答案

### 练习 1：半帧粘包与拆包

**题目**：把 `demo-stream.html` 模拟模式里的 `sleep(90)` 去掉，让所有帧一次性推入解析器；再改成每个字符单独推一次。观察两种情况下消息是否都能正确拼接。

**参考答案**：两种情况都应正确。`SseParser.push` 每次先把新片段追加到 `buffer`，再用 `indexOf("\n\n")` 找帧边界：一次性推入时一个 buffer 里含多帧，循环切出全部；逐字符推入时边界尚未出现，内容留在 buffer 里等待后续片段。这正是不能按网络 chunk 直接 `JSON.parse` 的原因——chunk 与 SSE 帧不是一一对应关系。

### 练习 2：停止按钮中断流式请求

**题目**：在「连接后端」模式下发送一条消息，流式输出到一半时点「停止」。补充前端行为：中断后把当前助手消息标记为已结束（保留已收到的文字），并恢复发送按钮。

**参考答案**：`AbortController.abort()` 会让 `fetch` 的 Promise reject 出 `AbortError`。`chat.tsx` 的 `catch` 分支已按错误名区分：`AbortError` 时把消息状态置为 `done` 而不是 `error`；其他异常才写入错误提示。`finally` 里清空 controller 引用并恢复 `loading`。HTML demo 中对应逻辑在 `sendToBackend` 的 `catch` / `finally` 分支。注意：中断只断开浏览器侧连接，后端生成是否停止取决于服务端是否监听了客户端断连（第 16、18 章的流式响应会在客户端断开后结束生成）。

### 练习 3：工具轨迹的折叠展示

**题目**：当前轨迹用 `<details>` 折叠展示。请补充：轨迹展开时按时间顺序显示工具名、入参和观察结果；同一条助手消息出现两次同名工具时，两条轨迹都保留而不是互相覆盖。

**参考答案**：`chat.tsx` 的 `appendTrace` 只把「同名且状态为 running」的记录替换为 done，第二次调用会作为新条目追加；`demo-stream.html` 的 `addTrace` 用 `tool-status` 作为条目标识，两次 `search_kb` 会生成两条 `<li>`。入参目前只在 `tool_start` 事件里携带，渲染时可从 `trace.args` 取 `JSON.stringify(args)` 显示；观察结果来自 `tool_end` 事件。生产实现建议给每条轨迹一个自增序号，避免同名工具的条目定位歧义。
