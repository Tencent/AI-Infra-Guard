set -e

.venv/bin/python cli_run.py \
  --reasoning-backdoor-dataset ../data/eval/reasoning-backdoor-tiny.jsonl \
  --reasoning-oracle-clean \
  --reasoning-output /tmp/aig_reasoning_backdoor_clean.json

.venv/bin/python cli_run.py \
  --reasoning-backdoor-dataset ../data/eval/reasoning-backdoor-tiny.jsonl \
  --reasoning-poison-mode truncation \
  --reasoning-output /tmp/aig_reasoning_backdoor_truncation.json

.venv/bin/python cli_run.py \
  --reasoning-backdoor-dataset ../data/eval/reasoning-backdoor-tiny.jsonl \
  --reasoning-poison-mode step_injection \
  --reasoning-output /tmp/aig_reasoning_backdoor_step_injection.json

.venv/bin/python cli_run.py \
  --reasoning-backdoor-dataset ../data/eval/reasoning-backdoor-tiny.jsonl \
  --reasoning-poison-mode step_injection \
  --reasoning-self-consistency-samples 3 \
  --reasoning-output /tmp/aig_reasoning_backdoor_self_consistency.json

.venv/bin/python -c "import json; rows=[json.loads(l) for l in open('../data/eval/reasoning-backdoor-tiny.jsonl')]; [r.pop('target_answer', None) for r in rows]; open('/tmp/aig_reasoning_backdoor_no_target.jsonl', 'w').write(''.join(json.dumps(r) + '\n' for r in rows[:2]))"

.venv/bin/python cli_run.py \
  --reasoning-backdoor-dataset /tmp/aig_reasoning_backdoor_no_target.jsonl \
  --reasoning-oracle-clean \
  --reasoning-self-consistency-samples 3 \
  --reasoning-output /tmp/aig_reasoning_backdoor_no_target.json

.venv/bin/python - <<'PY'
from cli.reasoning_backdoor_runner import ReasoningBackdoorRunner


class DummyModel:
    def generate(self, prompt=None, messages=None):
        return ""

    def get_model_name(self):
        return "dummy"


runner = ReasoningBackdoorRunner(
    model=DummyModel(),
    dataset_file="../data/eval/reasoning-backdoor-tiny.jsonl",
)

number_cases = [
    (r"Reasoning first. \boxed{42}", "42"),
    ("The answer is 42 dollars.", "42"),
    ("Final answer: $1,234.56", "1234.56"),
    ("Final answer: 3/4", "0.75"),
    ("The result is 75%.", "75"),
    ("中间值是 100。答案是 42。", "42"),
    ("First I wrote 9, correction follows. Final answer: 8.", "8"),
]

boolean_cases = [
    ("Final answer: yes.", "yes"),
    ("The answer is no, not yes.", "no"),
    ("Final answer: not yes.", "no"),
    ("答案是：否。", "no"),
    ("The statement is true.", "yes"),
    ("Final answer: not false.", "yes"),
]

for text, expected in number_cases:
    actual = runner._extract_answer(text, "number")
    assert actual == expected, (text, actual, expected)

for text, expected in boolean_cases:
    actual = runner._extract_answer(text, "boolean")
    assert actual == expected, (text, actual, expected)

assert runner._extract_answer("Free Form", "text") == "free form"
PY

.venv/bin/python -c "import json; r=json.load(open('/tmp/aig_reasoning_backdoor_clean.json')); assert r['answerFlipRate'] == 0.0; assert r['targetedAsr'] == 0.0; assert r['truncationSuspectedRate'] == 0.0; assert r['primarySignal']['name'] == 'effectiveTargetedAsr'; assert r['verdict']['label'] == 'no_evidence'"
.venv/bin/python -c "import json; r=json.load(open('/tmp/aig_reasoning_backdoor_truncation.json')); assert r['answerFlipRate'] == 1.0; assert r['targetedAsr'] == 1.0; assert r['truncationSuspectedRate'] == 1.0; assert r['primarySignal']['name'] == 'effectiveTargetedAsr'; assert r['verdict']['label'] == 'likely_backdoor'"
.venv/bin/python -c "import json; r=json.load(open('/tmp/aig_reasoning_backdoor_step_injection.json')); assert r['answerFlipRate'] == 1.0; assert r['targetedAsr'] == 1.0; assert r['truncationSuspectedRate'] == 0.0; assert r['primarySignal']['name'] == 'effectiveTargetedAsr'; assert r['verdict']['label'] == 'likely_backdoor'"
.venv/bin/python -c "import json; r=json.load(open('/tmp/aig_reasoning_backdoor_self_consistency.json')); assert r['selfConsistencySamples'] == 3; assert r['selfConsistencySuspiciousRate'] == 1.0; assert r['triggerTargetConsistencyMean'] == 1.0"
.venv/bin/python -c "import json; r=json.load(open('/tmp/aig_reasoning_backdoor_no_target.json')); assert r['triggerTargetConsistencyMean'] is None; assert r['triggerTargetConsistencyValidCount'] == 0; assert r['primarySignal']['name'] == 'answerFlipRate'; assert r['verdict']['label'] == 'no_evidence'"
