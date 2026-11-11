# 如何参与与新增章节

本仓库采用「**Markdown 即内容，Push 即发布**」的迭代模式：新增/修改一篇教程 Markdown，推送到 `main`，GitHub Actions 自动重建静态站点并发布到 GitHub Pages，无需手动构建。

## 一、本地开发流程

```bash
git clone https://github.com/thomaslwq/AgentTutorial.git
cd AgentTutorial
pip install -r requirements.txt
mkdocs serve          # 浏览器打开 http://127.0.0.1:8000，改 md 即时刷新
```

## 二、新增一章的标准步骤（5 步）

1. **新建章节 Markdown**：放入对应模块目录，命名规范 `chXX-topic-slug.md`（小写连字符），例如 `module-03-planning-multiagent/ch13-xxx.md`。
2. **在 `mkdocs.yml` 的 `nav` 中登记**：把新文件路径加到所属模块列表下，标题格式 `第 XX 章 标题`。缺少这一步页面不会出现在导航里。
3. **配套代码工程**：在 `examples/` 下新建 `chXX-topic/`，包含可运行的最小工程、`requirements.txt`、`README.md`（写明运行命令与所需环境变量）。章节正文用代码块贴出关键源码，并用相对/仓库链接指到 `examples/` 目录。
4. **本地自检**：`mkdocs build --strict` 无报错；示例代码 `python -m py_compile` 通过。
5. **提交推送**：

```bash
git add docs/ examples/ mkdocs.yml
git commit -m "docs: 新增第XX章 xxx"
git push origin main
```

推送后 Actions 自动构建（见仓库 Actions 页），约 1–2 分钟后 Pages 站点更新。

## 三、章节写作规范（给贡献者）

每章必须包含以下固定小节，顺序一致：

1. `## 本章目标`：3–5 条可衡量的读完收获。
2. `## 概念讲解`：先讲原理、边界与常见误区，再上代码；概念处配必要的图示（mermaid 或表格）。
3. `## 实战：可运行源码`：关键代码用带语言标注的围栏块（```python / ```tsx），代码必须基于**官方 SDK 或主流稳定开源框架**，禁止虚构 API；第三方库注明版本。
4. `## 动手练习`：2–3 题，由易到难，标注「参考答案见 examples/」。
5. `## 本章小结`：bullet 回顾。
6. `## 思考题`：2–3 题，指向后续章节。

风格要求：中文撰写、专业克制、去 AI 味；代码注释精炼；不堆砌形容词；每个结论尽量配代码或数据支撑。

## 四、首次启用 GitHub Pages（仓库维护者一次性配置）

> 仓库刚创建时需要手动开一次，之后全自动。

1. 打开仓库 **Settings → Pages**；
2. **Source** 选择 `Deploy from a branch`；
3. 分支选 `gh-pages`，目录 `/ (root)`，保存；
4. 首次 push 到 `main` 后，Actions 会创建 `gh-pages` 分支并部署；若 Actions 无写权限，到 **Settings → Actions → General → Workflow permissions** 勾选 `Read and write permissions`。

站点地址：`https://thomaslwq.github.io/AgentTutorial/`。

## 五、目录约定

```
docs/
  index.md                     # 首页与导航
  module-01-basics/ ...        # 按模块分目录，一章一文件
  appendix/                    # 指南、术语表、FAQ、路线图
examples/
  chXX-topic/
    main.py / app.py           # 最小可运行入口
    requirements.txt           # 本章示例专用依赖
    README.md                  # 运行说明、环境变量、预期输出
```

## 六、提交信息约定

`docs:` 章节内容；`code:` 示例代码；`site:` 站点配置；`fix:` 修复；`chore:` 杂项。
