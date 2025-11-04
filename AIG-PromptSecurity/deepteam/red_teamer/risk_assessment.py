from pydantic import BaseModel, Field
from typing import Dict, Optional, List
import datetime
import os
import json
from enum import Enum

from deepteam.vulnerabilities.types import VulnerabilityType


class RedTeamingTestCase(BaseModel):
    vulnerability: str
    vulnerability_type: VulnerabilityType
    risk_category: str = Field(alias="riskCategory")
    attack_method: Optional[str] = Field(None, alias="attackMethod")
    original_input: Optional[str] = None
    input: Optional[str] = None
    actual_output: Optional[str] = Field(
        None, serialization_alias="actualOutput"
    )
    score: Optional[float] = None
    reason: Optional[str] = None
    error: Optional[str] = None
    useless: bool = False


class TestCasesList(list):
    def to_df(self):
        import pandas as pd

        data = []
        for case in self:
            data.append(
                {
                    "Vulnerability": case.vulnerability,
                    "Vulnerability Type": str(case.vulnerability_type.value),
                    "Risk Category": case.risk_category,
                    "Attack Enhancement": case.attack_method,
                    "Input": case.input,
                    "Actual Output": case.actual_output,
                    "Score": case.score,
                    "Reason": case.reason,
                    "Error": case.error,
                    "Status": (
                        "Passed"
                        if case.score and case.score > 0
                        else "Errored" if case.error else "Failed"
                    ),
                }
            )
        return pd.DataFrame(data)


class VulnerabilityTypeResult(BaseModel):
    vulnerability: str
    vulnerability_type: VulnerabilityType
    pass_rate: float
    passing: int
    failing: int
    errored: int
    unused: int


class AttackMethodResult(BaseModel):
    attack_method: Optional[str] = None
    pass_rate: float
    passing: int
    failing: int
    errored: int
    unused: int


class RedTeamingOverview(BaseModel):
    vulnerability_type_results: List[VulnerabilityTypeResult]
    attack_method_results: List[AttackMethodResult]

    def to_df(self):
        import pandas as pd

        data = []
        for result in self.vulnerability_type_results:
            data.append(
                {
                    "Vulnerability": result.vulnerability,
                    "Vulnerability Type": str(result.vulnerability_type.value),
                    "Total": result.passing + result.failing + result.errored,
                    "Pass Rate": result.pass_rate,
                    "Passing": result.passing,
                    "Failing": result.failing,
                    "Errored": result.errored,
                }
            )
        return pd.DataFrame(data)


class EnumEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Enum):
            return obj.value
        return super().default(obj)


class RiskAssessment(BaseModel):
    overview: RedTeamingOverview
    test_cases: List[RedTeamingTestCase]

    def __init__(self, **data):
        super().__init__(**data)
        self.test_cases = TestCasesList[RedTeamingTestCase](self.test_cases)

    def save(self, to: str) -> str:
        try:
            new_filename = (
                datetime.datetime.now().strftime("%Y%m%d_%H%M%S") + ".json"
            )

            if not os.path.exists(to):
                try:
                    os.makedirs(to)
                except OSError as e:
                    raise OSError(f"Cannot create directory '{to}': {e}")

            full_file_path = os.path.join(to, new_filename)

            # Convert model to a dictionary
            data = self.model_dump(by_alias=True)

            # Write to JSON file
            with open(full_file_path, "w") as f:
                json.dump(data, f, indent=2, cls=EnumEncoder)

            print(
                f"🎉 Success! 🎉 Your risk assessment file has been saved to:\n📁 {full_file_path} ✅"
            )

        except OSError as e:
            raise OSError(f"Failed to save file to '{to}': {e}") from e


def construct_risk_assessment_overview(
    red_teaming_test_cases: List[RedTeamingTestCase],
) -> RedTeamingOverview:
    # Group test cases by vulnerability type
    vulnerability_to_cases: Dict[str, List[RedTeamingTestCase]] = {}
    attack_method_to_cases: Dict[str, List[RedTeamingTestCase]] = {}

    for test_case in red_teaming_test_cases:
        # Group by vulnerability type
        if test_case.vulnerability not in vulnerability_to_cases:
            vulnerability_to_cases[test_case.vulnerability] = []
        vulnerability_to_cases[test_case.vulnerability].append(test_case)

        # Group by attack method
        if test_case.attack_method not in attack_method_to_cases:
            attack_method_to_cases[test_case.attack_method] = []
        attack_method_to_cases[test_case.attack_method].append(test_case)

    vulnerability_type_results = []
    attack_method_results = []

    # Stats per vulnerability type
    for vuln, test_cases in vulnerability_to_cases.items():
        passing = sum(
            1 for tc in test_cases if tc.score is not None and tc.score > 0
        )
        errored = sum(1 for tc in test_cases if tc.error is not None)
        unused = sum(1 for tc in test_cases if (tc.useless and tc.error is None))
        failing = len(test_cases) - passing - errored - unused
        valid_cases = passing + failing
        pass_rate = (passing / valid_cases) if valid_cases > 0 else 0.0

        vulnerability_type_results.append(
            VulnerabilityTypeResult(
                vulnerability=vuln,
                vulnerability_type=test_cases[-1].vulnerability_type if test_cases else "",
                pass_rate=pass_rate,
                passing=passing,
                failing=failing,
                errored=errored,
                unused=unused,
            )
        )

    # Stats per attack method
    for attack_method, test_cases in attack_method_to_cases.items():
        passing = sum(
            1 for tc in test_cases if tc.score is not None and tc.score > 0
        )
        errored = sum(1 for tc in test_cases if tc.error is not None)
        unused = sum(1 for tc in test_cases if (tc.useless and tc.error is None))
        failing = len(test_cases) - passing - errored - unused
        valid_cases = passing + failing
        pass_rate = (passing / valid_cases) if valid_cases > 0 else 0.0

        attack_method_results.append(
            AttackMethodResult(
                attack_method=attack_method,
                pass_rate=pass_rate,
                passing=passing,
                failing=failing,
                errored=errored,
                unused=unused,
            )
        )

    return RedTeamingOverview(
        vulnerability_type_results=vulnerability_type_results,
        attack_method_results=attack_method_results,
    )
