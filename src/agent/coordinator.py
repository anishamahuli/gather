from typing import List
from langchain_openai import ChatOpenAI
from langchain.agents import AgentExecutor, create_react_agent
from langchain.prompts import PromptTemplate
from src.agent.tools.weather import create_weather_tool
from src.agent.tools.calendar import create_calendar_tool
from src.agent.tools.n8n_client import create_n8n_tool
from src.agent.types import ToolContext

def build_agent(ctx: ToolContext):
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
    # Create tools with context bound via closures
    tools = [
        create_weather_tool(ctx),
        create_calendar_tool(ctx),
        create_n8n_tool(ctx),
    ]
    
    # Create a ReAct prompt template
    prompt = PromptTemplate.from_template("""
You are a helpful assistant that can coordinate schedules and activities.

You have access to the following tools:
{tools}

Use the following format:

Question: the input question you must answer
Thought: you should always think about what to do
Action: the action to take, should be one of [{tool_names}]
Action Input: the input to the action
Observation: the result of the action
... (this Thought/Action/Action Input/Observation can repeat N times)
Thought: I now know the final answer
Final Answer: the final answer to the original input question

Begin!

Question: {input}
Thought:{agent_scratchpad}
""")
    
    agent = create_react_agent(llm, tools, prompt)
    agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=False, handle_parsing_errors=True)
    return agent_executor

def run_task(ctx: ToolContext, user_prompt: str) -> str:
    agent = build_agent(ctx)
    result = agent.invoke({"input": user_prompt})
    return result.get("output", str(result))