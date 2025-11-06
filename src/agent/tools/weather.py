from langchain.tools import tool
from ..types import ToolContext
import requests

def create_weather_tool(ctx: ToolContext):
    """Factory function to create weather tool with context bound via closure."""
    @tool("check_weather", return_direct=False)
    def check_weather(location: str) -> str:
        """
        Get current weather for a location. 
        Location can be just a city (e.g., "San Francisco") or city with country code (e.g., "San Francisco,US").
        Args: location (city name, optionally with country code like "city,country").
        """
        if ctx.weather_client is None:
            return "Weather client not configured."
        
        # Parse location - can be "city" or "city,country"
        parts = location.split(",", 1)
        city = parts[0].strip()
        country_code = parts[1].strip() if len(parts) > 1 else None
        
        try:
            data = ctx.weather_client.get_weather(city=city, country_code=country_code)
            main = data.get("weather", [{}])[0].get("description", "unknown")
            temp = data.get("main", {}).get("temp")
            return f"Weather in {location}: {main}, {temp}°C"
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                return f"Could not find weather for '{location}'. Try using just the city name (e.g., 'Hockessin') or city with country code like 'Hockessin,US'."
            return f"Error getting weather: {str(e)}"
        except Exception as e:
            return f"Error getting weather: {str(e)}"
    
    return check_weather