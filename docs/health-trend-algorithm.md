# ReHealth AI health-trend report algorithm / 睿禾健康趋势报告算法

This document describes **睿禾健康趋势报告生成合成算法**. The filing workbook supplied by the operator is a *structure reference only*: its digital-human voice content is not part of this algorithm.

## Product boundary

The first report capability compares a user's validated period aggregates with that same user's baseline and writes an evidence-linked, non-diagnostic trend summary. It does **not** infer chronic disease, issue emergency alerts, recommend medication, or substitute for a clinician. The current PPG research risk candidate is blocked and is excluded from the live report path.

## Input → facts → synthesis → output

| Stage | Current implementation | Production gate |
|---|---|---|
| Input | Period summaries: resting heart rate, sleep duration, daily steps; corresponding personal baselines; coverage | User authentication, separate consent for sensitive health data, lawful provenance, date/window validation |
| Quality | Finite values, supported ranges, coverage ≥ 70%; otherwise abstain | Device/source normalization, missingness and subgroup validation on authorized real data |
| Fact construction | Per-metric current value, baseline, absolute difference, and direction | Versioned definitions, temporal leakage checks, validation by health-domain reviewers |
| Text | Deterministic observational narrative in `trend_report.py` | Optional approved generative model only after fact-constrained prompt, output verification, security and privacy review |
| Output | Report text, structured facts, limitations, visible AI-generation label | Persistent provenance label, feedback/complaint channel, audit and human-review workflow |

The `min_change` constants in code are display thresholds for noticing a numerical difference; they are **not medical reference ranges or risk cutoffs**. Coverage 70% is an engineering abstention default, not a clinically validated safety threshold. These values require target-population validation before any claim of health-risk prediction.

## Model base and training

The fact engine is deterministic and requires no large model or GPU training. A large model is useful only for controlled wording after facts are frozen. If DeepSeek is selected, keep `DEEPSEEK_API_KEY` in a server-side secret store; never commit it or expose it to the browser. Send the minimum necessary de-identified fact packet, disclose that third-party processing to users, and review data-transfer legality and contracts before enabling it. Do not send names, phone numbers, raw waveforms, or full medical history by default.

Training/fine-tuning is **not required** to launch a carefully bounded numerical trend comparator. If future fine-tuning is pursued, use only licensed/authorized, de-identified and human-reviewed examples; separate subjects across train/validation/test; freeze the test set, assess subgroup and safety performance, and retain model/data lineage. Existing synthetic training and the blocked PPG benchmark do not establish clinical validity.

## Information disclosure mapping

The public algorithm site should provide: exact algorithm name and service scope; input/output and process; source and limits of data; model base and whether training is used; explicit AI-content label and verifiable provenance; product terms and privacy notice; complaint channel; safety-review process and release status. Internal evidence should contain machine-review rules, human-review records, audit retention, consent records, security tests and screenshots captured from the *actual* working systems. Do not fabricate a filing number, license, screenshot, model training run, or approved risk accuracy.

## Release separation

`src/healthsynth/trend_report.py` is an inspectable algorithm component. `src/healthsynth/api.py` is a local development API **without production authentication** and uses the research risk model; do not expose it to the public internet. The public research site does not constitute a live personal health-report service. A true production launch additionally needs authentication, sensitive-data consent, reviewed legal notices, retention/deletion controls, report provenance, complaint and human-review operations, security monitoring, and a tested deployment. The operator's key and infrastructure access alone cannot substitute for those gates.
