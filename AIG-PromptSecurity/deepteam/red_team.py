from typing import List, Optional

from deepteam.vulnerabilities import BaseVulnerability
from deepteam.attacks import BaseAttack
from deepteam.attacks.multi_turn.types import CallbackType
from deepteam.red_teamer import RedTeamer


def red_team(
    model_callback: CallbackType,
    vulnerabilities: List[BaseVulnerability],
    attacks: List[BaseAttack],
    attacks_per_vulnerability_type: int = 1,
    ignore_errors: bool = False,
    run_async: bool = True,
    max_concurrent: int = 10,
    target_purpose: Optional[str] = None,
):

    red_teamer = RedTeamer(
        async_mode=run_async,
        max_concurrent=max_concurrent,
        target_purpose=target_purpose,
    )
    risk_assessment = red_teamer.red_team(
        model_callback=model_callback,
        vulnerabilities=vulnerabilities,
        attacks=attacks,
        attacks_per_vulnerability_type=attacks_per_vulnerability_type,
        ignore_errors=ignore_errors,
    )
    return risk_assessment
