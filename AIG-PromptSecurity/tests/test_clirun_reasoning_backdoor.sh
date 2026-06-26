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

.venv/bin/python -c "import json; r=json.load(open('/tmp/aig_reasoning_backdoor_clean.json')); assert r['answerFlipRate'] == 0.0; assert r['targetedAsr'] == 0.0; assert r['truncationSuspectedRate'] == 0.0"
.venv/bin/python -c "import json; r=json.load(open('/tmp/aig_reasoning_backdoor_truncation.json')); assert r['answerFlipRate'] == 1.0; assert r['targetedAsr'] == 1.0; assert r['truncationSuspectedRate'] == 1.0"
.venv/bin/python -c "import json; r=json.load(open('/tmp/aig_reasoning_backdoor_step_injection.json')); assert r['answerFlipRate'] == 1.0; assert r['targetedAsr'] == 1.0; assert r['truncationSuspectedRate'] == 0.0"
.venv/bin/python -c "import json; r=json.load(open('/tmp/aig_reasoning_backdoor_self_consistency.json')); assert r['selfConsistencySamples'] == 3; assert r['selfConsistencySuspiciousRate'] == 1.0; assert r['triggerTargetConsistencyMean'] == 1.0"
.venv/bin/python -c "import json; r=json.load(open('/tmp/aig_reasoning_backdoor_no_target.json')); assert r['triggerTargetConsistencyMean'] is None; assert r['triggerTargetConsistencyValidCount'] == 0"
