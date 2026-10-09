<p align="center">
  <img src="docs/assets/banner.svg" width="100%" alt="ReHealth AI — Fail-Closed Health Intelligence" />
</p>

<h1 align="center">ReHealth AI</h1>

<p align="center">
  <strong>Fail-closed health intelligence for wearable time series.</strong><br/>
  Turn noisy biosignals into grounded, auditable health trend reports—without pretending to be a doctor.
</p>

<p align="center">
  <a href="https://github.com/csong8904-spec/rehealth-ai-algorithm/actions/workflows/ci.yml"><img src="https://github.com/csong8904-spec/rehealth-ai-algorithm/actions/workflows/ci.yml/badge.svg" alt="CI" /></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-Apache--2.0-2ea44f" alt="Apache-2.0" /></a>
  <img src="https://img.shields.io/badge/Python-3.10%2B-3776AB" alt="Python 3.10+" />
  <img src="https://img.shields.io/badge/safety-fail--closed-12B886" alt="Fail-closed" />
  <img src="https://img.shields.io/badge/status-research%20preview-F59E0B" alt="Research preview" />
</p>

<p align="center">
  <a href="#-60-second-start">60-second start</a> ·
  <a href="#-what-is-new">What is new</a> ·
  <a href="#-evidence-not-hype">Benchmarks</a> ·
  <a href="README_CN.md">中文说明</a> ·
  <a href="docs/algorithm-design.md">Deep dive</a>
</p>

> [!IMPORTANT]
> **Research software, not a medical device.** ReHealth AI does not diagnose disease, prescribe
> treatment, or make emergency decisions. Its current PPG model deliberately fails the production
> release gate. That failure is published—not hidden.

## The idea

Most health-AI demos optimize for a persuasive answer. ReHealth AI optimizes for a defensible one.

It separates **signal estimation**, **risk inference**, and **language generation** into independently
testable boundaries. Every boundary can refuse to proceed. The result is a reference architecture for
teams building wellness analytics where uncertainty, provenance, and abstention matter as much as output.

<p align="center">
  <img src="docs/assets/architecture.svg" width="100%" alt="ReHealth AI architecture" />
</p>

## ✦ What is new

| Design | Why it matters |
|---|---|
| **Motion-reference PPG denoising** | Learns the acceleration-correlated component inside each inference window and removes it before spectral candidate ranking—without ECG leakage. |
| **Fact firewall** | The generator receives validated facts, not raw health records. Unsupported numbers and medical claims never become generation context. |
| **Fail-closed model promotion** | Accuracy, P90 tail error, coverage, and cohort size are executable gates. A failed model cannot produce an activation manifest. |
| **Tamper-evident inference trail** | Privacy-minimized audit events are chained by hash, making silent log modification detectable without storing raw health measurements. |

This is not a wrapper around a chat model. The risk path runs independently; a language model is optional
and replaceable. The deterministic generator remains the safe default until a reviewed local model passes
fact-consistency and medical-boundary evaluation.

## ⚡ 60-second start

```bash
git clone https://github.com/csong8904-spec/rehealth-ai-algorithm.git
cd rehealth-ai-algorithm
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -e .
python -m unittest discover -s tests -v
python -m healthsynth.cli demo --model artifacts/risk_model.json
```

Run the dependency-light local API:

```bash
python -m healthsynth.api --audit-salt "replace-with-a-managed-secret"
```

```http
POST /v1/reports
Content-Type: application/json

{
  "user_key": "demo-001",
  "period_start": "2026-10-01",
  "period_end": "2026-10-07",
  "valid_coverage": 0.91,
  "metrics": {"resting_heart_rate": 72, "sleep_duration": 6.8, "activity": 7600, "spo2": 97},
  "baseline": {"resting_heart_rate": 66, "sleep_duration": 7.4, "activity": 8200, "spo2": 98}
}
```

Every response carries `X-AI-Generated: true`, a visible synthesis notice, evidence, confidence, and any
safety action applied by the output boundary.

## ◎ Evidence, not hype

We publish complete subject-isolated results, including regressions and rejected ideas. PhysioNet ECG
annotations are evaluation labels only; they are never available to PPG inference.

