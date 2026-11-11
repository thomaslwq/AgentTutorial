/**
 * 第17章 · React + TypeScript 聊天界面关键组件
 *
 * 依赖：react >= 18、react-dom >= 18（类型见 package.json）。
 * 本文件只保留对话界面的关键逻辑，样式用 className 占位，
 * 生产项目可替换为组件库（Ant Design / MUI 等）。
 *
 * 后端约定（与第16章 FastAPI 服务、第18章示例一致）：
 *   POST /api/chat
 *   body: {"message": string, "session_id"?: string}
 *   响应：text/event-stream，每个 SSE 帧为 `data: <json>\n\n`
 *     {"type":"tool_start","tool":"search_kb","args":{...}}
 *     {"type":"tool_end","tool":"search_kb","observation":"..."}
 *     {"type":"token","delta":"..."}
 *     {"type":"error","message":"..."}
 *     {"type":"done"}
 *
 * 后端地址在生产环境应来自环境变量或构建配置；这里用常量占位。
 */
import { useCallback, useRef, useState } from "react";

// ------------------------------------------------------------------ 类型

type Role = "user" | "assistant";

interface ToolTrace {
  tool: string;
  args: Record<string, unknown>;
  status: "running" | "done";
  observation?: string;
}

interface ChatMessage {
  id: string;
  role: Role;
  content: string;
  traces: ToolTrace[];
  status: "streaming" | "done" | "error";
  error?: string;
}

type StreamEvent =
  | { type: "tool_start"; tool: string; args: Record<string, unknown> }
  | { type: "tool_end"; tool: string; observation: string }
  | { type: "token"; delta: string }
  | { type: "error"; message: string }
  | { type: "done" };

/** 后端基础地址；接入真实工程时从环境变量注入。 */
const API_BASE = "http://localhost:8000";

let seq = 0;
const nextId = () => `msg-${Date.now()}-${seq++}`;

// ---------------------------------------------------------------- SSE 解析

/** 解析一帧 SSE 文本（已去掉结尾空行），返回 data 负载；无 data 行则返回 null。 */
function parseFrame(frame: string): unknown | null {
  const dataLines: string[] = [];
  for (const line of frame.split(/\r?\n/)) {
    if (line.startsWith("data:")) {
      dataLines.push(line.slice(5).trimStart());
    }
  }
  if (dataLines.length === 0) return null;
  return JSON.parse(dataLines.join("\n"));
}

/**
 * 读取 fetch 返回的 ReadableStream，按 SSE 分帧后逐事件回调。
 * 关键点：一次网络 chunk 可能包含多帧，也可能只到半帧，必须用 buffer 拼。
 */
async function readSSE(
  response: Response,
  onEvent: (evt: StreamEvent) => void,
): Promise<void> {
  if (!response.body) throw new Error("响应没有 body，无法流式读取");
  const reader = response.body.getReader();
  const decoder = new TextDecoder("utf-8");
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });

    let sep: number;
    while ((sep = buffer.indexOf("\n\n")) >= 0) {
      const frame = buffer.slice(0, sep);
      buffer = buffer.slice(sep + 2);
      const payload = parseFrame(frame);
      if (payload) onEvent(payload as StreamEvent);
    }
  }

  const tail = buffer.trim();
  if (tail) {
    const payload = parseFrame(tail);
    if (payload) onEvent(payload as StreamEvent);
  }
}

// ----------------------------------------------------------------- 组件

export default function ChatPanel() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const abortRef = useRef<AbortController | null>(null);

  const patchMessage = useCallback(
    (id: string, patch: Partial<ChatMessage>) => {
      setMessages((prev) =>
        prev.map((m) => (m.id === id ? { ...m, ...patch } : m)),
      );
    },
    [],
  );

  /** 追加一条工具轨迹；同名工具的 running 记录收到后替换为 done。 */
  const appendTrace = useCallback((id: string, trace: ToolTrace) => {
    setMessages((prev) =>
      prev.map((m) => {
        if (m.id !== id) return m;
        const idx = m.traces.findIndex(
          (t) => t.tool === trace.tool && t.status === "running",
        );
        if (idx >= 0) {
          const traces = m.traces.slice();
          traces[idx] = trace;
          return { ...m, traces };
        }
        return { ...m, traces: [...m.traces, trace] };
      }),
    );
  }, []);

  const stop = useCallback(() => {
    abortRef.current?.abort();
    setLoading(false);
  }, []);

  const send = useCallback(async () => {
    const text = input.trim();
    if (!text || loading) return;
    setInput("");
    setLoading(true);

    const userMsg: ChatMessage = {
      id: nextId(),
      role: "user",
      content: text,
      traces: [],
      status: "done",
    };
    const assistantId = nextId();
    const assistantMsg: ChatMessage = {
      id: assistantId,
      role: "assistant",
      content: "",
      traces: [],
      status: "streaming",
    };
    setMessages((prev) => [...prev, userMsg, assistantMsg]);

    const controller = new AbortController();
    abortRef.current = controller;

    try {
      const resp = await fetch(`${API_BASE}/api/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: text, session_id: "demo" }),
        signal: controller.signal,
      });
      if (!resp.ok) throw new Error(`后端返回 ${resp.status}`);

      await readSSE(resp, (evt) => {
        switch (evt.type) {
          case "token":
            setMessages((prev) =>
              prev.map((m) =>
                m.id === assistantId
                  ? { ...m, content: m.content + evt.delta }
                  : m,
              ),
            );
            break;
          case "tool_start":
            appendTrace(assistantId, {
              tool: evt.tool,
              args: evt.args,
              status: "running",
            });
            break;
          case "tool_end":
            appendTrace(assistantId, {
              tool: evt.tool,
              args: {},
              status: "done",
              observation: evt.observation,
            });
            break;
          case "error":
            patchMessage(assistantId, { status: "error", error: evt.message });
            break;
          case "done":
            patchMessage(assistantId, { status: "done" });
            break;
        }
      });
      patchMessage(assistantId, { status: "done" });
    } catch (err) {
      if ((err as Error).name === "AbortError") {
        patchMessage(assistantId, { status: "done" });
      } else {
        patchMessage(assistantId, {
          status: "error",
          error: (err as Error).message,
        });
      }
    } finally {
      setLoading(false);
      abortRef.current = null;
    }
  }, [input, loading, appendTrace, patchMessage]);

  // ---------------------------------------------------------------- 渲染

  return (
    <div className="chat-panel">
      <div className="message-list">
        {messages.map((m) => (
          <div key={m.id} className={`message ${m.role}`}>
            <div className="bubble">
              {m.content || (m.status === "streaming" ? "思考中…" : "")}
            </div>

            {m.traces.length > 0 && (
              <details className="trace">
                <summary>工具调用 {m.traces.length} 步</summary>
                <ul>
                  {m.traces.map((t, i) => (
                    <li key={i}>
                      <code>{t.tool}</code>（{t.status}）
                      {t.observation ? <p>{t.observation}</p> : null}
                    </li>
                  ))}
                </ul>
              </details>
            )}

            {m.status === "error" && (
              <div className="error">出错：{m.error}</div>
            )}
          </div>
        ))}
      </div>

      <div className="composer">
        <textarea
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              void send();
            }
          }}
          rows={2}
          placeholder="输入问题，Enter 发送，Shift+Enter 换行"
        />
        {loading ? (
          <button onClick={stop}>停止</button>
        ) : (
          <button onClick={() => void send()}>发送</button>
        )}
      </div>
    </div>
  );
}
