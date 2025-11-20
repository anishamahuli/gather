from typing import List, Optional, Tuple
from datetime import datetime
from langchain_openai import ChatOpenAI
from langchain.agents import AgentExecutor, create_react_agent
from langchain.prompts import PromptTemplate
from langchain.memory import ConversationBufferWindowMemory
from src.agent.tools.weather import create_weather_tool, create_forecast_tool
from src.agent.tools.calendar import (
    create_calendar_tool,
    create_get_events_tool,
    create_find_free_times_tool,
    create_create_event_tool,
    create_parse_date_tool
)
from src.agent.tools.n8n_client import create_n8n_tool
from src.agent.types import ToolContext

def build_agent(ctx: ToolContext, memory: Optional[ConversationBufferWindowMemory] = None):
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
    # Create tools with context bound via closures
    tools = [
        create_parse_date_tool(ctx),  # Add date parsing tool first
        create_weather_tool(ctx),
        create_forecast_tool(ctx),
        create_calendar_tool(ctx),
        create_get_events_tool(ctx),
        create_find_free_times_tool(ctx),
        create_create_event_tool(ctx),
        create_n8n_tool(ctx),
    ]
    
    # Get user_id from calendar client
    user_id = ctx.calendar_client.user_id if ctx.calendar_client else "me"
    
    # Build chat history string from memory if available
    chat_history_str = ""
    if memory:
        # Get chat history from memory
        messages = memory.chat_memory.messages
        if messages:
            chat_history_str = "\n\nPrevious conversation:\n"
            for msg in messages[-10:]:  # Show last 10 messages for context
                if hasattr(msg, 'content'):
                    role = "User" if msg.__class__.__name__ == "HumanMessage" else "Assistant"
                    chat_history_str += f"{role}: {msg.content}\n"
    
    # Create a ReAct prompt template with improved instructions
    prompt = PromptTemplate.from_template("""
You are a helpful assistant that can coordinate schedules and activities.

IMPORTANT: The current user ID is "{user_id}". Always use this user_id when calling calendar tools.
{chat_history}

You have access to the following tools:
{tools}

IMPORTANT INSTRUCTIONS:
- When users ask about "warmest day", "best weather", or comparing days, you MUST use the get_weather_forecast tool to get forecast data for multiple days, then analyze and compare them.
- Break down complex requests into steps. For example, "warmest day this week" requires: 1) Get forecast for the week, 2) Compare temperatures, 3) Identify the warmest day.
- Always use the appropriate tool - use get_weather_forecast for multi-day comparisons, use check_weather for current conditions.
- When comparing multiple days, analyze the forecast data you receive and clearly identify which day is best.
- For scheduling requests, follow these EXACT steps:
  - If the user mentions a specific time (e.g., "at 6pm", "at 2pm"), parse it: parse_date("Friday", "18:00:00") for 6pm
  - Calculate end time: if start is 6pm (18:00), end should be 8pm (20:00) for a 2-hour dinner
  - For events with specific times, you DON'T need to call find_available_times - just parse the date and suggest creating the event
  - For events without specific times, use parse_date("Friday", "09:00:00") for start and parse_date("Friday", "18:00:00") for end, then use find_available_times
  - IMPORTANT: When calling parse_date, pass parameters as simple values: parse_date("Friday", "18:00:00") NOT parse_date(date_description="Friday", default_time="18:00:00")
  - After getting dates, suggest the event details to the user (don't create automatically)
  - STOP after providing the suggestion - do NOT call tools repeatedly
- CRITICAL RULES:
  - When calling parse_date, use simple format: parse_date("Friday", "18:00:00") NOT parse_date(date_description="Friday", default_time="18:00:00")
  - If user says "at 6pm" or "at 2pm", convert to 24-hour: 6pm = "18:00:00", 2pm = "14:00:00"
  - Call each tool exactly ONCE per step - do NOT retry or call the same tool multiple times
  - If a tool returns an error, include that error in your final answer and STOP
  - For event creation requests, parse the date/time, then suggest the event details to the user (don't create automatically)
  - Never call create_calendar_event automatically - only suggest times to the user
- Always use parse_date FIRST for day names like "Friday", "Wednesday", "this Friday"
- Examples: 
  - "this Friday at 6pm" → parse_date("this Friday at 6pm") OR parse_date("this Friday", "18:00:00")
  - "Friday" → parse_date("Friday", "09:00:00") for start, parse_date("Friday", "18:00:00") for end

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
    
    # Format prompt with user_id and chat history
    formatted_prompt = prompt.partial(user_id=user_id, chat_history=chat_history_str)
    agent = create_react_agent(llm, tools, formatted_prompt)
    agent_executor = AgentExecutor(
        agent=agent, 
        tools=tools,
        verbose=True,  # Enable verbose to debug - check terminal/console for output
        handle_parsing_errors="Check your output and make sure to respond with a valid json blob, or use the Final Answer action.",
        max_iterations=12,  # Reduced to prevent excessive loops
        max_execution_time=90  # 90 second timeout
    )
    return agent_executor

def run_task(ctx: ToolContext, user_prompt: str, memory: Optional[ConversationBufferWindowMemory] = None) -> tuple[str, list]:
    """
    Run agent task with memory.
    
    Returns:
        tuple: (output_string, tool_calls_list)
    """
    # Add user message to memory before building agent (so it's in context)
    if memory:
        memory.chat_memory.add_user_message(user_prompt)
    
    agent = build_agent(ctx, memory=memory)
    tool_calls = []
    
    try:
        result = agent.invoke({"input": user_prompt})
        output = result.get("output", str(result))
        
        # Extract tool calls from intermediate steps if available
        if isinstance(result, dict):
            # Try to get intermediate_steps
            intermediate_steps = result.get("intermediate_steps", [])
            for step in intermediate_steps:
                try:
                    if len(step) >= 2:
                        # step[0] is usually an AgentAction, step[1] is the observation
                        action = step[0]
                        observation = step[1]
                        
                        tool_name = getattr(action, 'tool', str(action))
                        tool_input = getattr(action, 'tool_input', {})
                        tool_output = str(observation)[:500] if len(str(observation)) > 500 else str(observation)  # Truncate long outputs
                        
                        tool_calls.append({
                            "tool": str(tool_name),
                            "input": str(tool_input),
                            "output": tool_output,
                            "timestamp": datetime.now().isoformat()
                        })
                except Exception as e:
                    # If extraction fails, skip this tool call
                    continue
        
        # Add assistant response to memory
        if memory:
            memory.chat_memory.add_ai_message(output)
        
        return output, tool_calls
    except Exception as e:
        # Handle timeout or other errors gracefully
        error_msg = str(e)
        if "timeout" in error_msg.lower() or "max_execution_time" in error_msg.lower():
            return "I apologize, but the request took too long to process. This might be due to calendar API delays or complex scheduling. Please try again with a simpler request, or check your calendar connection."
        elif "max_iterations" in error_msg.lower():
            return "I apologize, but I reached the maximum number of steps while processing your request. Please try rephrasing your request more simply, or break it into smaller parts."
        else:
            return f"I encountered an error while processing your request: {error_msg}. Please try again or rephrase your request."