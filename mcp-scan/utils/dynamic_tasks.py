from typing import List, Tuple

# 硬编码动态任务配置，减少外部文件依赖
DYNAMIC_TASKS = {
    "tool_poisoning": {
        "type": "malicious",
        "prompt": "prompt/tasks/malicious/tool_poisoning_detection.yaml"
    },
    "rug_pull": {
        "type": "malicious",
        "prompt": "prompt/tasks/malicious/rug_pull_detection.yaml"
    },
    "malicious_code_execution": {
        "type": "vulnerability",
        "prompt": "prompt/tasks/vulnerability/malicious_code_execution_detection.yaml"
    },
    "tool_output_prompt_injection": {
        "type": "vulnerability",
        "prompt": "prompt/tasks/vulnerability/tool_output_prompt_injection.yaml"
    },
    "credential_leakage": {
        "type": "vulnerability",
        "prompt": "prompt/tasks/vulnerability/credential_leakage.yaml"
    }
}

def get_allowed_dynamic_tasks() -> List[str]:
    """返回允许的动态任务名称列表"""
    return list(DYNAMIC_TASKS.keys())

def get_targets_for_tasks(task_names: List[str]) -> List[Tuple[str, dict]]:
    """根据给定的任务名称列表返回有序的 (name, config) 列表。
    
    如果遇到不合法的任务名称会抛出 ValueError。
    """
    result = []
    for name in task_names:
        if name not in DYNAMIC_TASKS:
            raise ValueError(f"Invalid dynamic task: {name}")
        result.append((name, DYNAMIC_TASKS[name]))
    return result

if __name__ == "__main__":
    print("Allowed dynamic tasks:", get_allowed_dynamic_tasks())
