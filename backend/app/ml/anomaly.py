"""EXPERIMENTAL unsupervised anomaly detection over weekly activity.

Isolation Forest (Liu, Ting & Zhou, 2008) scores each of the last 52 weeks by how easy it is to isolate from
the repository's own other weeks. A week is reported only if (a) Isolation Forest labels it an outlier AND
(b) at least one activity feature deviates by ≥ 3 robust z-scores (median/MAD) — so every flag comes with a
human-readable reason. This output is informational and is NOT part of the risk score.
"""

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest

FEATURES = ["commits", "issues_opened", "issues_closed", "prs_opened", "prs_merged"]
MIN_ACTIVE_WEEKS = 12


def detect_anomalies(weekly: pd.DataFrame, seed: int = 42) -> dict:
    X = weekly[FEATURES].to_numpy(dtype=float)
    active = int((X.sum(axis=1) > 0).sum())
    if len(X) < 26 or active < MIN_ACTIVE_WEEKS:
        return {"status": "insufficient_data", "active_weeks": active,
                "message": f"Needs at least {MIN_ACTIVE_WEEKS} active weeks in the last 52.", "anomalies": []}
    model = IsolationForest(n_estimators=200, contamination="auto", random_state=seed).fit(X)
    labels = model.predict(X)
    scores = model.score_samples(X)
    median = np.median(X, axis=0)
    mad = np.median(np.abs(X - median), axis=0) * 1.4826
    scale = np.where(mad > 0, mad, np.maximum(X.std(axis=0), 1.0))
    z = (X - median) / scale
    anomalies = []
    for idx in np.where(labels == -1)[0]:
        reasons = [
            {"feature": f, "value": int(X[idx, j]), "typical": float(median[j]), "robust_z": round(float(z[idx, j]), 1)}
            for j, f in enumerate(FEATURES) if abs(z[idx, j]) >= 3
        ]
        if reasons:
            anomalies.append({"week_ending": weekly.iloc[idx]["week_ending"], "score": round(float(scores[idx]), 3),
                              "reasons": reasons})
    return {"status": "ok", "active_weeks": active, "method": "IsolationForest + robust z-score filter",
            "anomalies": anomalies}
