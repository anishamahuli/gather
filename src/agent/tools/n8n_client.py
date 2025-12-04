from langchain.tools import tool
from ..types import ToolContext
import json

def create_n8n_tool(ctx: ToolContext):
    """Factory function to create n8n tool with context bound via closure."""
    @tool("trigger_n8n", return_direct=False)
    def trigger_n8n(payload_json: str) -> str:
        """
        Trigger an n8n webhook with arbitrary JSON payload. Args: payload_json string.
        """
        if ctx.n8n_client is None:
            return "n8n client not configured."
        try:
            payload = json.loads(payload_json)
        except json.JSONDecodeError:
            return "Invalid JSON."
        result = ctx.n8n_client.trigger(payload)
        return f"n8n response: {result}"
    
    return trigger_n8n
