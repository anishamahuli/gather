import requests

class N8NClient:
    def __init__(self, webhook_url: str):
        self.webhook_url = webhook_url

    def trigger(self, payload: dict) -> dict:
        resp = requests.post(self.webhook_url, json=payload, timeout=30)
        resp.raise_for_status()
        # n8n webhooks often return array of items; normalize here
        try:
            return resp.json()
        except Exception:
            return {"status": resp.status_code, "text": resp.text}