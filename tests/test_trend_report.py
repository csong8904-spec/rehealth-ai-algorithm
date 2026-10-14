import pytest

from healthsynth.trend_report import make_trend_report


def test_low_coverage_abstains_without_health_claim():
    report = make_trend_report({"resting_heart_rate": 80}, {"resting_heart_rate": 70}, coverage=0.69)
    assert report.status == "insufficient_data"
    assert report.facts == ()


def test_comparison_is_observational_and_traceable():
    report = make_trend_report(
        {"resting_heart_rate": 76, "daily_steps": 7400},
        {"resting_heart_rate": 68, "daily_steps": 8000}, coverage=0.9,
    )
    assert report.status == "generated"
    assert [(fact.metric, fact.direction) for fact in report.facts] == [
        ("resting_heart_rate", "上升"), ("daily_steps", "下降")
    ]
    assert "疾病风险" in report.text
    assert "人工智能生成" in report.synthesis_label


@pytest.mark.parametrize("value", [float("nan"), float("inf"), -1, 300, True])
def test_invalid_metric_is_rejected(value):
    with pytest.raises(ValueError):
        make_trend_report({"resting_heart_rate": value}, {"resting_heart_rate": 70}, coverage=1)


def test_missing_comparable_metric_abstains():
    report = make_trend_report({"daily_steps": 6000}, {}, coverage=1)
    assert report.status == "insufficient_data"
