import os
import json
from typing import List, Tuple
from utils.config import base_dir


CONFIG_PATH = os.path.join(base_dir, "config", "dynamic_tasks.json")


def _load_config() -> dict:
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}
    except Exception:
        return {}


def get_allowed_dynamic_tasks() -> List[str]:
    """返回允许的动态任务名称列表"""
    cfg = _load_config()
    tasks = cfg.get("dynamic_tasks", {})
    if isinstance(tasks, dict):
        return list(tasks.keys())
    return []


def get_targets_for_tasks(task_names: List[str]) -> List[Tuple[str, dict]]:
    """根据给定的任务名称列表返回有序的 (name, config) 列表。

    如果遇到不合法的任务名称会抛出 ValueError。
    """
    cfg = _load_config()
    tasks = cfg.get("dynamic_tasks", {})
    result = []
    for name in task_names:
        if name not in tasks:
            raise ValueError(f"Invalid dynamic task: {name}")
        result.append((name, tasks[name]))
    return result


if __name__ == "__main__":
    print("Allowed dynamic tasks:", get_allowed_dynamic_tasks())
