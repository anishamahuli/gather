from langchain.tools import tool
from ..types import ToolContext
import requests
from datetime import datetime

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

def create_forecast_tool(ctx: ToolContext):
    """Factory function to create weather forecast tool with context bound via closure."""
    @tool("get_weather_forecast", return_direct=False)
    def get_weather_forecast(location: str, days: str = "5") -> str:
        """
        Get weather forecast for a location for multiple days. Use this when you need to compare weather across different days.
        Location can be just a city (e.g., "San Francisco") or city with country code (e.g., "San Francisco,US").
        Args: 
            location (city name, optionally with country code like "city,country")
            days (number of days for forecast, default "5", max 5)
        Returns: Forecast data with dates, temperatures, and conditions for each day.
        """
        if ctx.weather_client is None:
            return "Weather client not configured."
        
        # Parse location - can be "city" or "city,country"
        parts = location.split(",", 1)
        city = parts[0].strip()
        country_code = parts[1].strip() if len(parts) > 1 else None
        
        try:
            num_days = min(int(days), 5)  # Max 5 days
            data = ctx.weather_client.get_forecast(city=city, country_code=country_code, days=num_days)
            
            # Group forecasts by day and get daily max/min temps
            forecasts = data.get("list", [])
            daily_forecasts = {}
            
            for item in forecasts:
                dt = datetime.fromtimestamp(item["dt"])
                date_key = dt.strftime("%Y-%m-%d")
                day_name = dt.strftime("%A")
                
                if date_key not in daily_forecasts:
                    daily_forecasts[date_key] = {
                        "date": date_key,
                        "day": day_name,
                        "temps": [],
                        "conditions": []
                    }
                
                temp = item.get("main", {}).get("temp")
                condition = item.get("weather", [{}])[0].get("description", "unknown")
                daily_forecasts[date_key]["temps"].append(temp)
                daily_forecasts[date_key]["conditions"].append(condition)
            
            # Format output
            result = f"Weather forecast for {location}:\n\n"
            for date_key in sorted(daily_forecasts.keys())[:num_days]:
                day_data = daily_forecasts[date_key]
                max_temp = max(day_data["temps"])
                min_temp = min(day_data["temps"])
                avg_condition = day_data["conditions"][0]  # Use first condition as representative
                result += f"{day_data['day']} ({date_key}): {avg_condition}, High: {max_temp}°C, Low: {min_temp}°C\n"
            
            return result
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                return f"Could not find forecast for '{location}'. Try using just the city name (e.g., 'Hockessin') or city with country code like 'Hockessin,US'."
            return f"Error getting forecast: {str(e)}"
        except Exception as e:
            return f"Error getting forecast: {str(e)}"
    
    return get_weather_forecast