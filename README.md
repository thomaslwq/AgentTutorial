# AgentTutorial · AI Agent 全栈工程师教程

[![Deploy MkDocs](https://github.com/thomaslwq/AgentTutorial/actions/workflows/docs.yml/badge.svg)](https://github.com/thomaslwq/AgentTutorial/actions/workflows/docs.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

面向有编程基础工程师的 AI Agent 全栈实战教程：从一次真实的 LLM 调用，走到能上线的 FastAPI + React Agent 产品。
**每章含原理讲解、可运行真实源码、动手练习与思考题**，Markdown 编写，MkDocs 构建，GitHub Pages 在线阅读。

🔗 在线站点（push 到 main 后自动更新）：https://thomaslwq.github.io/AgentTutorial/

## 课程地图

| 模块 | 章节 | 目标 |
|---|---|---|
| 一 · 认知基础 | Ch01 什么是 Agent / Ch02 LLM 调用与 Prompt / Ch03 记忆 / Ch04 Function Calling / Ch05 ReAct | 手写不依赖框架的最小 Agent |
| 二 · RAG 全链路 | Ch06 架构 / Ch07 解析切分 / Ch08 Embedding 检索 / Ch09 增强与评测 | 给 Agent 接上私有知识库 |
| 三 · 规划与多智能体 | Ch10 规划反思 / Ch11 多智能体 / Ch12 LangGraph | 自主规划、多角色协作 |
| 四 · 工程化 | Ch13 可观测评测 / Ch14 安全成本 / Ch15 部署运维 | 让 Agent 可观测、安全、可控 |
| 五 · 全栈落地 | Ch16 FastAPI 服务化 / Ch17 前端对话 UI / Ch18 端到端实战 | 交付完整 Agent 产品 |

完整大纲见站点首页与 `docs/index.md`。

## 仓库结构

```
AgentTutorial/
├── docs/                        # 教程 Markdown 源文件（MkDocs 内容）
│   ├── index.md                 # 首页 / 课程导航
│   ├── module-01-basics/        # 模块一：认知基础
│   ├── module-02-rag/           # 模块二：RAG
│   ├── module-03-planning-multiagent/
│   ├── module-04-engineering/
│   ├── module-05-fullstack/
│   └── appendix/                # 指南 / 术语表 / FAQ / 路线图
├── examples/                    # 每章配套最小可运行代码工程（chXX-*/）
├── .github/workflows/docs.yml   # push 到 main 自动构建并发布 gh-pages
├── assets/                      # 站点 logo / favicon
├── mkdocs.yml                   # MkDocs 主题与导航配置
├── requirements.txt             # 文档站点依赖
└── LICENSE                      # MIT
```

## 本地预览

```bash
git clone https://github.com/thomaslwq/AgentTutorial.git
cd AgentTutorial
python3 -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\Activate.ps1
pip install -r requirements.txt
mkdocs serve        # 打开 http://127.0.0.1:8000，改 Markdown 即时刷新
```

示例代码运行见各 `examples/chXX-*/README.md`；API Key 通过环境变量 `OPENAI_API_KEY`（及可选 `OPENAI_BASE_URL`）注入，**不要提交 Key**。

## 推送与发布（GitHub Pages 全自动）

工作流 `.github/workflows/docs.yml` 在 **push 到 `main`**（仅变更 `docs/`、`mkdocs.yml`、`requirements.txt`、工作流本身时触发）后自动：安装依赖 → `mkdocs build --strict` → 发布到 `gh-pages` 分支。

**仓库维护者首次一次性启用：**

1. 仓库 **Settings → Pages**；
2. **Source** 选 `Deploy from a branch`，分支 `gh-pages`，目录 `/ (root)`，保存；
3. 若 Actions 无写权限：**Settings → Actions → General → Workflow permissions** → `Read and write permissions`；
4. 首次 `git push origin main` 后，Actions 自动创建 `gh-pages` 并部署，约 1–2 分钟后站点可访问。

日常迭代：

```bash
# 新增/修改教程后
git add docs/ examples/ mkdocs.yml
git commit -m "docs: 新增/修订第XX章"
git push origin main
# 到 Actions 页确认绿色勾，站点自动更新
```

新增章节的标准步骤见 `docs/appendix/contributing.md`。

## 环境与依赖说明

- 站点依赖：`requirements.txt`（mkdocs-material 等），只在本地预览或 CI 构建时安装。
- 示例依赖：每个 `examples/chXX-*/requirements.txt` 独立，按需 `pip install -r`。

## License

[MIT](LICENSE) © 2026 Thomas.Lin
