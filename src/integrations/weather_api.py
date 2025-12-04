import requests
from typing import Optional

class OpenWeatherClient:
    def __init__(self, api_key: str):
        self.api_key = api_key

    def _get_location_query(self, city: str, country_code: Optional[str] = None) -> str:
        """Helper to build location query string."""
        if country_code:
            return f"{city},{country_code}"
        return city

    def get_weather(self, city: str, country_code: Optional[str] = None) -> dict:
        """Get current weather for a location."""
        url = "https://api.openweathermap.org/data/2.5/weather"
        
        # Try with country code first if provided
        if country_code:
            q = self._get_location_query(city, country_code)
            resp = requests.get(url, params={"q": q, "appid": self.api_key, "units": "metric"}, timeout=15)
            if resp.status_code == 200:
                return resp.json()
            # If 404, try without country code (might be a state code or invalid country code)
            if resp.status_code == 404:
                resp = requests.get(url, params={"q": city, "appid": self.api_key, "units": "metric"}, timeout=15)
                if resp.status_code == 200:
                    return resp.json()
        
        # Try without country code
        resp = requests.get(url, params={"q": city, "appid": self.api_key, "units": "metric"}, timeout=15)
        resp.raise_for_status()
        return resp.json()

    def get_forecast(self, city: str, country_code: Optional[str] = None, days: int = 5) -> dict:
        """Get weather forecast for a location (up to 5 days)."""
        url = "https://api.openweathermap.org/data/2.5/forecast"
        
        # OpenWeatherMap forecast returns 3-hour intervals, so for N days we need N*8 intervals
        # But the API returns up to 40 intervals (5 days) by default, so we don't need to specify cnt
        params = {"appid": self.api_key, "units": "metric"}
        
        # Try with country code first if provided
        if country_code:
            q = self._get_location_query(city, country_code)
            params["q"] = q
            resp = requests.get(url, params=params, timeout=15)
            if resp.status_code == 200:
                return resp.json()
            # If 404, try without country code
            if resp.status_code == 404:
                params["q"] = city
                resp = requests.get(url, params=params, timeout=15)
                if resp.status_code == 200:
                    return resp.json()
        
        # Try without country code
        params["q"] = city
        resp = requests.get(url, params=params, timeout=15)
        resp.raise_for_status()
        return resp.json()
