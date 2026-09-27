# 02 — Literature Review and Research Gap

Statements are labelled:
**FACT** (reported by the cited source) · **INTERPRETATION** (our reading) · **OUR IMPLEMENTATION** (what PROSPECT does) · **OUR EXPERIMENTAL FINDING** (what we measured).

All references below were checked against publisher pages, arXiv or DBLP on 17 Sep 2026. Team members should still open each paper before quoting it in the report.

## 1. Mining Software Repositories (MSR)

- **FACT** — Kalliamvakou et al. (MSR 2014) studied GitHub as a research data source and documented "perils": most repositories are personal and inactive, and in their extended study a large share of pull requests that were in fact merged do not appear as merged in GitHub data.
- **INTERPRETATION** — GitHub metrics are proxies with systematic blind spots; a tool must state its limitations and avoid cross-project comparisons that ignore project type.
- **OUR IMPLEMENTATION** — Every metric has a "limitations" field (docs/05_METRICS.md); the UI and report carry a disclaimer; merged-PR metrics are documented as affected by squash/rebase workflows.

## 2. Pull-request analytics

- **FACT** — Gousios, Pinzger and van Deursen (ICSE 2014, pp. 345–355) conducted an exploratory study of the pull-based development model on GitHub, including the factors that influence merge decisions and merge time.
- **OUR IMPLEMENTATION** — Median PR turnaround, turnaround trend, stale open PR ratio and PR size are measured signals.
- **INTERPRETATION** — Our thresholds (e.g. risk 50 at a 4-day median turnaround) are *team heuristics*, not values derived from that study.

## 3. Contributor dependency / truck factor

- **FACT** — Avelino, Passos, Hora and Valente (ICPC 2016) proposed an automated truck-factor estimation approach based on code authorship, applied it to 133 popular GitHub systems, and reported that 65% had a truck factor of at most 2; a developer survey provided partial support for the estimates.
- **FACT** — Ferreira, Valente and Ferreira (ICPC 2017) compared three truck-factor algorithms.
- **OUR IMPLEMENTATION** — A deliberately simpler *commit-share bus factor*: the minimum number of authors producing ≥ 50% of recent commits. **It is not the Avelino et al. algorithm** (which uses file-level degree-of-authorship) and is labelled "estimate" everywhere.

## 4. Project failure and maintenance activity

- **FACT** — Coelho and Valente (ESEC/FSE 2017, pp. 186–196) surveyed maintainers of 104 popular deprecated GitHub projects and identified nine reasons for failure; they also report an association between contributing guidelines / continuous integration and project success.
- **FACT** — Coelho, Valente, Silva and Shihab (ESEM 2018) addressed *identifying unmaintained projects in GitHub* using machine learning on repository activity features.
- **INTERPRETATION** — Predicting maintenance decline from activity data is an established research direction. **PROSPECT's dormancy experiment is not novel as a task**; its value is as a transparent, reproducible student replication with strict leakage controls and honest baselines.

## 5. Explainable AI in software engineering

- **FACT** — Tantithamthavorn, Jiarpakdee and Grundy argue that AI/ML models in software engineering are often impractical, not explainable and not actionable, using defect prediction case studies (arXiv 2012.01614; ASE 2021 tutorial with Jiarpakdee).
- **FACT** — Jiarpakdee, Tantithamthavorn and Hassan (IEEE TSE, 2019) studied how correlated metrics affect the interpretation of defect models.
- **FACT** — Lundberg and Lee (NeurIPS 2017) introduced SHAP.
- **OUR IMPLEMENTATION** — The primary risk model is additive, so explanations are exact. The served ML model is logistic regression with exact log-odds contributions; the UI warns that correlated features make individual coefficients unreliable as causes (consistent with Jiarpakdee et al.).

## 6. Software risk management

- **FACT** — Boehm (IEEE Software, 1991) framed software risk management as risk identification, analysis, prioritisation and control.
- **INTERPRETATION** — PROSPECT supports the *identification* and *prioritisation* steps with evidence; *control* remains a human decision (recommendations are suggestions).

## 7. Anomaly detection

- **FACT** — Liu, Ting and Zhou (ICDM 2008) proposed Isolation Forest, which isolates anomalies by random partitioning.
- **OUR IMPLEMENTATION** — Used only as an informational "unusual weeks" view, filtered by a robust z-score rule so every flag has a readable reason.

## 8. Industry metric frameworks

- **FACT** — The CHAOSS project (Linux Foundation) publishes community-health metric definitions for open source.
- **OUR IMPLEMENTATION** — Several PROSPECT metrics (activity, issue response, contributor concentration) are similar in spirit; we define our own formulas precisely and do not claim CHAOSS compliance.

## Research gap (conservative)

**INTERPRETATION** — Individual pieces exist: repository mining tools, PR studies, truck-factor algorithms, maintenance prediction models, and XAI for defect prediction. What we did not find in the sources we reviewed is a *student-reproducible, open, integrated decision-support tool* that combines (a) documented GitHub metrics, (b) an additive risk score with exact per-signal attribution, (c) factor-linked recommendations, (d) a labelled What-If simulator over the same model, and (e) an ML component evaluated with repository-grouped splits against trivial baselines. Our literature search was limited in depth; this gap statement is about integration and transparency, **not** about new algorithms.

## References

1. E. Kalliamvakou, G. Gousios, K. Blincoe, L. Singer, D. M. German, D. Damian. "The promises and perils of mining GitHub." *MSR 2014*, pp. 92–101. Extended: *Empirical Software Engineering* 21(5), 2016, doi:10.1007/s10664-015-9393-5.
2. G. Gousios, M. Pinzger, A. van Deursen. "An exploratory study of the pull-based software development model." *ICSE 2014*, pp. 345–355.
3. G. Avelino, L. Passos, A. Hora, M. T. Valente. "A novel approach for estimating truck factors." *ICPC 2016*, pp. 1–10. arXiv:1604.06766.
4. M. Ferreira, M. T. Valente, K. Ferreira. "A comparison of three algorithms for computing truck factors." *ICPC 2017*, pp. 207–217.
5. J. Coelho, M. T. Valente. "Why modern open source projects fail." *ESEC/FSE 2017*, pp. 186–196, doi:10.1145/3106237.3106246.
6. J. Coelho, M. T. Valente, L. L. Silva, E. Shihab. "Identifying unmaintained projects in GitHub." *ESEM 2018*. arXiv:1809.04041.
7. C. Tantithamthavorn, J. Jiarpakdee, J. Grundy. "Explainable AI for Software Engineering." arXiv:2012.01614, 2020.
8. J. Jiarpakdee, C. Tantithamthavorn, A. E. Hassan. "The impact of correlated metrics on the interpretation of defect models." *IEEE TSE*, 2019.
9. S. M. Lundberg, S.-I. Lee. "A unified approach to interpreting model predictions." *NeurIPS 2017*.
10. F. T. Liu, K. M. Ting, Z.-H. Zhou. "Isolation Forest." *IEEE ICDM 2008*.
11. B. W. Boehm. "Software risk management: principles and practices." *IEEE Software* 8(1), 1991.
12. CHAOSS Project, Linux Foundation — community health metrics, https://chaoss.community.
