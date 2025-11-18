import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

import streamlit as st
from src.utils.config import load_config, get_env
from src.integrations.weather_api import OpenWeatherClient
from src.integrations.n8n_api import N8NClient
from src.integrations.calendar_api import CalendarClient
from src.integrations.google_auth import is_authenticated, get_authorization_url, complete_authorization_with_code
from src.agent.types import ToolContext
from src.agent.coordinator import run_task
import re
from urllib.parse import parse_qs, urlparse

# Page config
st.set_page_config(
    page_title="Gather - Coordination Assistant",
    page_icon="🤝",
    layout="wide"
)

# Custom CSS to make user message icon green
# Using multiple approaches to ensure it works
st.markdown("""
<style>
    /* Approach 1: Target all chat message avatars and apply green color directly */
    [data-testid="stChatMessage"] [data-testid="stChatMessageAvatar"] svg {
        color: #00cc00 !important;
    }
    
    /* Approach 2: Target SVG paths and shapes directly */
    [data-testid="stChatMessage"] [data-testid="stChatMessageAvatar"] svg path,
    [data-testid="stChatMessage"] [data-testid="stChatMessageAvatar"] svg circle,
    [data-testid="stChatMessage"] [data-testid="stChatMessageAvatar"] svg rect {
        fill: #00cc00 !important;
        stroke: #00cc00 !important;
    }
    
    /* Approach 3: Use CSS filter to transform red to green (hue rotation) */
    /* This will change any red-colored icon to green */
    [data-testid="stChatMessage"] [data-testid="stChatMessageAvatar"] svg {
        filter: hue-rotate(120deg) saturate(1.3) brightness(1.1) !important;
    }
    
    /* Approach 4: More aggressive - target by class if it exists */
    .stChatMessage [data-testid="stChatMessageAvatar"] svg {
        filter: hue-rotate(120deg) !important;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if "messages" not in st.session_state:
    st.session_state.messages = []

if "pending_event" not in st.session_state:
    st.session_state.pending_event = None

if "auth_code" not in st.session_state:
    st.session_state.auth_code = None

if "tool_context" not in st.session_state:
    # Initialize configuration
    load_config()
    ow_key = get_env("OPENAI_API_KEY")
    w_key = get_env("OPENWEATHERMAP_API_KEY")
    n8n_url = get_env("N8N_WEBHOOK_URL")
    
    # Create clients
    weather_client = OpenWeatherClient(api_key=w_key) if w_key else None
    n8n_client = N8NClient(webhook_url=n8n_url) if n8n_url else None
    calendar_client = CalendarClient(user_id="me")
    
    # Create tool context
    st.session_state.tool_context = ToolContext(
        weather_client=weather_client,
        n8n_client=n8n_client,
        calendar_client=calendar_client,
    )
    
    # Check for required API key
    if not ow_key:
        st.warning("⚠️ OPENAI_API_KEY missing. The agent will not be able to run.")

# Sidebar for settings
with st.sidebar:
    st.header("Settings")
    user_id = st.text_input("User ID", value="me", help="User ID for calendar access")
    
    # Update calendar client if user ID changes
    if user_id != st.session_state.tool_context.calendar_client.user_id:
        st.session_state.tool_context.calendar_client = CalendarClient(user_id=user_id)
    
    st.divider()
    st.subheader("Google Calendar")
    
    # Check authentication status
    is_auth = is_authenticated(user_id)
    
    # Check if we have an authorization code in the URL (from OAuth redirect)
    query_params = st.query_params
    auth_code_from_url = query_params.get("code", None)
    
    # If we have a code in the URL, automatically complete authorization
    if auth_code_from_url and not is_auth:
        try:
            with st.spinner("Completing authorization..."):
                complete_authorization_with_code(user_id, auth_code_from_url, redirect_uri="http://localhost:8501")
                # Reinitialize calendar client
                st.session_state.tool_context.calendar_client = CalendarClient(user_id=user_id)
                # Remove code from URL
                st.query_params.clear()
                st.success("✅ Successfully connected to Google Calendar!")
                st.rerun()
        except Exception as e:
            st.error(f"Error completing authorization: {str(e)}")
            # Remove code from URL to prevent retry loop
            st.query_params.clear()
    
    if is_auth:
        st.success("✅ Connected to Google Calendar")
        if st.button("Disconnect Google Calendar"):
            # Delete token file
            from src.integrations.google_auth import get_token_path
            import os
            token_path = get_token_path(user_id)
            if token_path.exists():
                os.remove(token_path)
            # Reinitialize calendar client
            st.session_state.tool_context.calendar_client = CalendarClient(user_id=user_id)
            st.rerun()
    else:
        st.warning("⚠️ Not connected to Google Calendar")
        
        # OAuth flow
        if "auth_url" not in st.session_state or st.button("Connect Google Calendar"):
            try:
                auth_url = get_authorization_url(user_id)
                st.session_state.auth_url = auth_url
            except Exception as e:
                st.error(f"Error: {str(e)}")
                st.session_state.auth_url = None
        
        if "auth_url" in st.session_state and st.session_state.auth_url:
            st.markdown("**Step 1:** Click the link below to authorize:")
            st.markdown(f"[🔗 Authorize Google Calendar]({st.session_state.auth_url})")
            st.markdown("**Step 2:** After authorizing, you'll be automatically redirected back here and connected.")
            st.info("💡 After clicking 'Continue' on Google's page, you'll be redirected back and the connection will complete automatically.")
    
    st.divider()
    st.subheader("Status")
    st.write("✅ Agent ready")
    if st.session_state.tool_context.weather_client:
        st.write("✅ Weather API configured")
    else:
        st.write("⚠️ Weather API not configured")
    
    if st.session_state.tool_context.n8n_client:
        st.write("✅ n8n configured")
    else:
        st.write("⚠️ n8n not configured")
    
    calendar_status = "✅ Google Calendar" if is_auth else "⚠️ Local Calendar (JSON)"
    st.write(calendar_status)
    
    st.divider()
    if st.button("Clear Chat History"):
        st.session_state.messages = []
        st.session_state.pending_event = None
        st.rerun()

# Main UI
st.title("🤝 Gather - Coordination Assistant")
st.caption("Ask me to coordinate schedules, check weather, and more!")

# Display chat history
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.write(message["content"])

# Event confirmation UI (if pending)
if st.session_state.pending_event:
    st.info("📅 Event Pending Approval")
    event = st.session_state.pending_event
    col1, col2 = st.columns(2)
    
    with col1:
        st.write(f"**Title:** {event.get('title', 'N/A')}")
        st.write(f"**Date:** {event.get('date', 'N/A')}")
        st.write(f"**Time:** {event.get('time', 'N/A')}")
        if event.get('location'):
            st.write(f"**Location:** {event.get('location')}")
        if event.get('description'):
            st.write(f"**Description:** {event.get('description')}")
    
    with col2:
        if st.button("✅ Approve & Create Event", type="primary", use_container_width=True):
            # Extract event details and create
            try:
                from datetime import datetime
                # Parse the date/time from the event
                date_str = event.get('date', '')
                time_str = event.get('time', '')
                # Combine into ISO format (simplified - you may need to adjust)
                start_iso = f"{date_str}T{time_str}:00"
                # Assume 2 hour duration for hikes
                from datetime import timedelta
                start_dt = datetime.fromisoformat(start_iso)
                end_dt = start_dt + timedelta(hours=2)
                end_iso = end_dt.isoformat()
                
                event_id = st.session_state.tool_context.calendar_client.create_event(
                    title=event.get('title', 'Event'),
                    start_iso=start_iso,
                    end_iso=end_iso,
                    description=event.get('description', ''),
                    location=event.get('location', '')
                )
                
                if event_id:
                    st.success(f"✅ Event created successfully! Event ID: {event_id}")
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": f"Event '{event.get('title')}' has been created in your calendar!"
                    })
                else:
                    st.error("Failed to create event.")
                
                st.session_state.pending_event = None
                st.rerun()
            except Exception as e:
                st.error(f"Error creating event: {str(e)}")
        
        if st.button("❌ Reject", use_container_width=True):
            st.session_state.pending_event = None
            st.rerun()

# Chat input
if prompt := st.chat_input("Type your request here..."):
    # Add user message to history
    st.session_state.messages.append({"role": "user", "content": prompt})
    
    # Display user message
    with st.chat_message("user"):
        st.write(prompt)
    
    # Get agent response
    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            try:
                result = run_task(st.session_state.tool_context, prompt)
                st.write(result)
                
                # Check if agent response contains event creation suggestion
                # Look for patterns that indicate the agent is suggesting an event
                if any(keyword in result.lower() for keyword in ["suggest", "recommend", "best time", "would be"]):
                    # Try to extract event details from the response
                    # This is a simplified extraction - in production, you'd want more robust parsing
                    # or have the agent return structured data
                    time_match = re.search(r'(\d{1,2}):(\d{2})\s*(?:am|pm|AM|PM)?', result, re.IGNORECASE)
                    day_match = re.search(r'(monday|tuesday|wednesday|thursday|friday|saturday|sunday)', result, re.IGNORECASE)
                    
                    # Only create pending event if we found time information
                    if time_match or day_match:
                        from datetime import datetime, timedelta
                        # Try to determine the date
                        today = datetime.now()
                        if day_match:
                            day_name = day_match.group(1).lower()
                            days_ahead = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday'].index(day_name)
                            target_date = today + timedelta(days=(days_ahead - today.weekday()) % 7)
                            date_str = target_date.strftime('%Y-%m-%d')
                        else:
                            date_str = today.strftime('%Y-%m-%d')
                        
                        time_str = time_match.group(0) if time_match else "14:00"
                        # Convert to 24-hour format if needed
                        if 'pm' in time_str.lower() or 'am' in time_str.lower():
                            # Simple conversion (you might want to improve this)
                            hour, minute = time_match.groups()[:2]
                            hour = int(hour)
                            if 'pm' in time_str.lower() and hour != 12:
                                hour += 12
                            elif 'am' in time_str.lower() and hour == 12:
                                hour = 0
                            time_str = f"{hour:02d}:{minute}"
                        
                        st.session_state.pending_event = {
                            "title": "Hike" if "hike" in prompt.lower() else "Event",
                            "date": date_str,
                            "time": time_str,
                            "description": result,
                            "location": "Wilmington, Delaware" if "wilmington" in prompt.lower() else ""
                        }
                
                # Add assistant response to history
                st.session_state.messages.append({"role": "assistant", "content": result})
            except Exception as e:
                error_msg = f"Error: {str(e)}"
                st.error(error_msg)
                st.session_state.messages.append({"role": "assistant", "content": error_msg})

