"""Turn the local page into a check request."""

from __future__ import annotations

from dataclasses import dataclass, field

from .model_check import list_datasets


@dataclass
class Answers:
    service: str
    specific: bool
    model: str
    base_url: str
    api_key: str
    adversarial: bool
    target: str
    policies: dict[str, bool] = field(default_factory=dict)
    judge_model: str = ""
    judge_base_url: str = ""
    judge_api_key: str = ""
    attacker_model: str = ""
    attacker_base_url: str = ""
    attacker_api_key: str = ""
    datasets: tuple[str, ...] = ()
    workers: int = 4


def mask_key(secret: str) -> str:
    tail = secret[-4:] if len(secret) > 4 else ""
    return f"****{tail}" if tail else "****"


def _text(data: dict, key: str) -> str:
    value = data.get(key)
    if value is None:
        return ""
    return str(value).strip()


def _need(data: dict, key: str, label: str) -> str:
    value = _text(data, key)
    if not value:
        raise ValueError(f"请填写{label}")
    return value


def _dataset_ids(data: dict) -> tuple[str, ...]:
    raw = data.get("datasets")
    if raw is None:
        raw = data.get("dataset")
    if isinstance(raw, str):
        parts = [part.strip() for part in raw.split(",") if part.strip()]
    elif isinstance(raw, list):
        parts = [str(part).strip() for part in raw if str(part).strip()]
    else:
        parts = []
    return tuple(dict.fromkeys(parts))


def workers_of(data: dict) -> int:
    raw = data.get("workers", 4)
    if raw is None or str(raw).strip() == "":
        return 4
    try:
        value = int(str(raw).strip())
    except ValueError:
        raise ValueError("并发请填 1 到 16") from None
    if value < 1 or value > 16:
        raise ValueError("并发请填 1 到 16")
    return value


def infra_lines(text: str) -> list[str]:
    return [line.strip() for line in (text or "").replace("\r\n", "\n").split("\n") if line.strip()]


def _flag(value: object) -> bool:
    if isinstance(value, bool):
        return value
    return str(value or "").strip().lower() in {"1", "true", "yes", "y", "是", "on"}


def answers_from_form(data: dict) -> Answers:
    if not isinstance(data, dict):
        raise ValueError("请求格式不正确")
    service = _need(data, "service", "任务名称。例如：xx模型安全评测")
    model = _text(data, "target_model")
    base_url = _text(data, "target_base_url")
    api_key = _text(data, "target_api_key")
    lines = infra_lines(_text(data, "infra"))
    filled = (model, base_url, api_key)
    has_model = all(filled)
    if any(filled) and not has_model:
        raise ValueError("请把被测模型的名称、接口地址和 API Key 填完整。例如：openai:gpt-4o-mini、https://api.openai.com/v1、sk-xxxx")
    if not has_model and not lines:
        raise ValueError("请填写被测模型或基础设施地址，至少填一项。基础设施一行一个，例如：https://192.168.1.10:8080")
    judge_model = judge_base_url = judge_api_key = ""
    adversarial = _flag(data.get("adversarial"))
    attacker_model = attacker_base_url = attacker_api_key = ""
    if has_model:
        judge_model = _need(data, "judge_model", "裁判模型名称。例如：openai:gpt-4o")
        judge_base_url = _need(data, "judge_base_url", "裁判模型接口地址。例如：https://api.openai.com/v1")
        judge_api_key = _need(data, "judge_api_key", "裁判模型 API Key。例如：sk-xxxx")
        if adversarial:
            attacker_model = _need(data, "attacker_model", "攻击模型名称。例如：openai:gpt-4o")
            attacker_base_url = _need(data, "attacker_base_url", "攻击模型接口地址。例如：https://api.openai.com/v1")
            attacker_api_key = _need(data, "attacker_api_key", "攻击模型 API Key。例如：sk-xxxx")
    elif adversarial:
        raise ValueError("做对抗测试需要填写被测模型。例如：openai:gpt-4o-mini")
    datasets = _dataset_ids(data)
    if has_model and not datasets:
        raise ValueError("请至少选择一个评测集")
    if has_model:
        allowed = {item["id"] for item in list_datasets()}
        if any(item not in allowed for item in datasets):
            raise ValueError("请选择列出的评测集")
    else:
        datasets = ()
    return Answers(
        service,
        False,
        model,
        base_url,
        api_key,
        adversarial if has_model else False,
        "\n".join(lines),
        {},
        judge_model,
        judge_base_url,
        judge_api_key,
        attacker_model,
        attacker_base_url,
        attacker_api_key,
        tuple(datasets),
        workers_of(data) if has_model else 4,
    )
