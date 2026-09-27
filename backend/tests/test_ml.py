from datetime import UTC, datetime, timedelta

import joblib
import numpy as np
import pandas as pd
import pytest
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from app.ml import dormancy
from app.ml.anomaly import detect_anomalies
from app.ml.features import FEATURE_NAMES, commit_features

CUT = datetime(2024, 1, 1, tzinfo=UTC)


def test_features_ignore_future_commits_no_temporal_leakage():
    past = [CUT - timedelta(days=d) for d in (1, 5, 40, 100)]
    future = [CUT + timedelta(days=d) for d in (1, 2, 3)]
    base = commit_features(past, ["a", "b", "a", "c"], CUT)
    with_future = commit_features(past + future, ["a", "b", "a", "c", "x", "y", "z"], CUT)
    assert base == with_future


def test_feature_values():
    times = [CUT - timedelta(days=d) for d in (2, 10, 50, 120)]
    f = commit_features(times, ["a", "a", "b", "a"], CUT)
    assert list(f) == FEATURE_NAMES
    assert f["log_commits_30d"] == pytest.approx(np.log1p(2))
    assert f["log_commits_180d"] == pytest.approx(np.log1p(4))
    assert f["days_since_last_commit"] == pytest.approx(2)
    assert f["authors_90d"] == 2
    assert f["top_author_share_180d"] == 0.75


def test_features_none_when_inactive():
    assert commit_features([CUT - timedelta(days=400)], ["a"], CUT) is None


def weekly(values):
    frame = pd.DataFrame({"week_ending": [f"w{i}" for i in range(len(values))], "commits": values,
                          "issues_opened": [2] * len(values), "issues_closed": [2] * len(values),
                          "prs_opened": [1] * len(values), "prs_merged": [1] * len(values)})
    return frame


def test_anomaly_insufficient_data():
    assert detect_anomalies(weekly([0] * 52).assign(issues_opened=0, issues_closed=0, prs_opened=0,
                                                    prs_merged=0))["status"] == "insufficient_data"


def test_anomaly_detects_spike_with_reason_and_is_reproducible():
    rng = np.random.default_rng(0)
    values = list(rng.integers(8, 12, size=52))
    values[40] = 120
    first, second = detect_anomalies(weekly(values)), detect_anomalies(weekly(values))
    assert first == second
    flagged = {a["week_ending"]: a for a in first["anomalies"]}
    assert "w40" in flagged
    assert flagged["w40"]["reasons"][0]["feature"] == "commits"
    assert all(r["robust_z"] >= 3 or r["robust_z"] <= -3 for a in first["anomalies"] for r in a["reasons"])


@pytest.fixture
def model_file(tmp_path):
    rng = np.random.default_rng(1)
    # Synthetic data used ONLY to test code paths (loading, prediction, explanation) — not a result.
    X = rng.normal(size=(200, len(FEATURE_NAMES)))
    y = (X[:, 0] < 0).astype(int)
    pipe = Pipeline([("scaler", StandardScaler()), ("model", LogisticRegression())]).fit(X, y)
    path = tmp_path / "model.joblib"
    joblib.dump({"pipeline": pipe, "feature_names": FEATURE_NAMES, "version": "test"}, path)
    dormancy.load_artifact.cache_clear()
    return str(path)


def test_prediction_with_exact_linear_explanation(model_file):
    times = [CUT - timedelta(days=d) for d in range(1, 60, 3)]
    out = dormancy.predict_dormancy(times, ["a"] * len(times), CUT, model_file, data_truncated=False)
    assert out["status"] == "ok" and 0 <= out["probability_dormant_180d"] <= 1
    logit = out["intercept"] + sum(c["log_odds_contribution"] for c in out["contributions"])
    assert 1 / (1 + np.exp(-logit)) == pytest.approx(out["probability_dormant_180d"], abs=0.01)


def test_prediction_flags_truncated_data(model_file):
    out = dormancy.predict_dormancy([CUT - timedelta(days=1)], ["a"], CUT, model_file, data_truncated=True)
    assert out["status"] == "unreliable"


def test_prediction_not_applicable_for_inactive(model_file):
    assert dormancy.predict_dormancy([], [], CUT, model_file, False)["status"] == "not_applicable"


def test_missing_model_reported_honestly(tmp_path):
    dormancy.load_artifact.cache_clear()
    out = dormancy.predict_dormancy([CUT], ["a"], CUT, str(tmp_path / "none.joblib"), False)
    assert out["status"] == "model_unavailable"


def test_feature_mismatch_rejected(tmp_path):
    path = tmp_path / "bad.joblib"
    joblib.dump({"pipeline": None, "feature_names": ["x"], "version": "bad"}, path)
    dormancy.load_artifact.cache_clear()
    with pytest.raises(ValueError):
        dormancy.load_artifact(str(path))


def test_shipped_artifact_loads_if_present():
    from pathlib import Path
    path = Path(__file__).resolve().parents[1] / "app" / "ml" / "artifacts" / "dormancy_model.joblib"
    if not path.exists():
        pytest.skip("model not trained")
    dormancy.load_artifact.cache_clear()
    artifact = dormancy.load_artifact(str(path))
    assert artifact["feature_names"] == FEATURE_NAMES
    assert "roc_auc" in artifact["test_metrics"]
