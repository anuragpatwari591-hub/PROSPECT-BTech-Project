"""Commit-history features shared by the offline experiment (ml/train_dormancy.py) and the API.

Using ONE implementation for training and serving prevents training/serving skew.
Only commits authored at or before `cutoff` are used (no look-ahead → no temporal leakage).
"""

from datetime import datetime, timedelta

import numpy as np

FEATURE_NAMES = [
    "log_commits_30d", "log_commits_90d", "log_commits_180d", "active_weeks_ratio_26w",
    "days_since_last_commit", "recent_rate_ratio", "authors_90d", "top_author_share_180d",
]


def commit_features(times: list[datetime], authors: list[str], cutoff: datetime) -> dict[str, float] | None:
    """Return the feature dict, or None if there is no commit in the 180 days before cutoff."""
    pairs = [(t, a) for t, a in zip(times, authors, strict=True) if cutoff - timedelta(days=180) < t <= cutoff]
    if not pairs:
        return None
    ages = np.array([(cutoff - t).total_seconds() / 86400 for t, _ in pairs])
    c30, c90, c180 = int((ages <= 30).sum()), int((ages <= 90).sum()), len(pairs)
    weeks = {int(a // 7) for a in ages if a < 182}
    authors_90 = {a for (_, a), age in zip(pairs, ages, strict=True) if age <= 90}
    _, counts = np.unique([a for _, a in pairs], return_counts=True)
    return {
        "log_commits_30d": float(np.log1p(c30)),
        "log_commits_90d": float(np.log1p(c90)),
        "log_commits_180d": float(np.log1p(c180)),
        "active_weeks_ratio_26w": len(weeks) / 26,
        "days_since_last_commit": float(ages.min()),
        # Smoothed ratio of the last-30-day commit rate to the 180-day rate (1 = steady, <1 = slowing).
        "recent_rate_ratio": float((c30 + 1) / (c180 * 30 / 180 + 1)),
        "authors_90d": float(len(authors_90)),
        "top_author_share_180d": float(counts.max() / counts.sum()),
    }
