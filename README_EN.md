<p align="center"><img src="docs/assets/banner.svg" alt="ReHealth AI" width="900" /></p>

<p align="center"><strong>Safety-first health trend report synthesis for wearable and check-up data</strong><br/>
<a href="README.md">中文</a> · <a href="docs/algorithm-design.md">Algorithm design</a> · <a href="docs/benchmark-results.md">Benchmarks</a></p>

<p align="center">
  <a href="https://github.com/csong8904-spec/rehealth-ai-algorithm/actions/workflows/ci.yml"><img src="https://github.com/csong8904-spec/rehealth-ai-algorithm/actions/workflows/ci.yml/badge.svg" alt="CI" /></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-Apache--2.0-2ea44f" alt="Apache-2.0" /></a>
  <img src="https://img.shields.io/badge/status-research%20only-f59e0b" alt="Research only" />
</p>

> [!WARNING]
> This is a research and engineering reference, not a medical device. It does not diagnose disease,
> prescribe treatment, or make emergency decisions. The current PPG model is blocked from production.

## Overview

**ReHealth AI Health Trend Report Synthesis Algorithm** turns authorized wearable or check-up metrics
into evidence-grounded health trend reports with confidence and AI labels. It is fail-closed: insufficient
data, an unqualified model, or unsafe generated text suppresses the risk conclusion.

<p align="center"><img src="docs/assets/architecture.svg" alt="Architecture" width="900" /></p>

## Highlights

- Data-quality controls, missingness detection, and personal-baseline comparison
- Wrist PPG and tri-axial accelerometer fusion with motion-artifact suppression
- Subject-isolated validation to prevent user-level leakage
- Structured risk prediction and fact-constrained Chinese report generation
- Blocking of diagnoses, prescriptions, cure claims, and unsupported medical statements
- Visible AI labels, machine-readable API labels, and hash-chained audit logs
- Release gates for accuracy, tail error, coverage, and validation sample size
- Optional local causal-LM adapter and QLoRA training configuration

## Public-data benchmark

PhysioNet wrist PPG exercise data is used for offline engineering validation. ECG annotations are held
out as evaluation labels and are never inference inputs.

<p align="center"><img src="docs/assets/benchmark.svg" alt="Candidate benchmark comparison" width="820" /></p>

| Candidate | MAE ↓ | P90 error ↓ | Within 10 bpm ↑ | Decision |
|---|---:|---:|---:|---|
| Spectral baseline v0.1 | 19.96 | 48.51 | 47.37% | Blocked |
| Candidate ranker v0.2 | 24.06 | 69.28 | 61.11% | Blocked |
| Temporal decoder v0.4 | 29.90 | 74.07 | 55.56% | Rejected |
| Adaptive denoising v0.5 | **19.70** | 56.06 | **66.67%** | Research champion; blocked |
| Denoising + softmax v0.6 | 21.44 | 56.53 | 55.56% | Rejected |

The frozen gate requires MAE ≤10 bpm, P90 ≤15 bpm, ≥90% of records within 10 bpm, ≥50% coverage,
at least 20 subjects, and at least 100 records. The benchmark has only 8 subjects and 18 evaluable
records, so no candidate is approved for production.

## Quick start

Python 3.10+ is required. The core package only depends on NumPy.

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# Linux/macOS: source .venv/bin/activate
pip install -e .
python -m unittest discover -s tests -v
```

```bash
python -m healthsynth.cli train-synthetic --output artifacts
python -m healthsynth.cli demo --model artifacts/risk_model.json
python -m healthsynth.api --audit-salt "replace-with-a-managed-secret"
```

## Reproducing the PPG experiment

```bash
python scripts/download_wrist_dataset.py
python scripts/benchmark_wrist_dataset.py
python scripts/train_fusion_ranker.py --adaptive-denoise \
  --model artifacts/models/ppg_motion_ranker_adaptive_denoise_v1.json \
  --report artifacts/benchmarks/ppg_motion_ranker_adaptive_denoise_v1_loso.json
python scripts/evaluate_safety.py
```

Raw datasets, audit logs, environments, and report-generator checkpoints are excluded from Git.

## Safety and governance

The repository includes a model card, data register, benchmark history, medical-boundary red-team suite,
and a fail-closed release gate. Synthetic SFT examples are for pipeline testing only and have not been
professionally reviewed. Real deployment requires independent privacy, content-safety, medical-boundary,
and target-population validation.

See [SECURITY.md](SECURITY.md) before reporting a vulnerability. Never place personal health data in a
public issue.

## License

Code is released under the [Apache License 2.0](LICENSE). Datasets, base models, and third-party
dependencies retain their own licenses. This license grants no medical authorization or data rights.
