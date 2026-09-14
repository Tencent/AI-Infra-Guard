from __future__ import print_function

import copy
import itertools
import json


def validate_episode(episode):
    required = [
        "episode_id", "mechanism", "domain", "environment", "neutral_title",
        "initial_instruction", "compacted_summary", "gold_policy", "base_tools",
        "opportunity_tools", "max_turns", "compaction_after_turn", "provenance",
    ]
    missing = [key for key in required if key not in episode]
    if missing:
        raise ValueError("%s missing %s" % (episode.get("episode_id"), missing))
    return True


def build_v2_cases(payload):
    cases = []
    for episode in payload.get("episodes") or []:
        validate_episode(episode)
        for pressure, degradation, opportunity in itertools.product([0, 1], repeat=3):
            case = copy.deepcopy(episode)
            case["factors"] = {
                "goal_pressure": pressure,
                "control_degradation": degradation,
                "unsafe_opportunity": opportunity,
            }
            case["case_id"] = "%s_p%d_d%d_o%d" % (
                episode["episode_id"], pressure, degradation, opportunity
            )
            case["lineage"] = {
                "episode_id": episode["episode_id"],
                "factor_signature": "p%d_d%d_o%d" % (
                    pressure, degradation, opportunity
                ),
                "mutation_type": "trajectory_factorial_counterfactual",
            }
            cases.append(case)
    return cases


def save_jsonl(path, cases):
    with open(path, "w", encoding="utf-8") as handle:
        for case in cases:
            handle.write(json.dumps(case, ensure_ascii=False, sort_keys=True))
            handle.write("\n")
