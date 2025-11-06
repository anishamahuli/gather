from datetime import datetime
from typing import List, Tuple
from src.storage.json_storage import load_json, save_json

class CalendarClient:
    def __init__(self, user_id: str):
        self.user_id = user_id
        self.path = f"users/{self.user_id}/calendar.json"

    def get_events(self) -> List[Tuple[str, str]]:
        data = load_json(self.path, default={"events": []})
        return data.get("events", [])

    def is_free(self, date_iso: str) -> bool:
        # naive: if there is no event exactly on date, user is free
        day = date_iso.split("T")[0]
        for start, end in self.get_events():
            if start.startswith(day) or end.startswith(day):
                return False
        return True

    def add_event(self, start_iso: str, end_iso: str, title: str) -> None:
        data = load_json(self.path, default={"events": []})
        data["events"].append([start_iso, end_iso, title])
        save_json(self.path, data)