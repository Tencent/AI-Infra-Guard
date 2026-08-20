# Aggregate results

The sanitized CSV contains one row per completed run without prompts, generated
model text, tool arguments, internal paths, credentials, or provider-specific
transport fields. Recreate aggregate tables with:

```bash
python3 analysis/aggregate_statistics.py results/sanitized_results.csv \
  --out-dir results/aggregate
```

## Overall outcomes

| Evaluator | Full success | Partial compliance | Broad influence |
|---|---:|---:|---:|
| `J_R` deterministic evaluator | 5.6% | 2.0% | 7.6% |
| `J_L` semantic evaluator | 5.3% | 7.3% | 12.6% |

`J_R` and `J_L` are described in the accompanying technical report. Full and
partial are mutually exclusive. Broad influence is their sum.

## High-signal slices

| Slice | Result |
|---|---:|
| Fake-completion attack, text mode, `J_L` full | 17.0% |
| Hidden-Unicode channel, file mode, `J_R` full | 25.5% |
| Skills channel, file mode, `J_R` full | 16.0% |
| Skill-loading source tool, `J_R` / `J_L` full | 15.2% / 13.7% |

These values describe the controlled configuration in this release. They are
not general vulnerability rates for all DeepSeek Harness deployments.
