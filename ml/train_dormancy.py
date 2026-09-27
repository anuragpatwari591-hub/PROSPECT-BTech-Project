"""Step 2 of the ML experiment: build the dataset, train, evaluate, and save the model + model card.

TASK (binary classification)
  For a repository that is ACTIVE at cutoff date T (≥ 1 non-bot commit in the 90 days before T), predict
  whether it will have ZERO non-bot commits in the following 180 days, (T, T + 180d].
LABEL SOURCE
  Derived from the repository's own future commit history — no manual labelling, no fabricated data.
LEAKAGE CONTROLS
  * Features use only commits authored ≤ T (app/ml/features.py); labels use only commits > T.
  * T + 180d must be ≤ collection date, so every label is fully observed.
  * Train/test split is BY REPOSITORY (GroupShuffleSplit): no repository appears in both sets, because
    successive cutoffs of one repository are highly correlated.
  * Model selection uses GroupKFold cross-validation on the training repositories only; the test set is used once.
BASELINES
  * Majority-class prior (DummyClassifier).
  * One-line rule: predict dormant if days_since_last_commit > 60.

Usage:  python ml/train_dormancy.py
"""

import json
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.dummy import DummyClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score, average_precision_score, balanced_accuracy_score, confusion_matrix, f1_score,
    precision_score, recall_score, roc_auc_score,
)
from sklearn.model_selection import GroupKFold, GroupShuffleSplit
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parent / "backend"))
from app.ml.features import FEATURE_NAMES, commit_features  # noqa: E402

SEED = 42
STEP_DAYS = 90
HORIZON_DAYS = 180
MIN_HISTORY_DAYS = 365
VERSION = "dormancy-lr-1.0"


def build_dataset(collection_date: datetime) -> pd.DataFrame:
    rows = []
    for csv_file in sorted((ROOT / "data" / "commits").glob("*.csv")):
        repo = csv_file.stem.replace("__", "/")
        frame = pd.read_csv(csv_file)
        frame = frame[frame["is_bot"] == 0]
        if frame.empty:
            continue
        times = [datetime.fromtimestamp(int(t), UTC) for t in frame["authored_ts"]]
        authors = frame["author_hash"].astype(str).tolist()
        ts_array = np.array([t.timestamp() for t in times])
        cutoff = min(times) + timedelta(days=MIN_HISTORY_DAYS)
        last_cutoff = collection_date - timedelta(days=HORIZON_DAYS)
        while cutoff <= last_cutoff:
            feats = commit_features(times, authors, cutoff)
            if feats and feats["log_commits_90d"] > 0:
                c, h = cutoff.timestamp(), (cutoff + timedelta(days=HORIZON_DAYS)).timestamp()
                future = int(((ts_array > c) & (ts_array <= h)).sum())
                rows.append({"repo": repo, "cutoff": cutoff.date().isoformat(), **feats,
                             "label_dormant_180d": int(future == 0)})
            cutoff += timedelta(days=STEP_DAYS)
    return pd.DataFrame(rows)


def evaluate(y_true, y_pred, y_score=None) -> dict:
    out = {
        "accuracy": accuracy_score(y_true, y_pred), "balanced_accuracy": balanced_accuracy_score(y_true, y_pred),
        "precision": precision_score(y_true, y_pred, zero_division=0),
        "recall": recall_score(y_true, y_pred, zero_division=0), "f1": f1_score(y_true, y_pred, zero_division=0),
        "confusion_matrix": confusion_matrix(y_true, y_pred, labels=[0, 1]).tolist(),
    }
    if y_score is not None and len(set(y_true)) == 2:
        out["roc_auc"] = roc_auc_score(y_true, y_score)
        out["pr_auc"] = average_precision_score(y_true, y_score)
    return {k: (round(float(v), 3) if isinstance(v, float | np.floating) else v) for k, v in out.items()}


def cluster_bootstrap_ci(y, score, groups, n_boot=1000) -> dict:
    """95% CI by resampling whole test REPOSITORIES with replacement (samples within a repo are correlated)."""
    rng = np.random.default_rng(SEED)
    repos = np.unique(groups)
    index = {r: np.where(groups == r)[0] for r in repos}
    roc, pr = [], []
    for _ in range(n_boot):
        idx = np.concatenate([index[r] for r in rng.choice(repos, size=len(repos), replace=True)])
        if len(set(y[idx])) == 2:
            roc.append(roc_auc_score(y[idx], score[idx]))
            pr.append(average_precision_score(y[idx], score[idx]))
    q = lambda v: [round(float(np.percentile(v, 2.5)), 3), round(float(np.percentile(v, 97.5)), 3)]  # noqa: E731
    return {"roc_auc_95ci": q(roc), "pr_auc_95ci": q(pr), "valid_resamples": len(roc)}


