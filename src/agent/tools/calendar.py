from langchain.tools import tool
from ..types import ToolContext
from datetime import datetime, timedelta

def create_calendar_tool(ctx: ToolContext):
    """Factory function to create calendar tool with context bound via closure."""
    @tool("check_availability", return_direct=False)
    def check_availability(user_id: str = "", date_iso: str = "") -> str:
        """
        Check if user is free on a given date and time.
        Args:
            user_id: User ID to check (optional, defaults to the current user)
            date_iso: Date and time in ISO format (YYYY-MM-DDTHH:MM:SS) or just date (YYYY-MM-DD). 
                     If empty, you must provide a valid ISO date string. Examples: "2025-11-15T14:00:00" or "2025-11-15T09:00:00"
        Returns: Whether the user is free or busy on that date/time.
        """
        if ctx.calendar_client is None:
            return "Calendar client not configured."
        
        # Use user_id from calendar client if not provided
        if not user_id or user_id.strip() == "":
            user_id = ctx.calendar_client.user_id
        
        if not date_iso or date_iso.strip() == "":
            return "Error: date_iso parameter is required. Provide date in ISO format like '2025-11-15T14:00:00'"
        
        try:
            free = ctx.calendar_client.is_free(date_iso)
            return f"{user_id} is {'free' if free else 'busy'} on {date_iso.split('T')[0]}"
        except Exception as e:
            return f"Error checking availability: {str(e)}. Make sure date_iso is in correct ISO format (YYYY-MM-DDTHH:MM:SS)"
    
    return check_availability

def create_get_events_tool(ctx: ToolContext):
    """Factory function to create get calendar events tool."""
    @tool("get_calendar_events", return_direct=False)
    def get_calendar_events(user_id: str = "", start_date: str = "", end_date: str = "") -> str:
        """
        Get calendar events for a user in a date range.
        Args:
            user_id: User ID (optional, defaults to the current user)
            start_date: Start date in ISO format (YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS). If empty, uses today.
            end_date: End date in ISO format. If empty, uses 7 days from start_date.
        Returns: List of events with dates, times, and titles.
        """
        if ctx.calendar_client is None:
            return "Calendar client not configured."
        
        # Use user_id from calendar client if not provided
        if not user_id or user_id.strip() == "":
            user_id = ctx.calendar_client.user_id
        
        try:
            events = ctx.calendar_client.get_events(
                start_date=start_date if start_date else None,
                end_date=end_date if end_date else None
            )
            
            if not events:
                return f"No events found for {user_id} in the specified date range."
            
            result = f"Calendar events for {user_id}:\n"
            for start, end, title in events:
                result += f"- {title}: {start} to {end}\n"
            
            return result
        except Exception as e:
            return f"Error getting calendar events: {str(e)}"
    
    return get_calendar_events

def create_find_free_times_tool(ctx: ToolContext):
    """Factory function to create find free times tool."""
    @tool("find_available_times", return_direct=False)
    def find_available_times(user_id: str = "", start_date: str = "", end_date: str = "", duration_minutes: str = "60") -> str:
        """
        Find available time slots for a user in a date range. Use this tool when scheduling activities.
        CRITICAL: You MUST convert day names (like "Friday", "Wednesday") to actual ISO dates before calling this tool.
        Args:
            user_id: User ID (optional, defaults to the current user)
            start_date: Start date in ISO format (YYYY-MM-DDTHH:MM:SS). REQUIRED. Example: "2025-11-15T09:00:00" for Friday at 9am. 
                       You must calculate the actual date - if user says "Friday", calculate which Friday and format as ISO.
            end_date: End date in ISO format (YYYY-MM-DDTHH:MM:SS). REQUIRED. Example: "2025-11-15T18:00:00" for Friday at 6pm.
                      For a single day, set this to the same day but later time (e.g., end of day like 18:00:00).
            duration_minutes: Duration of the slot needed in minutes (default "60")
        Returns: List of available time slots.
        """
        if ctx.calendar_client is None:
            return "Calendar client not configured."
        
        # Parse input if it's passed as a single string (LangChain sometimes does this)
        import re
        # Check if user_id contains comma-separated values (LangChain passes as "me", "date1", "date2", "60")
        if user_id and "," in user_id and start_date == "":
            # Try to parse comma-separated format: "me", "2025-11-21T18:00:00", "2025-11-21T20:00:00", "60"
            parts = [p.strip().strip('"').strip("'") for p in user_id.split(',')]
            if len(parts) >= 4:
                user_id = parts[0]
                start_date = parts[1]
                end_date = parts[2]
                duration_minutes = parts[3]
            elif len(parts) >= 3:
                user_id = parts[0]
                start_date = parts[1]
                end_date = parts[2]
            elif len(parts) >= 2:
                user_id = parts[0]
                start_date = parts[1]
        
        # Also try to parse named parameter format: user_id="me", start_date="...", end_date="..."
        if user_id and "start_date" in str(user_id) and start_date == "":
            match = re.search(r'start_date=["\']([^"\']+)["\']', str(user_id))
            if match:
                start_date = match.group(1)
            match = re.search(r'end_date=["\']([^"\']+)["\']', str(user_id))
            if match:
                end_date = match.group(1)
            match = re.search(r'duration_minutes=["\']([^"\']+)["\']', str(user_id))
            if match:
                duration_minutes = match.group(1)
            match = re.search(r'user_id=["\']([^"\']+)["\']', str(user_id))
            if match:
                user_id = match.group(1)
        
        # Use user_id from calendar client if not provided
        if not user_id or user_id.strip() == "":
            user_id = ctx.calendar_client.user_id
        
        # Debug: Check what we received
        if not start_date or start_date.strip() == "":
            return f"Error: start_date is REQUIRED but received empty value. Received parameters: user_id='{user_id}', start_date='{start_date}', end_date='{end_date}'. Make sure to pass start_date as a separate parameter, not as part of a string."
        
        if not end_date or end_date.strip() == "":
            return f"Error: end_date is REQUIRED but received empty value. Received parameters: user_id='{user_id}', start_date='{start_date}', end_date='{end_date}'. Make sure to pass end_date as a separate parameter, not as part of a string."
        
        try:
            duration = int(duration_minutes)
            slots = ctx.calendar_client.find_free_slots(start_date, end_date, duration)
            
            if not slots:
                return f"No available time slots found for {user_id} between {start_date} and {end_date}."
            
            result = f"Available time slots for {user_id}:\n"
            for start, end in slots[:5]:  # Show top 5
                try:
                    start_dt = datetime.fromisoformat(start.replace('Z', '+00:00'))
                    end_dt = datetime.fromisoformat(end.replace('Z', '+00:00'))
                    result += f"- {start_dt.strftime('%A, %B %d at %I:%M %p')} to {end_dt.strftime('%I:%M %p')}\n"
                except:
                    result += f"- {start} to {end}\n"
            
            return result
        except Exception as e:
            return f"Error finding available times: {str(e)}. Make sure dates are in ISO format (YYYY-MM-DDTHH:MM:SS)"
    
    return find_available_times

