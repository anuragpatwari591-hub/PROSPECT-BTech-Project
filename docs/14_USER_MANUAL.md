# 14 — User Manual

1. **Add a repository.** Paste `https://github.com/owner/repo` (or `owner/repo`) into *Add a GitHub repository* and select **Add repository**. PROSPECT checks that the repository exists and is public.
2. **Run the analysis.** Select **Run first analysis**. A message shows progress; most repositories finish within a minute. If GitHub's rate limit is reached, the message tells you when to retry.
3. **Read the headline.** The *Risk score* (0–100, higher = riskier), *risk level*, *health score* (100 − risk) and *data coverage*. The coloured strip shows how many points each dimension adds.
4. **Overview tab.** Six key metrics (hover a metric name for its definition and formula), the main factors explaining the score, and recommended actions. Each recommendation names the factor that triggered it.
5. **Risk factors tab.** Every signal with its metric value, 0–100 signal score, points contributed and a plain explanation of the threshold used.
6. **Activity tab.** Weekly commits, issues and pull requests for the last 52 weeks, and unusual weeks (experimental).
7. **Contributors tab.** How concentrated recent commits are. Use it to find knowledge-sharing needs — not to judge people.
8. **What-if tab.** Move sliders to hypothetical values and select **Simulate**. Compare current and simulated scores. Results are estimates of the rule-based model, not predictions.
9. **History tab.** Every stored analysis. 7/30/90-day changes appear only when a real analysis exists from that long ago. Re-analyse periodically to build a trend.
10. **Experimental ML tab.** Dormancy estimate with the features that pushed it up or down, and the model's measured test performance.
11. **Download PDF report.** A shareable report with methodology and limitations.
12. **Re-analyse / Delete.** *Re-analyse* fetches fresh data. *Delete* removes the project and all its analyses.

**Reading scores responsibly:** compare a project with its own past; large popular projects naturally have more issues; a project with no GitHub Releases is not penalised for release risk.
