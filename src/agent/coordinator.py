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
- For scheduling/calendar requests:
  - If user specifies EXACT times (e.g., "dinner at 6 PM", "meeting from 2-3 PM"):
    * Parse the date/time
    * Immediately suggest the event in Final Answer
    * DO NOT call find_available_times - the time is already specified
    * Example: "I'll create a Dinner event on Wednesday at 6 PM to 8 PM. Should I add this to your calendar?"
  - If user says "schedule a meeting" WITHOUT specific time:
    * Use find_available_times to suggest free slots
    * Then ask user which time they prefer
  - NEVER call create_calendar_event without user confirmation
- CRITICAL: After getting all information needed, ALWAYS provide a Final Answer immediately
- DO NOT call the same tool multiple times in a row
- NEVER loop - if you have the information, provide the Final Answer

OUTPUT FORMAT RULES (STRICTLY FOLLOW):
1. After each tool use, you MUST include "Thought:" before your next action
2. When ready to answer, you MUST format exactly as:
   Thought: I now know the final answer
   Final Answer: [your answer here]
3. Do not write explanations or answers without the "Final Answer:" prefix
4. If you write any response to the user, it MUST come after "Final Answer:"

Use the following format (follow this EXACTLY):

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

    # Custom error handler to provide better guidance
    def handle_parsing_error(error) -> str:
        """Custom error handler that reminds the agent of the correct format."""
        return (
            "PARSING ERROR. You must follow this EXACT format:\n"
            "Thought: I now know the final answer\n"
            "Final Answer: [your complete answer to the user]\n\n"
            "Do NOT write any text without the proper prefix (Thought:, Action:, Action Input:, or Final Answer:).\n"
            "If you already have the information needed, provide the Final Answer NOW."
        )

    agent_executor = AgentExecutor(
        agent=agent,
        tools=tools,
        verbose=True,  # Enable verbose to debug - check terminal/console for output
        handle_parsing_errors=handle_parsing_error,
        max_iterations=6,  # Reduced to prevent excessive loops
        max_execution_time=45  # 45 second timeout
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
            return ("I apologize, but the request took too long to process. This might be due to calendar API delays or complex scheduling. Please try again with a simpler request, or check your calendar connection.", [])
        elif "max_iterations" in error_msg.lower() or "iteration limit" in error_msg.lower():
            return ("I apologize, but I reached the maximum number of steps while processing your request. Please try rephrasing your request more simply, or break it into smaller parts.", [])
        else:
            return (f"I encountered an error while processing your request: {error_msg}. Please try again or rephrase your request.", [])