"""
Debug script to view memory contents.
Run with: python -m tests.debug_memory
"""
import sys
import json
from pathlib import Path

# Add project root to path
project_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(project_root))

from src.storage.json_storage import load_json
from src.agent.memory import get_memory


def view_memory_file(user_id: str = "me"):
    """View the raw memory file contents."""
    print(f"\n=== Memory File for user: {user_id} ===\n")
    data = load_json(f"users/{user_id}/conversations.json", default={})
    
    messages = data.get("messages", [])
    tool_calls = data.get("tool_calls", [])
    last_updated = data.get("last_updated", "Never")
    
    print(f"Total messages in file: {len(messages)}")
    print(f"Total tool calls: {len(tool_calls)}")
    print(f"Last updated: {last_updated}\n")
    
    print("Recent Messages (last 10):")
    for i, msg in enumerate(messages[-10:], 1):
        role = msg.get("role", "unknown")
        content = msg.get("content", "")[:100]  # Truncate long messages
        timestamp = msg.get("timestamp", "")
        print(f"  {i}. [{role}] {content}... (at {timestamp})")
    
    if tool_calls:
        print(f"\nRecent Tool Calls (last 5):")
        for i, tc in enumerate(tool_calls[-5:], 1):
            tool = tc.get("tool", "unknown")
            input_data = str(tc.get("input", ""))[:50]
            print(f"  {i}. {tool}({input_data}...)")
    
    print("\n" + "="*50)


def view_memory_state(user_id: str = "me"):
    """View the current memory state (what's loaded in memory)."""
    print(f"\n=== Memory State for user: {user_id} ===\n")
    memory = get_memory(user_id, window_size=20)
    messages = memory.chat_memory.messages
    
    print(f"Messages in memory (window): {len(messages)}")
    print("\nMemory Contents:")
    for i, msg in enumerate(messages, 1):
        msg_type = msg.__class__.__name__
        content = msg.content[:80] if hasattr(msg, 'content') else str(msg)[:80]
        print(f"  {i}. [{msg_type}] {content}...")
    
    print("\n" + "="*50)


def compare_memory_vs_file(user_id: str = "me"):
    """Compare what's in memory vs what's in the file."""
    print(f"\n=== Memory vs File Comparison for user: {user_id} ===\n")
    
    # Get file data
    file_data = load_json(f"users/{user_id}/conversations.json", default={})
    file_messages = file_data.get("messages", [])
    
    # Get memory
    memory = get_memory(user_id, window_size=20)
    memory_messages = memory.chat_memory.messages
    
    print(f"File: {len(file_messages)} messages")
    print(f"Memory: {len(memory_messages)} messages")
    print(f"Window size: 20")
    print(f"Expected in memory: min({len(file_messages)}, 20) = {min(len(file_messages), 20)}")
    
    if len(memory_messages) == min(len(file_messages), 20):
        print("✅ Memory size matches expected")
    else:
        print(f"⚠️  Memory size mismatch! Expected {min(len(file_messages), 20)}, got {len(memory_messages)}")
    
    print("\n" + "="*50)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Debug memory system")
    parser.add_argument("--user-id", default="me", help="User ID to debug")
    parser.add_argument("--view-file", action="store_true", help="View memory file")
    parser.add_argument("--view-memory", action="store_true", help="View memory state")
    parser.add_argument("--compare", action="store_true", help="Compare memory vs file")
    parser.add_argument("--all", action="store_true", help="Show all views")
    
    args = parser.parse_args()
    
    if args.all or (not args.view_file and not args.view_memory and not args.compare):
        # Default: show all
        view_memory_file(args.user_id)
        view_memory_state(args.user_id)
        compare_memory_vs_file(args.user_id)
    else:
        if args.view_file:
            view_memory_file(args.user_id)
        if args.view_memory:
            view_memory_state(args.user_id)
        if args.compare:
            compare_memory_vs_file(args.user_id)

