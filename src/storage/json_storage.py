import json
from pathlib import Path
from typing import Any

DATA_DIR = Path(__file__).resolve().parents[2] / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

def load_json(relative_path: str, default: Any) -> Any:
    file_path = DATA_DIR / relative_path
    if not file_path.exists():
        return default
    with open(file_path, "r") as f:
        return json.load(f)

def save_json(relative_path: str, data: Any) -> None:
    file_path = DATA_DIR / relative_path
    file_path.parent.mkdir(parents=True, exist_ok=True)
    with open(file_path, "w") as f:
        json.dump(data, f, indent=2)