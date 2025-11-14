from langchain.tools import tool
from ..types import ToolContext

def create_calendar_tool(ctx: ToolContext):
    """Factory function to create calendar tool with context bound via closure."""
    @tool("check_availability", return_direct=False)
    def check_availability(user_id: str, date_iso: str) -> str:
        """
        Check if user is free on given ISO date (YYYY-MM-DDThh:mm). Naive day-level check.
        """
        if ctx.calendar_client is None:
            return "Calendar client not configured."
        free = ctx.calendar_client.is_free(date_iso)
        return f"{user_id} is {'free' if free else 'busy'} on {date_iso.split('T')[0]}"
    
    return check_availability