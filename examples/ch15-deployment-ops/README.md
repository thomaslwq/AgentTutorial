# ch15-deployment-ops · 第 15 章配套示例

一个基于 `asyncio` 的异步任务队列骨架：任务入队 → worker 协程并发消费 → 状态台账 → 失败重试退避 → 健康检查端点。骨架不强制要求模型 Key，`run_agent_task` 是预留的 Agent 执行体扩展点。

## 环境准备

```bash
# 骨架运行本身不需要 Key；接入真实模型时再配置：
# export OPENAI_API_KEY=sk-你的key
# export OPENAI_BASE_URL=https://your-endpoint/v1

pip install -r requirements.txt
```

可选环境变量：

| 变量 | 默认值 | 说明 |
|---|---|---|
| `WORKER_CONCURRENCY` | `3` | 并发消费的 worker 协程数 |
| `HEALTH_PORT` | `8081` | 健康检查 HTTP 端口 |
| `LOG_LEVEL` | `INFO` | 日志级别（DEBUG / INFO / WARNING / ERROR） |

## 运行

```bash
python worker_skeleton.py
```

程序提交两个示例任务，等待全部结束后打印任务台账（JSON）。另开一个终端可查看健康检查：

```bash
curl http://localhost:8081/healthz
```

返回形如：

```json
{
  "status": "ok",
  "uptime_s": 3,
  "queue_depth": 0,
  "stats": {"queued": 0, "running": 0, "succeeded": 2, "failed": 0}
}
```

## 预期输出

日志按行输出 JSON，关键事件依次为：`health_server_started` → `job_enqueued`（两条）→ `job_start` → `job_succeeded` → `all_done`。任务台账里每条记录包含 `status`、`attempts`、`result`、`error` 与时间戳。

## 代码结构与生产替换方向

| 骨架组件 | 职责 | 生产替换方向 |
|---|---|---|
| `asyncio.Queue` | 单进程内任务缓冲 | 跨进程/多机场景换 Redis Streams、RabbitMQ 或 Celery/RQ 后端 |
| `worker` | 消费任务、执行、重试退避 | 独立部署为 worker 进程，按 CPU/IO 特征调并发度 |
| `TaskStore` | 内存任务状态台账 | Redis（带 TTL）或关系库，支持任务查询与断点恢复 |
| `JsonLineFormatter` | 结构化日志输出 | 接入 ELK / Loki / 云日志服务，补充 trace_id、用户标识 |
| `/healthz` | 存活与负载探测 | 区分存活探针与就绪探针，接入容器编排的健康检查 |
| `run_agent_task` | Agent 执行体扩展点 | 接入第 05 章 ReAct 循环；异步环境用 `AsyncOpenAI` |

## 练习参考答案

### 练习 1：观察任务流转与健康检查

运行 `python worker_skeleton.py`，对照日志看每条任务的状态迁移：`queued`（入队）→ `running`（worker 取出）→ `succeeded`（结果落账）。在任务尚未跑完时访问 `curl http://localhost:8081/healthz`，可以看到 `queue_depth` 与 `running` 统计不为零；跑完后队列深度归零、`succeeded` 计数增加。健康检查的意义在于：编排系统据此判断实例是否还能接活，队列堆积或进程假死时探针可以反映出异常。

### 练习 2：注入失败观察重试

在 `run_agent_task` 开头按概率抛异常，例如：

```python
import random

if random.random() < 0.5:
    raise RuntimeError("模拟模型调用超时")
```

观察日志：首次失败后出现 `job_retry_scheduled`，退避时间取自 `BACKOFF_SECONDS` 序列（0.2s → 0.5s → 1.0s）；达到 `MAX_ATTEMPTS` 后任务置为 `failed` 并记录错误堆栈。要点是：重试要有次数上限和退避间隔，否则下游故障会被重试放大成雪崩；最终失败的任务需要进入死信队列或告警流程，而不是静默丢弃。

### 练习 3：把内存台账换成 Redis

`TaskStore` 需要持久化的字段：`job_id`、`status`、`payload`、`attempts`、`result`、`error`、`created_at`、`updated_at`。建议 key 设计为 `job:{job_id}`（Hash 存任务详情），另用一个 `job:index:by-status:{status}` 集合做按状态检索；任务结果设置 TTL（如 24 小时）避免堆积。读取路径保持 `get / update / stats` 三个方法不变，业务代码不需要改动——这就是把存储隔离在 `TaskStore` 接口后面的目的。
