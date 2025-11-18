import os
import json
from pathlib import Path
from typing import Optional
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

# Google Calendar API scopes
SCOPES = [
    'https://www.googleapis.com/auth/calendar.readonly',
    'https://www.googleapis.com/auth/calendar.events'
]

def get_credentials_path() -> Path:
    """Get path to credentials.json file."""
    project_root = Path(__file__).resolve().parents[2]
    return project_root / "credentials.json"

def get_token_path(user_id: str) -> Path:
    """Get path to store user's OAuth tokens."""
    project_root = Path(__file__).resolve().parents[2]
    token_dir = project_root / "data" / "users" / user_id
    token_dir.mkdir(parents=True, exist_ok=True)
    return token_dir / "google_tokens.json"

def load_credentials(user_id: str) -> Optional[Credentials]:
    """
    Load OAuth credentials for a user.
    Returns None if user is not authenticated.
    """
    token_path = get_token_path(user_id)
    
    if not token_path.exists():
        return None
    
    try:
        creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)
        
        # Refresh token if expired
        if creds.expired and creds.refresh_token:
            creds.refresh(Request())
            save_credentials(user_id, creds)
        
        return creds
    except Exception as e:
        print(f"Error loading credentials: {e}")
        return None

def save_credentials(user_id: str, creds: Credentials) -> None:
    """Save OAuth credentials for a user."""
    token_path = get_token_path(user_id)
    
    token_data = {
        'token': creds.token,
        'refresh_token': creds.refresh_token,
        'token_uri': creds.token_uri,
        'client_id': creds.client_id,
        'client_secret': creds.client_secret,
        'scopes': creds.scopes
    }
    
    with open(token_path, 'w') as token_file:
        json.dump(token_data, token_file)

def get_authorization_url(user_id: str, redirect_uri: str = "http://localhost:8501") -> str:
    """
    Get OAuth authorization URL for manual flow (Streamlit-friendly).
    Uses localhost redirect - user will need to copy the code from the redirect URL.
    Returns the authorization URL.
    """
    credentials_path = get_credentials_path()
    
    if not credentials_path.exists():
        raise FileNotFoundError(f"credentials.json not found at {credentials_path}")
    
    # Read credentials file
    with open(credentials_path, 'r') as f:
        client_config = json.load(f)
    
    # Extract client info
    client_info = client_config.get('web', {})
    client_id = client_info.get('client_id')
    
    # Build authorization URL
    from urllib.parse import urlencode
    params = {
        'client_id': client_id,
        'redirect_uri': redirect_uri,
        'scope': ' '.join(SCOPES),
        'response_type': 'code',
        'access_type': 'offline',
        'prompt': 'consent'
    }
    
    auth_url = f"https://accounts.google.com/o/oauth2/auth?{urlencode(params)}"
    return auth_url

def complete_authorization_with_code(user_id: str, authorization_code: str, redirect_uri: str = "http://localhost:8501") -> Credentials:
    """
    Complete OAuth flow using authorization code (from manual flow).
    Returns the credentials object.
    """
    credentials_path = get_credentials_path()
    
    # Read credentials file
    with open(credentials_path, 'r') as f:
        client_config = json.load(f)
    
    client_info = client_config.get('web', {})
    client_id = client_info.get('client_id')
    client_secret = client_info.get('client_secret')
    token_uri = client_info.get('token_uri', 'https://oauth2.googleapis.com/token')
    
    # Exchange code for tokens
    import requests
    data = {
        'code': authorization_code,
        'client_id': client_id,
        'client_secret': client_secret,
        'redirect_uri': redirect_uri,
        'grant_type': 'authorization_code'
    }
    
    response = requests.post(token_uri, data=data)
    response.raise_for_status()
    token_data = response.json()
    
    # Create credentials object
    creds = Credentials(
        token=token_data.get('access_token'),
        refresh_token=token_data.get('refresh_token'),
        token_uri=token_uri,
        client_id=client_id,
        client_secret=client_secret,
        scopes=SCOPES
    )
    
    save_credentials(user_id, creds)
    return creds

def is_authenticated(user_id: str) -> bool:
    """Check if user is authenticated with Google Calendar."""
    creds = load_credentials(user_id)
    return creds is not None and creds.valid

def get_calendar_service(user_id: str):
    """
    Get authenticated Google Calendar service.
    Returns None if user is not authenticated.
    """
    creds = load_credentials(user_id)
    if not creds:
        return None
    
    try:
        service = build('calendar', 'v3', credentials=creds)
        return service
    except Exception as e:
        print(f"Error building calendar service: {e}")
        return None

