"""第11章 · CrewAI 三角色流水线 demo

researcher（研究员）→ writer（文案）→ reviewer（审稿人）顺序执行，
后一个 Task 通过 context=[...] 拿到前一个 Task 的产出。

前置：
    export OPENAI_API_KEY=sk-...
    # 兼容 OpenAI 协议的服务另设：export OPENAI_BASE_URL=https://.../v1
运行：
    pip install -r requirements.txt
    python crew_demo.py
"""
from crewai import Agent, Task, Crew, Process, LLM

# crewai 基于 litellm，model 字符串带 provider 前缀，例如 openai/gpt-4o-mini
# OPENAI_API_KEY / OPENAI_BASE_URL 会被自动读取，无需硬编码
llm = LLM(model="openai/gpt-4o-mini")


researcher = Agent(
    role="资深研究员",
    goal="围绕用户主题归纳 3 个关键事实要点",
    backstory="你擅长从公开常识中快速抓住要点，只列事实、不抒情。",
    llm=llm,
    verbose=False,
    allow_delegation=False,
)

writer = Agent(
    role="技术文案",
    goal="基于研究要点写一段 200 字以内的中文短评",
    backstory="你写东西直接、克制，不堆形容词，不写'在当今时代'这类空话。",
    llm=llm,
    verbose=False,
    allow_delegation=False,
)

reviewer = Agent(
    role="审稿人",
    goal="检查短文是否切题、是否与研究要点一致，给出通过或打回",
    backstory="你只看成品，不重写；结论必须是一行：通过 / 打回：<原因>。",
    llm=llm,
    verbose=False,
    allow_delegation=False,
)

t1 = Task(
    description="围绕主题「{topic}」列出 3 个关键事实要点。",
    expected_output="一个 markdown 无序列表，3 条要点，每条不超过 30 字。",
    agent=researcher,
)

t2 = Task(
    description="基于上一步的要点，写一段 200 字以内的中文短评。",
    expected_output="200 字以内的短评正文，不要标题、不要分点。",
    agent=writer,
    context=[t1],
)

t3 = Task(
    description="审稿：判断短文是否切题、事实是否与要点一致。",
    expected_output="一行结论：通过 / 打回：<原因>。",
    agent=reviewer,
    context=[t2],
)

crew = Crew(
    agents=[researcher, writer, reviewer],
    tasks=[t1, t2, t3],
    process=Process.sequential,
    verbose=False,
)


if __name__ == "__main__":
    result = crew.kickoff(inputs={"topic": "为什么团队应该优先写文档"})
    print("=== Crew 最终产出 ===")
    print(result)
