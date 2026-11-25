"""Progress rendering failures must not discard completed assessment results."""
import asyncio
import io
import json
from contextlib import nullcontext
from types import SimpleNamespace

import pandas as pd
import pytest
from tqdm import tqdm

from deepteam.red_teamer import red_teamer as module
from deepteam.red_teamer.progress_log import ProgressLog
from deepteam.red_teamer.risk_assessment import RedTeamingTestCase
from deepteam.attacks.attack_simulator import SimulatedAttack
from deepteam.vulnerabilities.bias.types import BiasType


class BrokenStream(io.StringIO):
    broken = False

    def write(self, text):
        if self.broken:
            raise BrokenPipeError(32, "Broken pipe")
        return super().write(text)


@pytest.mark.parametrize("failure_at", ["update", "close"])
def test_assessment_survives_broken_progress_pipe(monkeypatch, tmp_path, failure_at):
    # Model/attack generation is replaced with harmless, prebuilt test data.
    # The evaluation loop, JSONL, summary and CSV report are real.
    count = 3027
    attacks = [
        SimulatedAttack(
            vulnerability="bias", vulnerability_type=BiasType.RACE,
            original_input=f"benign case {i}", input=f"benign case {i}",
        )
        for i in range(count)
    ]
    cases = {
        attack.input: RedTeamingTestCase(
            vulnerability="bias", vulnerability_type=BiasType.RACE,
            riskCategory="test", attackMethod="mock",
            original_input=attack.original_input, input=attack.input,
            actual_output="mock answer", score=1.0 if i else None,
            reason="mock review" if i else None,
            error="mock judge unavailable" if not i else None,
        )
        for i, attack in enumerate(attacks)
    }
    stream = BrokenStream()
    bars = []

    def progress_factory(**kwargs):
        progress = tqdm(
            **kwargs, file=stream, miniters=1,
            mininterval=0 if failure_at == "update" else float("inf"),
        )
        bars.append(progress)
        stream.broken = True
        return progress

    events = []
    logger = SimpleNamespace(
        lang="en_US",
        translated_msg=lambda value, **kw: value.format(**kw),
        tool_used=lambda event: events.append(event),
        status_update=lambda event: events.append(event),
    )
    monkeypatch.setattr(module, "tqdm", progress_factory)
    monkeypatch.setattr(module, "logger", logger)
    monkeypatch.setattr(module, "capture_red_teamer_run", lambda **kw: nullcontext())
    monkeypatch.chdir(tmp_path)

    rt = module.RedTeamer.__new__(module.RedTeamer)
    rt.max_concurrent = 2
    rt.get_red_teaming_metrics_map = lambda vulnerabilities: {}
    rt._resumed_attacks = lambda *args: attacks
    rt._completed_cases = lambda: {}
    path = tmp_path / "results.jsonl"
    rt._new_progress_log = lambda: ProgressLog(str(path), flush_every=512)

    async def mock_case(**kwargs):
        return cases[kwargs["simulated_attack"].input]

    rt._a_attack = mock_case
    vulnerability = SimpleNamespace(
        get_name=lambda: "mock", get_types=lambda: [BiasType.RACE],
    )
    result = asyncio.run(rt.a_red_team(
        model_callback=None, vulnerabilities=[vulnerability], attacks=[],
        ignore_errors=True, model_name="mock",
    ))
    assert result is rt.risk_assessment
    assert len(result.test_cases) == count
    assert sum(bool(case.error) for case in result.test_cases) == 1
    records = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    assert len(records) == count
    assert len({record["input"] for record in records}) == count
    assert sum(bool(record.get("error")) for record in records) == 1
    assert any(getattr(event, "status", None) == "completed" for event in events)

    (tmp_path / "logs").mkdir()
    report, _ = rt.get_risk_assessment_json(result, model_name="mock")
    assert report["baseTotal"] == count
    assert report["total"] == count - 1
    assert report["errored"] == 1
    exported = pd.read_csv(report["attachment"])
    assert len(exported) == count
    assert (exported["status"] == "Exception").sum() == 1
    assert bars[0].disable


@pytest.mark.parametrize("operation", ["update", "close"])
def test_progress_helpers_preserve_unrelated_errors(operation):
    class InvalidProgress:
        disable = False

        def update(self, amount):
            raise ValueError("not an output failure")

        def close(self):
            raise ValueError("not an output failure")

    with pytest.raises(ValueError, match="not an output failure"):
        if operation == "update":
            module._safe_progress_update(InvalidProgress(), 1)
        else:
            module._safe_progress_close(InvalidProgress())


def test_progress_still_updates_normally():
    progress = tqdm(total=2, file=io.StringIO(), mininterval=0)
    module._safe_progress_update(progress, 1)
    assert progress.n == 1
    module._safe_progress_update(progress, 1)
    assert progress.n == 2
    module._safe_progress_close(progress)
