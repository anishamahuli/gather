from datetime import datetime, timedelta
from typing import List, Tuple, Optional
from src.storage.json_storage import load_json, save_json
from src.integrations.google_auth import get_calendar_service, is_authenticated

class CalendarClient:
    def __init__(self, user_id: str):
        self.user_id = user_id
        self.path = f"users/{self.user_id}/calendar.json"
        self.use_google_calendar = is_authenticated(user_id)
        self.service = get_calendar_service(user_id) if self.use_google_calendar else None

    def get_events(self, start_date: Optional[str] = None, end_date: Optional[str] = None) -> List[Tuple[str, str, str]]:
        """
        Get calendar events. Returns list of (start, end, title) tuples.
        If Google Calendar is connected, uses that. Otherwise falls back to JSON storage.
        """
        if self.use_google_calendar and self.service:
            return self._get_google_events(start_date, end_date)
        else:
            # Fallback to JSON storage
            data = load_json(self.path, default={"events": []})
            events = data.get("events", [])
            # Convert to (start, end, title) format if needed
            return [(e[0], e[1], e[2] if len(e) > 2 else "") for e in events]

    def _get_google_events(self, start_date: Optional[str] = None, end_date: Optional[str] = None) -> List[Tuple[str, str, str]]:
        """Get events from Google Calendar."""
        try:
            # Default to current week if no dates provided
            if not start_date:
                start_date = datetime.now().isoformat() + 'Z'
            if not end_date:
                end_date = (datetime.now() + timedelta(days=7)).isoformat() + 'Z'
            
            # Ensure dates are in RFC3339 format (required by Google Calendar API)
            # Convert ISO format to RFC3339 if needed
            if start_date and not start_date.endswith('Z') and '+' not in start_date:
                try:
                    dt = datetime.fromisoformat(start_date.replace('Z', ''))
                    start_date = dt.isoformat() + 'Z'
                except:
                    pass
            if end_date and not end_date.endswith('Z') and '+' not in end_date:
                try:
                    dt = datetime.fromisoformat(end_date.replace('Z', ''))
                    end_date = dt.isoformat() + 'Z'
                except:
                    pass
            
            events_result = self.service.events().list(
                calendarId='primary',
                timeMin=start_date,
                timeMax=end_date,
                singleEvents=True,
                orderBy='startTime'
            ).execute()
            
            events = events_result.get('items', [])
            result = []
            for event in events:
                start = event['start'].get('dateTime', event['start'].get('date'))
                end = event['end'].get('dateTime', event['end'].get('date'))
                title = event.get('summary', 'No Title')
                result.append((start, end, title))
            
            return result
        except Exception as e:
            print(f"Error fetching Google Calendar events: {e}")
            return []

    def is_free(self, date_iso: str, duration_minutes: int = 60) -> bool:
        """
        Check if user is free at a specific time.
        date_iso should be in format: YYYY-MM-DDTHH:MM:SS
        """
        if self.use_google_calendar and self.service:
            return self._is_free_google(date_iso, duration_minutes)
        else:
            # Fallback to JSON storage (naive check)
            day = date_iso.split("T")[0]
            for start, end, _ in self.get_events():
                if start.startswith(day) or end.startswith(day):
                    return False
            return True

    def _is_free_google(self, date_iso: str, duration_minutes: int) -> bool:
        """Check if time slot is free using Google Calendar."""
        try:
            start_dt = datetime.fromisoformat(date_iso.replace('Z', '+00:00'))
            end_dt = start_dt + timedelta(minutes=duration_minutes)
            
            # Format for Google Calendar API (RFC3339 with Z)
            start_rfc3339 = start_dt.isoformat() + 'Z'
            end_rfc3339 = end_dt.isoformat() + 'Z'
            
            # Check for overlapping events
            events = self._get_google_events(
                start_date=start_rfc3339,
                end_date=end_rfc3339
            )
            
            return len(events) == 0
        except Exception as e:
            print(f"Error checking Google Calendar availability: {e}")
            return True  # Assume free on error

    def find_free_slots(self, start_date: str, end_date: str, duration_minutes: int = 60, 
                       preferred_times: Optional[List[str]] = None) -> List[Tuple[str, str]]:
        """
        Find free time slots in a date range.
        Returns list of (start, end) ISO datetime tuples.
        preferred_times: List of preferred times like ["09:00", "14:00"] to check first.
        """
        if self.use_google_calendar and self.service:
            try:
                return self._find_free_slots_google(start_date, end_date, duration_minutes, preferred_times)
            except Exception as e:
                print(f"Error in find_free_slots: {e}")
                # Return a few default time slots as fallback
                try:
                    start_dt = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
                    return [
                        (start_dt.replace(hour=9, minute=0).isoformat(), 
                         (start_dt.replace(hour=9, minute=0) + timedelta(minutes=duration_minutes)).isoformat()),
                        (start_dt.replace(hour=14, minute=0).isoformat(),
                         (start_dt.replace(hour=14, minute=0) + timedelta(minutes=duration_minutes)).isoformat()),
                    ]
                except:
                    return []
        else:
            # Simple fallback - return a few default time slots
            try:
                start_dt = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
                return [
                    (start_dt.replace(hour=9, minute=0).isoformat(), 
                     (start_dt.replace(hour=9, minute=0) + timedelta(minutes=duration_minutes)).isoformat()),
                    (start_dt.replace(hour=14, minute=0).isoformat(),
                     (start_dt.replace(hour=14, minute=0) + timedelta(minutes=duration_minutes)).isoformat()),
                ]
            except:
                return []

    def _find_free_slots_google(self, start_date: str, end_date: str, duration_minutes: int,
                                preferred_times: Optional[List[str]] = None) -> List[Tuple[str, str]]:
        """Find free slots using Google Calendar."""
        try:
            start_dt = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
            end_dt = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
            
            # Format for Google Calendar API (RFC3339 with Z)
            start_rfc3339 = start_dt.isoformat() + 'Z'
            end_rfc3339 = end_dt.isoformat() + 'Z'
            
            # Get all events in range
            events = self._get_google_events(start_rfc3339, end_rfc3339)
            
            # Convert events to datetime ranges
            busy_times = []
            for event_start, event_end, _ in events:
                try:
                    busy_start = datetime.fromisoformat(event_start.replace('Z', '+00:00'))
                    busy_end = datetime.fromisoformat(event_end.replace('Z', '+00:00'))
                    busy_times.append((busy_start, busy_end))
                except:
                    continue
            
            # Find free slots
            free_slots = []
            current = start_dt
            
            while current < end_dt:
                slot_end = current + timedelta(minutes=duration_minutes)
                
                # Check if this slot overlaps with any busy time
                is_free = True
                for busy_start, busy_end in busy_times:
                    if not (slot_end <= busy_start or current >= busy_end):
                        is_free = False
                        break
                
                if is_free and slot_end <= end_dt:
                    free_slots.append((current.isoformat(), slot_end.isoformat()))
                
                # Move to next hour (or preferred time)
                if preferred_times and current.hour < 23:
                    # Try next preferred time
                    current = current.replace(hour=current.hour + 1, minute=0)
                else:
                    current += timedelta(hours=1)
            
            return free_slots[:10]  # Limit to 10 slots
        except Exception as e:
            print(f"Error finding free slots: {e}")
            return []

    def create_event(self, title: str, start_iso: str, end_iso: str, 
                    description: str = "", location: str = "") -> Optional[str]:
        """
        Create a calendar event.
        Returns event ID if successful, None otherwise.
        """
        if self.use_google_calendar and self.service:
            return self._create_google_event(title, start_iso, end_iso, description, location)
        else:
            # Fallback to JSON storage
            self.add_event(start_iso, end_iso, title)
            return "local_event"

    def _create_google_event(self, title: str, start_iso: str, end_iso: str,
                            description: str, location: str) -> Optional[str]:
        """Create event in Google Calendar."""
        try:
            # Ensure datetime is in RFC3339 format with timezone
            # Google Calendar API requires timezone info
            start_dt = start_iso
            end_dt = end_iso

            # If datetime doesn't have timezone info, add it
            if 'T' in start_dt and not ('+' in start_dt or 'Z' in start_dt):
                # Add timezone offset for America/New_York (EST/EDT)
                # For simplicity, using UTC offset. Better: use pytz
                from datetime import datetime
                import time

                # Get local timezone offset
                is_dst = time.daylight and time.localtime().tm_isdst > 0
                utc_offset = - (time.altzone if is_dst else time.timezone)
                offset_hours = utc_offset // 3600
                offset_minutes = (abs(utc_offset) % 3600) // 60
                offset_str = f"{offset_hours:+03d}:{offset_minutes:02d}"

                start_dt = f"{start_iso}{offset_str}"
                end_dt = f"{end_iso}{offset_str}"

            event = {
                'summary': title,
                'start': {
                    'dateTime': start_dt,
                    'timeZone': 'America/New_York',  # TODO: Make timezone configurable
                },
                'end': {
                    'dateTime': end_dt,
                    'timeZone': 'America/New_York',
                },
            }

            # Only add description and location if they have values
            if description:
                event['description'] = description
            if location:
                event['location'] = location

            created_event = self.service.events().insert(
                calendarId='primary',
                body=event
            ).execute()

            return created_event.get('id')
        except Exception as e:
            print(f"Error creating Google Calendar event: {e}")
            import traceback
            traceback.print_exc()
            return None

    def add_event(self, start_iso: str, end_iso: str, title: str) -> None:
        """Legacy method - creates event using create_event."""
        self.create_event(title, start_iso, end_iso)