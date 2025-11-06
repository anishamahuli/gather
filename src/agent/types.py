from dataclasses import dataclass
from typing import Optional
from src.integrations.weather_api import OpenWeatherClient
from src.integrations.n8n_api import N8NClient
from src.integrations.calendar_api import CalendarClient

@dataclass
class ToolContext:
    weather_client: Optional[OpenWeatherClient] = None
    n8n_client: Optional[N8NClient] = None
    calendar_client: Optional[CalendarClient] = None