# 07 — Machine Learning Methodology and Results

## 1. Is supervised learning defensible here?

Asking "is this project risky?" has no ground-truth label: no public dataset labels GitHub repositories with project risk, and inventing labels would be fabrication. We therefore **did not** train a model to predict the risk score (that would only re-learn our own rules).

We found one outcome that *can* be observed honestly from public data: **whether a currently active repository stops receiving commits.** The label comes from the repository's own future history, so it is objective and reproducible. Prior work studies a related problem (Coelho et al., ESEM 2018, identifying unmaintained projects), so the task is not novel; our contribution is a transparent replication-style experiment.

Two ML components exist, both marked **experimental** and **excluded from the risk score**:

| Component | Type | Purpose |
|---|---|---|
| Unusual-week detection | Unsupervised (Isolation Forest) | Flag weeks that differ strongly from the repository's own pattern |
| Dormancy estimate | Supervised (logistic regression) | P(no non-bot commit in next 180 days \| active in last 90 days) |

## 2. Dormancy experiment

### Data
- **Source:** commit histories of 76 public repositories listed in `ml/data/repositories.txt`, collected with `git clone --bare --filter=tree:0` (commit objects only; no GitHub API quota). Author e-mails were salted-hashed before writing to disk.
- **Sample:** hand-picked well-known JavaScript/Python/Ruby projects, some known to be deprecated or archived. **This is a convenience sample with selection bias**; results do not generalise to all GitHub repositories (most of which are small, personal and inactive — Kalliamvakou et al., 2014).
- **Units:** repository × cutoff date. Cutoffs every 90 days, starting 365 days after the first commit and ending 180 days before the collection date (17 Sep 2026), so every label is fully observed.
- **Eligibility:** ≥ 1 non-bot commit in the 90 days before the cutoff.
- **Result:** 3,533 samples; 90 positives (2.5%) spread across 42 repositories; cutoffs from 2006 to 2026.

### Label
`label_dormant_180d = 1` if the repository has **zero** non-bot commits in (T, T + 180 days].

### Features (computed only from commits ≤ T; shared code in `backend/app/ml/features.py`)
log commits in last 30/90/180 days; share of the last 26 weeks with commits; days since last commit; smoothed ratio of 30-day to 180-day commit rate; distinct authors in 90 days; top-author share in 180 days.

### Leakage and contamination controls
| Risk | Control |
|---|---|
| Temporal leakage (future data in features) | Feature function ignores commits after T; unit test `test_features_ignore_future_commits_no_temporal_leakage` |
| Label not fully observed | Last cutoff ≤ collection date − 180 days |
| Train/test contamination between correlated samples of one repo | `GroupShuffleSplit` by repository (60 train / 16 test repos); assertion that the sets are disjoint |
| Model selection on test data | 5-fold `GroupKFold` CV on training repositories only; test set evaluated once |
| Training/serving skew | Same feature code used by training script and API |
| Irreproducibility | Fixed seed 42; dataset CSV and metrics JSON are committed; script regenerates both |

### Handling imbalance
`class_weight="balanced"`; evaluation emphasises balanced accuracy, precision, recall, F1, ROC-AUC and PR-AUC rather than accuracy (a model that always says "not dormant" reaches 98.1% test accuracy).

### Baselines
1. Majority-class prior (`DummyClassifier`).
2. One-line rule: dormant if `days_since_last_commit > 60`.

### OUR EXPERIMENTAL FINDING (test set: 16 repositories, 837 samples, 16 positives)

Values copied from `ml/results/metrics.json`. 95% CIs from 1,000 bootstrap resamples **of test repositories** (cluster bootstrap).

| Model | Bal. acc. | Precision | Recall | F1 | ROC-AUC [95% CI] | PR-AUC [95% CI] |
|---|---|---|---|---|---|---|
| Majority prior | 0.500 | 0.000 | 0.000 | 0.000 | 0.500 | 0.019 |
| Rule: >60 days since commit | 0.740 | 0.333 | 0.500 | **0.400** | 0.908 [0.836, 0.967] | 0.239 [0.142, 0.445] |
| Logistic regression | **0.865** | 0.160 | **0.812** | 0.268 | **0.950** [0.907, 0.981] | **0.379** [0.189, 0.639] |
| Random forest | 0.677 | 0.261 | 0.375 | 0.308 | 0.946 [0.904, 0.975] | 0.276 [0.112, 0.538] |

Confusion matrix, logistic regression @ 0.5: TN 753, FP 68, FN 3, TP 13. CV PR-AUC on training repos: LR 0.402 ± 0.074, RF 0.436 ± 0.098.

### Interpretation (honest)
- Logistic regression **ranks** repositories better than the rule on point estimates (PR-AUC 0.38 vs 0.24), but the confidence intervals overlap heavily. **We cannot claim it is better than the simple rule.**
- At the default 0.5 threshold it finds most dormant cases (recall 0.81) but most alarms are false (precision 0.16). The rule has the best F1.
- With only 16 positive test samples, all estimates are unstable.
- Random forest's cross-validation PR-AUC was slightly higher, but its test PR-AUC was lower; neither difference is reliable.
- **Why logistic regression is served anyway:** its explanation is exact (coefficient × standardised value in log-odds), it is simple to defend, and performance differences were not significant. The UI labels it experimental and never mixes it into the risk score.
- Coefficients of correlated features (e.g. 30/90/180-day commit counts) are unstable and must not be read causally (cf. Jiarpakdee et al., TSE 2019).

### Serving caveats
The API computes the same features from GitHub API commits (default branch only), whereas training used all branches from Git. When the collection is truncated by page caps, output status is `unreliable`.

## 3. Why SHAP is not used
SHAP explains arbitrary models by approximating Shapley values. For a linear model on standardised inputs, the exact contribution is already `coef_j × z_j` (this equals linear SHAP with a mean baseline under feature independence). Adding the `shap` dependency would add install weight and complexity without additional fidelity. If a tree model were ever served, SHAP's TreeExplainer would be the appropriate choice.

## 4. Unusual-week detection
Isolation Forest (200 trees, seed 42) over 52 weekly vectors (commits, issues opened/closed, PRs opened/merged). A week is reported only if the forest flags it **and** at least one feature is ≥ 3 robust z-scores (median/MAD) from the median. Needs ≥ 12 active weeks. Output lists reasons such as "commits 120 (typical 10)". There is no labelled ground truth, so no accuracy is claimed; unit tests only check that an injected spike is found and results are reproducible.

## 5. Reproduce
```bash
python ml/collect_histories.py --workers 4   # ~1 minute, ~200 MB of partial clones
python ml/train_dormancy.py                   # writes ml/results/metrics.json and the model artifact
```
Numbers change if run on a different date (new cutoffs become eligible) — record the `trained_at` value.
