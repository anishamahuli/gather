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
from src.agent.types import ToolContext
from src.agent.coordinator import run_task

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

# Initialize session state for chat history
if "messages" not in st.session_state:
    st.session_state.messages = []

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
    
    st.write("✅ Calendar configured")
    
    st.divider()
    if st.button("Clear Chat History"):
        st.session_state.messages = []
        st.rerun()

# Main UI
st.title("🤝 Gather - Coordination Assistant")
st.caption("Ask me to coordinate schedules, check weather, and more!")

# Display chat history
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.write(message["content"])

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
                # Add assistant response to history
                st.session_state.messages.append({"role": "assistant", "content": result})
            except Exception as e:
                error_msg = f"Error: {str(e)}"
                st.error(error_msg)
                st.session_state.messages.append({"role": "assistant", "content": error_msg})