def create_create_event_tool(ctx: ToolContext):
    """Factory function to create calendar event tool (requires confirmation)."""
    @tool("create_calendar_event", return_direct=False)
    def create_calendar_event(user_id: str = "", title: str = "", start_iso: str = "", end_iso: str = "", 
                              description: str = "", location: str = "") -> str:
        """
        Create a calendar event. NOTE: This tool should only be called after user approval.
        Args:
            user_id: User ID (optional, defaults to the current user)
            title: Event title
            start_iso: Start time in ISO format (YYYY-MM-DDTHH:MM:SS)
            end_iso: End time in ISO format (YYYY-MM-DDTHH:MM:SS)
            description: Event description (optional)
            location: Event location (optional)
        Returns: Confirmation message with event ID.
        """
        if ctx.calendar_client is None:
            return "Calendar client not configured."
        
        # Use user_id from calendar client if not provided
        if not user_id or user_id.strip() == "":
            user_id = ctx.calendar_client.user_id
        
        try:
            event_id = ctx.calendar_client.create_event(title, start_iso, end_iso, description, location)
            if event_id:
                return f"Event '{title}' created successfully for {user_id} on {start_iso.split('T')[0]}. Event ID: {event_id}"
            else:
                return f"Failed to create event '{title}' for {user_id}."
        except Exception as e:
            return f"Error creating calendar event: {str(e)}"
    
    return create_calendar_event

