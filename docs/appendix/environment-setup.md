# 环境搭建

## 1. 基础环境

| 工具 | 版本要求 | 说明 |
|---|---|---|
| Python | 3.10+（推荐 3.12） | 所有后端示例使用 |
| Git | 任意现代版本 | 拉取与提交 |
| Node.js | 18+（仅前端章节需要） | Ch17 / Ch18 |
| 终端 | macOS Terminal / Linux bash / Windows PowerShell 均可 | |

检查：

```bash
python3 --version   # 或 python --version
git --version
node --version      # 前端章节
```

## 2. 获取 API Key

示例统一使用 **OpenAI 官方 SDK 兼容协议**（`openai` 包）。你可以选择：

- OpenAI 官方 Key（`https://platform.openai.com`）；
- Anthropic 官方 SDK（`anthropic` 包，部分章节对比使用）；
- 任何兼容 OpenAI 协议的国产模型服务：只需改 `base_url` 与 `api_key`，调用代码不变。

> 兼容服务通常提供一个 `base_url`（形如 `https://xxx/v1`）和一个 API Key。本教程的示例通过环境变量注入，**不要把 Key 写进代码或提交进仓库**。

设置环境变量（以 bash/zsh 为例，写入 `~/.bashrc` 或 `~/.zshrc`）：

```bash
export OPENAI_API_KEY="sk-你的key"
# 若使用兼容服务，同时设置：
export OPENAI_BASE_URL="https://your-compatible-endpoint/v1"
```

Windows PowerShell：

```powershell
$env:OPENAI_API_KEY = "sk-你的key"
$env:OPENAI_BASE_URL = "https://your-compatible-endpoint/v1"
```

## 3. 拉取仓库并创建虚拟环境

```bash
git clone https://github.com/thomaslwq/AgentTutorial.git
cd AgentTutorial

python3 -m venv .venv
# macOS / Linux
source .venv/bin/activate
# Windows PowerShell
# .venv\Scripts\Activate.ps1
```

## 4. 安装依赖

**文档站点依赖**（只想在线看不需要本地装）：

```bash
pip install -r requirements.txt
mkdocs serve    # http://127.0.0.1:8000
```

**章节示例依赖**：每章 `examples/chXX-*/requirements.txt` 独立安装，避免一次拉全：

```bash
cd examples/ch02-llm-prompt
pip install -r requirements.txt
python main.py
```

## 5. 最小验证（第 02 章之前的自检）

```bash
python -c "import openai; print(openai.__version__)"
echo $OPENAI_API_KEY | head -c 6   # 只看前几位，确认已设置
```

能打印版本号、Key 已设置，即可开始。遇到问题先查 [FAQ](faq.md)。