<p align="center">
  <img src="docs/assets/benchmark.svg" width="88%" alt="PPG candidate benchmark" />
</p>

| Candidate | MAE ↓ | P90 ↓ | Within 10 bpm ↑ | Decision |
|---|---:|---:|---:|---|
| Spectral baseline v0.1 | 19.96 | **48.51** | 47.37% | Blocked |
| Candidate ranker v0.2 | 24.06 | 69.28 | 61.11% | Blocked |
| Temporal decoder v0.4 | 29.90 | 74.07 | 55.56% | Rejected |
| **Adaptive denoising v0.5** | **19.70** | 56.06 | **66.67%** | Research champion; blocked |
| Denoising + group softmax v0.6 | 21.44 | 56.53 | 55.56% | Rejected |

The frozen production gate requires MAE ≤10 bpm, P90 ≤15 bpm, ≥90% within 10 bpm, ≥50% coverage,
≥20 subjects, and ≥100 records. This benchmark contains 8 subjects and 18 evaluable records. **No model
is production-approved.** See the [full benchmark history](docs/benchmark-results.md) and the machine-readable
[release decision](artifacts/release-decisions/ppg-motion-ranker-adaptive-denoise-v1.json).

## ⛨ Safety is a runtime property

```text
Authorized metrics
      │
      ▼
Data-quality gate ── insufficient ──▶ abstain
      │ valid
      ▼
Structured inference ── gate failed ─▶ no activation
      │ approved facts
      ▼
Constrained synthesis ── unsafe text ─▶ safe fallback
      │
      ▼
AI label + hash-chain audit
```

The repository ships with a medical-boundary red-team suite covering diagnosis, medication instructions,
cure guarantees, care avoidance, and emergency exclusion. Run it with:

```bash
python scripts/evaluate_safety.py
```

## Reproduce the signal experiment

```bash
python scripts/download_wrist_dataset.py
python scripts/benchmark_wrist_dataset.py
python scripts/train_fusion_ranker.py --adaptive-denoise \
  --model artifacts/models/ppg_motion_ranker_adaptive_denoise_v1.json \
  --report artifacts/benchmarks/ppg_motion_ranker_adaptive_denoise_v1_loso.json
```

Raw datasets, audit logs, secrets, virtual environments, and report-generator checkpoints are excluded
from Git. Public artifacts include checksums, candidate models, complete benchmark outputs, and release
decisions so results can be inspected rather than trusted.

## Repository map

```text
src/healthsynth/       inference · biosignal processing · safety · audit · release gates
scripts/               dataset · training · evaluation · delivery automation
artifacts/benchmarks/  complete public-data results, including failed candidates
artifacts/models/      small research checkpoints with preprocessing metadata
docs/                  architecture · model card · data register · filing notes
tests/                 deterministic unit and safety tests
configs/               optional local-LLM QLoRA configuration
```

## Roadmap

- [x] Subject-isolated PPG benchmark and official checksum verification
- [x] Accelerometer-referenced waveform denoising
- [x] Medical-boundary red team and fail-closed release gate
- [x] Fact-constrained deterministic synthesis and local-LM adapter
- [ ] Cross-device, cross-population public benchmark
- [ ] Waveform morphology and signal-quality representation learning
- [ ] Professionally reviewed bilingual report dataset
- [ ] Calibrated uncertainty and subgroup robustness evaluation

## Build with us

Useful contributions include new public-dataset adapters, signal-quality features, stronger abstention,
privacy tests, bilingual safety cases, and reproducible baselines. Start with
[CONTRIBUTING.md](CONTRIBUTING.md), and never place personal health data in an issue or pull request.

If the project's approach resonates with you, **star the repository**—it helps more researchers find an
honest, safety-first health-AI baseline.

## License and data rights

Code is licensed under [Apache-2.0](LICENSE). Datasets, model weights, and dependencies retain their own
licenses. The software license grants no medical authorization, data rights, or approval for clinical use.

<p align="center"><sub>Built for evidence over confidence · 可验证，胜过看起来可信</sub></p>
