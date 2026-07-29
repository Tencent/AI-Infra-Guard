# API Checker third-party notices

The integrated checker retains the following third-party components and
attributions in addition to the repository-level `License.txt`.

## Ventor QTest

- Upstream: `kexinoh/ventor_qtest`
- Integrated upstream revision noted by the imported project: `b76c2a2`
- License: MIT
- Full license text: `ventor_qtest/LICENSE`

## PAMELA

- Project: PAMELA — Probing And Measuring Emergent LLM Alignments
- The local upstream package declares MIT in its `package.json`.
- The generated reference dataset used here is
  `pamela/reference/distributions.json`; provenance and checksum are recorded
  in `pamela/reference/README.md`.
- The checker implementation is a Python port of PAMELA matching and
  normalization behavior.

## Relay audit probes

The seven OpenAI-compatible relay probes originate from Tencent Zhuque Lab's
A.I.G relay audit capability and are integrated into the same AIG repository.
