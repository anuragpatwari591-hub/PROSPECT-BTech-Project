# 01 — Problem Statement, Objectives and Scope

## Problem

Software projects rarely fail suddenly. Warning signs usually accumulate in the development record first: work slows down, the issue backlog grows faster than it is closed, pull requests wait longer for review, and knowledge concentrates in one or two people. On GitHub this record is public and machine-readable, yet teams, students, and people choosing open-source dependencies seldom examine it systematically. They look at stars or the date of the last commit, which say little about *why* a project may be at risk.

Existing tools either show raw charts without interpretation (GitHub Insights) or produce a single score whose reasoning is hidden. A score that cannot be explained cannot be acted on.

**Problem statement:** *There is a need for a system that collects software-development activity from a GitHub repository, converts it into documented engineering metrics, and presents a transparent risk assessment that explains which signals contribute to the risk, recommends actions linked to those signals, lets users explore hypothetical improvements, and keeps a history of assessments over time.*

## Objectives

1. Collect commits, issues, pull requests, contributors and releases from the GitHub REST API reliably (pagination, rate limits, errors).
2. Define and implement software-engineering metrics, each with definition, formula, source, unit, interpretation and limitations.
3. Build a configurable, rule-based risk engine whose score decomposes exactly into per-signal contributions.
4. Generate recommendations traceable to the risk factor that triggered them.
5. Provide a What-If simulator clearly labelled as a simulation/estimate.
6. Store every analysis run and show historical trends without inventing missing data.
7. Investigate, honestly, whether machine learning adds value, and report measured results including negative ones.
8. Deliver a tested, containerised, documented web application.

## Scope

**In scope:** public GitHub repositories; default-branch commits; issues; pull requests; releases; single-team deployment; PDF reports.

**Out of scope (MVP):** private repositories, GitLab/Bitbucket, source-code quality analysis (complexity, defects), user accounts and roles, real-time webhooks, cross-project benchmarking, claims about business outcomes.

## Stakeholders

| Stakeholder | Need |
|---|---|
| Project lead / maintainer | Spot growing risk early and know what to act on |
| Student team / course instructor | Monitor team-project health objectively |
| Developer choosing a dependency | Judge whether a library is actively maintained |
| Researcher | Transparent, reproducible repository metrics |