def create_parse_date_tool(ctx: ToolContext):
    """Factory function to create date parsing tool."""
    @tool("parse_date", return_direct=False)
    def parse_date(date_description: str, default_time: str = "09:00:00") -> str:
        """
        Convert natural language date descriptions to ISO format dates.
        Use this tool FIRST when users mention days like "Friday", "Wednesday", "this Friday", etc.
        
        Args:
            date_description: Natural language date (e.g., "Friday", "this Friday", "next Wednesday", "Wednesday at 2pm", "today", "tomorrow")
            default_time: Default time in HH:MM:SS format (default "09:00:00" for 9am). IMPORTANT: Always use this parameter when you want a specific time.
        
        Returns: ISO format date string (YYYY-MM-DDTHH:MM:SS)
        
        Examples:
            - parse_date("Friday", "09:00:00") → Returns the upcoming Friday at 9am
            - parse_date("Friday", "18:00:00") → Returns the upcoming Friday at 6pm
            - parse_date("this Friday") → Returns this week's Friday at 9am (default)
            - parse_date("Wednesday at 2pm") → Returns upcoming Wednesday at 14:00:00
        """
        try:
            import re
            today = datetime.now()
            
            # Handle case where LangChain passes parameters as a string like: date_description="this Friday", default_time="09:00:00"
            # This happens when the agent writes the action input with parameter names
            if "date_description=" in date_description or "default_time=" in str(default_time):
                # Try to extract parameters from the string format
                match = re.search(r'date_description=["\']([^"\']+)["\']', str(date_description))
                if match:
                    date_description = match.group(1)
                
                # Check if default_time is also in the date_description string
                match = re.search(r'default_time=["\']([^"\']+)["\']', str(date_description))
                if match:
                    default_time = match.group(1)
                else:
                    # Also check the default_time parameter itself
                    match = re.search(r'default_time=["\']([^"\']+)["\']', str(default_time))
                    if match:
                        default_time = match.group(1)
            
            # Handle case where LangChain passes both as a single string: "Friday", "18:00:00"
            # Check if date_description contains both the date and time separated by comma
            if "," in date_description and '"' in date_description and "date_description=" not in date_description:
                parts = [p.strip().strip('"') for p in date_description.split(',')]
                if len(parts) >= 2:
                    date_description = parts[0]
                    default_time = parts[1] if parts[1] else default_time
            
            date_lower = date_description.lower().strip()
            
            # IMPORTANT: Always use the default_time parameter - it's passed by the agent
            # Ensure default_time is set
            if not default_time or default_time.strip() == "":
                default_time = "09:00:00"
            time_str = default_time.strip()
            
            # Ensure time_str is in HH:MM:SS format
            if len(time_str.split(':')) == 2:
                time_str = time_str + ":00"
            
            # Handle "today"
            if date_lower == "today":
                if "at" in date_description:
                    # Try to extract time from original
                    parts = date_description.lower().split("at")
                    if len(parts) > 1:
                        time_part = parts[1].strip()
                        time_str = _parse_time(time_part)
                return f"{today.strftime('%Y-%m-%d')}T{time_str}"
            
            # Handle "tomorrow"
            if date_lower == "tomorrow":
                if "at" in date_description:
                    parts = date_description.lower().split("at")
                    if len(parts) > 1:
                        time_part = parts[1].strip()
                        time_str = _parse_time(time_part)
                tomorrow = today + timedelta(days=1)
                return f"{tomorrow.strftime('%Y-%m-%d')}T{time_str}"
            
            # Handle day names (Monday, Tuesday, etc.)
            day_names = {
                'monday': 0, 'tuesday': 1, 'wednesday': 2, 'thursday': 3,
                'friday': 4, 'saturday': 5, 'sunday': 6
            }
            
            # Extract day name
            day_name = None
            for day, day_num in day_names.items():
                if day in date_lower:
                    day_name = day
                    # Check if there's a time specified in the date_description itself (e.g., "Friday at 2pm")
                    if "at" in date_lower:
                        parts = date_lower.split("at")
                        if len(parts) > 1:
                            time_part = parts[1].strip()
                            time_str = _parse_time(time_part)
                    # Otherwise, use the default_time parameter that was passed
                    break
            
            if day_name is None:
                # Try to parse as a date string
                try:
                    # Try common date formats
                    parsed = datetime.strptime(date_description, "%Y-%m-%d")
                    return f"{parsed.strftime('%Y-%m-%d')}T{time_str}"
                except:
                    return f"Error: Could not parse date '{date_description}'. Use day names like 'Friday', 'Wednesday', or ISO dates like '2025-11-15'."
            
            # Calculate the target day
            target_day_num = day_names[day_name]
            current_day_num = today.weekday()
            
            # Check if "next" is specified
            is_next = "next" in date_lower
            is_this = "this" in date_lower
            
            days_ahead = target_day_num - current_day_num
            
            if days_ahead < 0:  # Day already passed this week
                if is_this:
                    days_ahead += 7  # This week's occurrence (next occurrence)
                else:
                    days_ahead += 7  # Next week
            elif days_ahead == 0:  # Today is the target day
                if is_next:
                    days_ahead = 7  # Next week
                else:
                    days_ahead = 0  # Today
            else:  # Day is later this week
                if is_next:
                    days_ahead += 7  # Next week
                # else: use this week's occurrence
            
            target_date = today + timedelta(days=days_ahead)
            # Format the time string properly (ensure it's HH:MM:SS)
            if len(time_str.split(':')) == 2:
                time_str = time_str + ":00"
            return f"{target_date.strftime('%Y-%m-%d')}T{time_str}"
            
        except Exception as e:
            return f"Error parsing date '{date_description}': {str(e)}. Use day names like 'Friday' or ISO dates like '2025-11-15T09:00:00'."
    
    return parse_date

def _parse_time(time_str: str) -> str:
    """Parse time string to HH:MM:SS format."""
    time_str = time_str.strip().lower()
    
    # Handle "2pm", "2 pm", "14:00", etc.
    if "pm" in time_str or "am" in time_str:
        # 12-hour format
        time_str = time_str.replace(" ", "").replace(":", "")
        if "pm" in time_str:
            hour = int(time_str.replace("pm", ""))
            if hour != 12:
                hour += 12
            time_str = time_str.replace("pm", "")
        else:
            hour = int(time_str.replace("am", ""))
            if hour == 12:
                hour = 0
            time_str = time_str.replace("am", "")
        return f"{hour:02d}:00:00"
    elif ":" in time_str:
        # 24-hour format like "14:00"
        parts = time_str.split(":")
        hour = int(parts[0])
        minute = int(parts[1]) if len(parts) > 1 else 0
        return f"{hour:02d}:{minute:02d}:00"
    else:
        # Just a number, assume hour
        hour = int(time_str)
        return f"{hour:02d}:00:00"