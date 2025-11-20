"""
Monitor memory system performance.
Run with: python -m tests.monitor_memory_performance
"""
import sys
import time
import json
from pathlib import Path
from typing import Dict, List

# Add project root to path
project_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(project_root))

from src.agent.memory import get_memory, save_memory, clear_memory
from src.storage.json_storage import load_json


def measure_load_time(user_id: str, iterations: int = 5) -> Dict[str, float]:
    """Measure memory loading performance."""
    times = []
    for _ in range(iterations):
        start = time.time()
        memory = get_memory(user_id, window_size=20)
        load_time = time.time() - start
        times.append(load_time)
    
    return {
        "avg": sum(times) / len(times),
        "min": min(times),
        "max": max(times),
        "all": times
    }


def measure_save_time(user_id: str, message_count: int = 10) -> Dict[str, float]:
    """Measure memory saving performance."""
    clear_memory(user_id)
    memory = get_memory(user_id, window_size=20)
    
    # Add messages
    for i in range(message_count):
        memory.chat_memory.add_user_message(f"Test message {i}")
        memory.chat_memory.add_ai_message(f"Test response {i}")
    
    # Measure save time
    start = time.time()
    save_memory(user_id, memory, max_messages_in_file=100)
    save_time = time.time() - start
    
    return {"save_time": save_time, "message_count": message_count}


def get_file_stats(user_id: str) -> Dict[str, any]:
    """Get statistics about the memory file."""
    data = load_json(f"users/{user_id}/conversations.json", default={})
    messages = data.get("messages", [])
    tool_calls = data.get("tool_calls", [])
    
    # Calculate file size
    file_path = Path(__file__).resolve().parents[1] / "data" / "users" / user_id / "conversations.json"
    file_size = file_path.stat().st_size if file_path.exists() else 0
    
    # Calculate average message length
    avg_msg_length = sum(len(msg.get("content", "")) for msg in messages) / len(messages) if messages else 0
    
    return {
        "message_count": len(messages),
        "tool_call_count": len(tool_calls),
        "file_size_bytes": file_size,
        "file_size_kb": file_size / 1024,
        "file_size_mb": file_size / (1024 * 1024),
        "avg_message_length": avg_msg_length,
        "last_updated": data.get("last_updated", "Never")
    }


def measure_memory_usage(user_id: str) -> Dict[str, any]:
    """Measure memory usage (in-memory vs file)."""
    memory = get_memory(user_id, window_size=20)
    memory_messages = memory.chat_memory.messages
    
    file_data = load_json(f"users/{user_id}/conversations.json", default={})
    file_messages = file_data.get("messages", [])
    
    return {
        "memory_messages": len(memory_messages),
        "file_messages": len(file_messages),
        "window_size": 20,
        "expected_in_memory": min(len(file_messages), 20),
        "matches": len(memory_messages) == min(len(file_messages), 20)
    }


def run_performance_report(user_id: str = "me"):
    """Run a complete performance report."""
    print("=" * 60)
    print("Memory Performance Report")
    print("=" * 60)
    print(f"User ID: {user_id}\n")
    
    # File Statistics
    print("📁 File Statistics:")
    file_stats = get_file_stats(user_id)
    print(f"  Messages in file: {file_stats['message_count']}")
    print(f"  Tool calls: {file_stats['tool_call_count']}")
    print(f"  File size: {file_stats['file_size_kb']:.2f} KB ({file_stats['file_size_mb']:.3f} MB)")
    print(f"  Avg message length: {file_stats['avg_message_length']:.0f} chars")
    print(f"  Last updated: {file_stats['last_updated']}")
    print()
    
    # Memory Usage
    print("💾 Memory Usage:")
    mem_usage = measure_memory_usage(user_id)
    print(f"  Messages in memory: {mem_usage['memory_messages']}")
    print(f"  Messages in file: {mem_usage['file_messages']}")
    print(f"  Window size: {mem_usage['window_size']}")
    print(f"  Expected in memory: {mem_usage['expected_in_memory']}")
    if mem_usage['matches']:
        print("  ✅ Memory size matches expected")
    else:
        print("  ⚠️  Memory size mismatch!")
    print()
    
    # Load Performance
    print("⏱️  Load Performance:")
    load_perf = measure_load_time(user_id, iterations=5)
    print(f"  Average load time: {load_perf['avg']*1000:.2f} ms")
    print(f"  Min load time: {load_perf['min']*1000:.2f} ms")
    print(f"  Max load time: {load_perf['max']*1000:.2f} ms")
    if load_perf['avg'] < 0.1:
        print("  ✅ Load time is fast (< 100ms)")
    elif load_perf['avg'] < 0.5:
        print("  ⚠️  Load time is acceptable (< 500ms)")
    else:
        print("  ❌ Load time is slow (> 500ms)")
    print()
    
    # Save Performance
    print("💾 Save Performance:")
    save_perf = measure_save_time(user_id, message_count=10)
    print(f"  Save time: {save_perf['save_time']*1000:.2f} ms")
    print(f"  Messages saved: {save_perf['message_count']}")
    if save_perf['save_time'] < 0.1:
        print("  ✅ Save time is fast (< 100ms)")
    else:
        print("  ⚠️  Save time could be optimized")
    print()
    
    # Recommendations
    print("💡 Recommendations:")
    if file_stats['file_size_mb'] > 1:
        print("  ⚠️  File size is large (> 1MB). Consider reducing max_messages_in_file.")
    if load_perf['avg'] > 0.5:
        print("  ⚠️  Load time is slow. Consider loading only window_size messages.")
    if mem_usage['file_messages'] > 200:
        print("  ⚠️  Many messages in file. Consider implementing summarization.")
    if not mem_usage['matches']:
        print("  ⚠️  Memory size mismatch detected. Check memory loading logic.")
    if not any([file_stats['file_size_mb'] > 1, load_perf['avg'] > 0.5, mem_usage['file_messages'] > 200, not mem_usage['matches']]):
        print("  ✅ All metrics look good!")
    
    print()
    print("=" * 60)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Monitor memory performance")
    parser.add_argument("--user-id", default="me", help="User ID to monitor")
    args = parser.parse_args()
    
    run_performance_report(args.user_id)