def models() -> dict:
    return {
        "logistic_regression": Pipeline([("scaler", StandardScaler()), ("model", LogisticRegression(
            class_weight="balanced", max_iter=2000, random_state=SEED))]),
        "random_forest": Pipeline([("scaler", StandardScaler()), ("model", RandomForestClassifier(
            n_estimators=300, min_samples_leaf=5, class_weight="balanced", random_state=SEED, n_jobs=1))]),
    }


def main() -> None:
    collection_date = datetime.now(UTC)
    data = build_dataset(collection_date)
    results_dir = ROOT / "results"
    results_dir.mkdir(exist_ok=True)
    data.to_csv(ROOT / "data" / "dormancy_dataset.csv", index=False)
    summary = data.groupby("repo").agg(samples=("label_dormant_180d", "size"),
                                       dormant=("label_dormant_180d", "sum")).reset_index()
    summary.to_csv(ROOT / "data" / "dataset_summary.csv", index=False)

    X, y, groups = data[FEATURE_NAMES].to_numpy(), data["label_dormant_180d"].to_numpy(), data["repo"].to_numpy()
    splitter = GroupShuffleSplit(n_splits=1, test_size=0.2, random_state=SEED)
    train_idx, test_idx = next(splitter.split(X, y, groups))
    assert not set(groups[train_idx]) & set(groups[test_idx]), "repository leakage between train and test"

    cv = {}
    for name, pipe in models().items():
        fold_scores = []
        for tr, va in GroupKFold(n_splits=5).split(X[train_idx], y[train_idx], groups[train_idx]):
            pipe.fit(X[train_idx][tr], y[train_idx][tr])
            prob = pipe.predict_proba(X[train_idx][va])[:, 1]
            if len(set(y[train_idx][va])) == 2:
                fold_scores.append(average_precision_score(y[train_idx][va], prob))
        cv[name] = {"cv_pr_auc_mean": round(float(np.mean(fold_scores)), 3),
                    "cv_pr_auc_std": round(float(np.std(fold_scores)), 3), "folds": len(fold_scores)}

    test = {}
    fitted = {}
    for name, pipe in models().items():
        pipe.fit(X[train_idx], y[train_idx])
        fitted[name] = pipe
        prob = pipe.predict_proba(X[test_idx])[:, 1]
        test[name] = evaluate(y[test_idx], (prob >= 0.5).astype(int), prob)
        test[name].update(cluster_bootstrap_ci(y[test_idx], prob, groups[test_idx]))
    dummy = DummyClassifier(strategy="prior").fit(X[train_idx], y[train_idx])
    test["baseline_majority_prior"] = evaluate(y[test_idx], dummy.predict(X[test_idx]),
                                               dummy.predict_proba(X[test_idx])[:, 1])
    days = data["days_since_last_commit"].to_numpy()
    test["baseline_rule_days_since_last_commit_gt_60"] = evaluate(
        y[test_idx], (days[test_idx] > 60).astype(int), days[test_idx])
    test["baseline_rule_days_since_last_commit_gt_60"].update(
        cluster_bootstrap_ci(y[test_idx], days[test_idx], groups[test_idx]))

    lr = fitted["logistic_regression"]
    coefficients = dict(zip(FEATURE_NAMES, np.round(lr.named_steps["model"].coef_[0], 3).tolist(), strict=True))
    rf_importance = dict(zip(FEATURE_NAMES, np.round(
        fitted["random_forest"].named_steps["model"].feature_importances_, 3).tolist(), strict=True))

    report = {
        "version": VERSION, "trained_at": collection_date.isoformat(), "seed": SEED,
        "task": f"P(zero non-bot commits in next {HORIZON_DAYS} days | active in last 90 days)",
        "dataset": {"repositories": int(data["repo"].nunique()), "samples": int(len(data)),
                    "positive_rate": round(float(y.mean()), 3),
                    "train_repositories": int(len(set(groups[train_idx]))), "train_samples": int(len(train_idx)),
                    "test_repositories": int(len(set(groups[test_idx]))), "test_samples": int(len(test_idx)),
                    "test_positive_rate": round(float(y[test_idx].mean()), 3),
                    "test_repository_list": sorted(set(groups[test_idx]))},
        "cross_validation_on_train": cv, "test": test,
        "logistic_regression_coefficients_standardised": coefficients,
        "random_forest_impurity_importance": rf_importance,
    }
    (results_dir / "metrics.json").write_text(json.dumps(report, indent=2))
    (ROOT.parent / "backend" / "app" / "ml" / "artifacts" / "metrics.json").write_text(json.dumps(report, indent=2))

    artifact_dir = ROOT.parent / "backend" / "app" / "ml" / "artifacts"
    artifact_dir.mkdir(parents=True, exist_ok=True)
    # The SERVED model is logistic regression (exactly explainable); RF is reported for comparison only.
    joblib.dump({"pipeline": lr, "feature_names": FEATURE_NAMES, "version": VERSION,
                 "test_metrics": test["logistic_regression"], "trained_at": collection_date.isoformat()},
                artifact_dir / "dormancy_model.joblib")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
