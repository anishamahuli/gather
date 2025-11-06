import requests
from typing import Optional

class OpenWeatherClient:
    def __init__(self, api_key: str):
        self.api_key = api_key

    def get_weather(self, city: str, country_code: Optional[str] = None) -> dict:
        url = "https://api.openweathermap.org/data/2.5/weather"
        
        # Try with country code first if provided
        if country_code:
            q = f"{city},{country_code}"
            resp = requests.get(url, params={"q": q, "appid": self.api_key, "units": "metric"}, timeout=15)
            if resp.status_code == 200:
                return resp.json()
            # If 404, try without country code (might be a state code or invalid country code)
            if resp.status_code == 404:
                # Try just the city
                resp = requests.get(url, params={"q": city, "appid": self.api_key, "units": "metric"}, timeout=15)
                if resp.status_code == 200:
                    return resp.json()
        
        # Try without country code
        resp = requests.get(url, params={"q": city, "appid": self.api_key, "units": "metric"}, timeout=15)
        resp.raise_for_status()
        return resp.json()