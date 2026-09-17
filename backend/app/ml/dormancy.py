"""Serving side of the EXPERIMENTAL dormancy model.

Loads the logistic-regression pipeline produced by ml/train_dormancy.py. For a linear model on standardised
features, each feature's contribution to the log-odds is exactly coef_j × z_j, so the explanation is exact
(no approximation such as SHAP is needed). If no trained artifact exists, the API reports that honestly.
"""

from datetime import datetime
from functools import lru_cache
from pathlib import Path

import joblib
import numpy as np

from app.ml.features import FEATURE_NAMES, commit_features


@lru_cache(maxsize=4)
def load_artifact(path: str) -> dict | None:
    file = Path(path)
    if not file.exists():
        return None
    artifact = joblib.load(file)
    if artifact.get("feature_names") != FEATURE_NAMES:
        raise ValueError("Model artifact was trained with a different feature set.")
    return artifact


def predict_dormancy(times: list[datetime], authors: list[str], cutoff: datetime, model_path: str,
                     data_truncated: bool) -> dict:
    artifact = load_artifact(model_path)
    if artifact is None:
        return {"status": "model_unavailable", "message": "No trained model artifact. Run ml/train_dormancy.py."}
    feats = commit_features(times, authors, cutoff)
    if feats is None:
        return {"status": "not_applicable", "message": "No commits in the last 180 days; the model only scores "
                                                        "projects that are currently active."}
    pipeline = artifact["pipeline"]
    x = np.array([[feats[n] for n in FEATURE_NAMES]])
    probability = float(pipeline.predict_proba(x)[0, 1])
    scaler, clf = pipeline.named_steps["scaler"], pipeline.named_steps["model"]
    z = scaler.transform(x)[0]
    contributions = sorted(
        ({"feature": n, "value": round(feats[n], 3), "log_odds_contribution": round(float(c * zi), 3)}
         for n, c, zi in zip(FEATURE_NAMES, clf.coef_[0], z, strict=True)),
        key=lambda d: abs(d["log_odds_contribution"]), reverse=True)
    return {
        "status": "ok" if not data_truncated else "unreliable",
        "message": ("Commit data was truncated by the page cap; features may be underestimated."
                    if data_truncated else "Experimental estimate — see model card for measured performance."),
        "probability_dormant_180d": round(probability, 3),
        "intercept": round(float(clf.intercept_[0]), 3),
        "contributions": contributions,
        "model_version": artifact.get("version"),
        "test_metrics": artifact.get("test_metrics"),
    }
