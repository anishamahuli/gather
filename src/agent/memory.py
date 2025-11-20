"""
Memory management for the agent.
Uses ConversationBufferWindowMemory with file-based JSON storage.
"""
from datetime import datetime
from typing import Optional, List, Dict, Any
from langchain.memory import ConversationBufferWindowMemory
from langchain.schema import BaseMessage, HumanMessage, AIMessage
from src.storage.json_storage import load_json, save_json


def get_memory(user_id: str, window_size: int = 20) -> ConversationBufferWindowMemory:
    """
    Load or create memory for a user.
    
    Args:
        user_id: User identifier
        window_size: Number of messages to keep in memory (default 20)
    
    Returns:
        ConversationBufferWindowMemory instance with loaded history
    """
    memory = ConversationBufferWindowMemory(
        k=window_size,
        return_messages=True,
        memory_key="chat_history"
    )
    
    # Load conversation history from file
    history_path = f"users/{user_id}/conversations.json"
    history_data = load_json(history_path, default={"messages": [], "tool_calls": []})
    
    messages = history_data.get("messages", [])
    tool_calls = history_data.get("tool_calls", [])
    
    # Load only the last window_size messages into memory
    # (The memory will automatically manage the window, but we load recent ones)
    recent_messages = messages[-window_size:] if len(messages) > window_size else messages
    
    # Add messages to memory
    for msg_data in recent_messages:
        role = msg_data.get("role")
        content = msg_data.get("content", "")
        timestamp = msg_data.get("timestamp", "")
        
        if role == "user":
            memory.chat_memory.add_user_message(content)
        elif role == "assistant":
            memory.chat_memory.add_ai_message(content)
    
    return memory


def save_memory(
    user_id: str, 
    memory: ConversationBufferWindowMemory,
    tool_calls: Optional[List[Dict[str, Any]]] = None,
    max_messages_in_file: int = 100
) -> None:
    """
    Save memory to file, keeping only recent messages.
    
    Args:
        user_id: User identifier
        memory: The memory object to save
        tool_calls: Optional list of tool calls to store
        max_messages_in_file: Maximum messages to keep in file (default 100)
    """
    history_path = f"users/{user_id}/conversations.json"
    
    # Load existing history
    existing_data = load_json(history_path, default={"messages": [], "tool_calls": []})
    all_messages = existing_data.get("messages", [])
    all_tool_calls = existing_data.get("tool_calls", [])
    
    # Get all messages from memory (these are the last 20 due to window)
    memory_messages = memory.chat_memory.messages
    
    # Convert LangChain messages to dict format
    memory_messages_dict = []
    for msg in memory_messages:
        if isinstance(msg, HumanMessage):
            memory_messages_dict.append({
                "role": "user",
                "content": msg.content,
                "timestamp": datetime.now().isoformat()
            })
        elif isinstance(msg, AIMessage):
            memory_messages_dict.append({
                "role": "assistant",
                "content": msg.content,
                "timestamp": datetime.now().isoformat()
            })
    
    # Merge strategy: Replace the last N messages (where N = window size) with memory content
    # This ensures we don't duplicate and keep the most recent accurate state
    window_size = 20  # Match the window size
    if len(all_messages) >= window_size:
        # Remove last window_size messages and replace with memory content
        all_messages = all_messages[:-window_size] + memory_messages_dict
    else:
        # If we have fewer messages than window, just replace all
        all_messages = memory_messages_dict
    
    # Keep only last max_messages_in_file
    if len(all_messages) > max_messages_in_file:
        all_messages = all_messages[-max_messages_in_file:]
    
    # Add tool calls if provided
    if tool_calls:
        all_tool_calls.extend(tool_calls)
        # Keep only recent tool calls (last 200)
        if len(all_tool_calls) > 200:
            all_tool_calls = all_tool_calls[-200:]
    
    # Save to file
    save_json(history_path, {
        "messages": all_messages,
        "tool_calls": all_tool_calls,
        "last_updated": datetime.now().isoformat()
    })


def clear_memory(user_id: str) -> None:
    """Clear all memory for a user."""
    history_path = f"users/{user_id}/conversations.json"
    save_json(history_path, {"messages": [], "tool_calls": [], "last_updated": datetime.now().isoformat()})

