import json
from pathlib import Path

def get_strategy_map():
    json_path = Path(__file__).resolve().parent / "strategy_map.json"
    with open(json_path, "r", encoding="utf-8") as f:
        strategy_map = json.load(f)
    return strategy_map