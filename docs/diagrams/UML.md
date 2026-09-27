# UML Diagrams

## Use case diagram

```mermaid
flowchart LR
  A([Analyst])
  GH([GitHub API])
  subgraph PROSPECT
    UC1(Register repository)
    UC2(Run analysis)
    UC3(View risk score and explanation)
    UC4(View metrics and activity charts)
    UC5(View contributor dependency)
    UC6(Run What-If simulation)
    UC7(View history)
    UC8(Download PDF report)
    UC9(Delete project)
    UC10(View experimental ML output)
  end
  A --- UC1 & UC2 & UC3 & UC4 & UC5 & UC6 & UC7 & UC8 & UC9 & UC10
  UC1 --- GH
  UC2 --- GH
  UC2 -. include .-> UC3
```

## Class diagram (core domain and engines)

```mermaid
classDiagram
  class Project { +id +owner +repo +url +stars +is_archived +last_collected_at }
  class AnalysisRun { +id +status +started_at +finished_at +used_cache +data_truncated +ml_output }
  class RepositoryMetric { +key +value +unit +note }
  class RiskAssessment { +risk_score +health_score +risk_level +coverage +config_snapshot }
  class RiskFactor { +signal_key +metric_value +score +contribution +severity +explanation }
  class Recommendation { +priority +title +detail }
  class Scenario { +overrides +baseline_score +simulated_score }
  Project "1" --> "*" AnalysisRun
  AnalysisRun "1" --> "*" RepositoryMetric
  AnalysisRun "1" --> "0..1" RiskAssessment
  RiskAssessment "1" --> "*" RiskFactor
  RiskAssessment "1" --> "*" Recommendation
  RiskFactor "0..1" <-- Recommendation : triggered by
  Project "1" --> "*" Scenario

  class GitHubClient { +calls +rate_remaining +paginate() +get_repository() +list_commits() +list_issues() +list_pulls() }
  class Collector { +collect(db, project, client, settings) }
  class MetricEngine { +compute_metrics(RepoData) +weekly_activity(RepoData) }
  class RiskEngine { +compute_risk(metrics, config) RiskResult }
  class RiskResult { +risk_score +risk_level +dimensions +signals +top_factors() }
  class RecommendationEngine { +generate_recommendations(RiskResult) }
  class Simulator { +simulate(metrics, overrides, config) SimulationResult }
  Collector ..> GitHubClient
  RiskEngine ..> RiskResult
  RecommendationEngine ..> RiskResult
  Simulator ..> RiskEngine
```

## State chart — AnalysisRun

```mermaid
stateDiagram-v2
  [*] --> PENDING : POST /analyze
  PENDING --> RUNNING : background task starts
  RUNNING --> COMPLETED : metrics, risk, ML stored
  RUNNING --> FAILED : GitHub error / internal error (partial data rolled back)
  PENDING --> FAILED : stale > 15 min when a new run is requested
  RUNNING --> FAILED : stale > 15 min when a new run is requested
  COMPLETED --> [*]
  FAILED --> [*]
```

## Sequence diagram — run an analysis

```mermaid
sequenceDiagram
  actor U as Analyst
  participant FE as React UI
  participant API as FastAPI
  participant BG as Background task
  participant GH as GitHub API
  participant DB as PostgreSQL
  U->>FE: Click "Run analysis"
  FE->>API: POST /api/projects/1/analyze
  API->>DB: insert AnalysisRun(PENDING), audit log
  API-->>FE: 202 {run id}
  API->>BG: execute_run(run id)
  BG->>DB: status RUNNING
  alt cache fresh and not forced
    BG->>DB: reuse stored raw data
  else
    loop each endpoint, each page
      BG->>GH: GET /repos/o/r/... (Bearer token)
      GH-->>BG: JSON + Link header
    end
    BG->>DB: upsert commits, issues, PRs, releases, contributors
  end
  BG->>BG: compute metrics → risk → recommendations → ML
  BG->>DB: store metrics, assessment, factors, recommendations, status COMPLETED
  loop every 2 s until finished
    FE->>API: GET /runs/{id}
    API-->>FE: status
  end
  FE->>API: GET /risk, /metrics, /recommendations
  API-->>FE: explained results
  FE-->>U: Dashboard
```

## Activity diagram — What-If simulation

```mermaid
flowchart TD
  S([Start]) --> A[Open What-if tab]
  A --> B[Load simulatable metrics and ranges]
  B --> C[Move sliders]
  C --> D{At least one metric changed?}
  D -- no --> C
  D -- yes --> E[POST /simulate]
  E --> F{Valid metric and range?}
  F -- no --> G[Show 422 message] --> C
  F -- yes --> H[Compute baseline and simulated risk with same engine]
  H --> I[Store scenario]
  I --> J[Show current, simulated, difference, dimension chart<br/>labelled SIMULATION / ESTIMATE]
  J --> K{Try another?}
  K -- yes --> C
  K -- no --> E2([End])
```

## Component diagram

```mermaid
flowchart LR
  subgraph Frontend
    AppShell --> ProjectView
    ProjectView --> ScoreStrip & OverviewTab & FactorsTab & ActivityTab & ContributorsTab & SimulatorTab & HistoryTab & ExperimentalTab
    ProjectView & SimulatorTab --> ApiClient[lib/api.ts]
  end
  ApiClient -- REST/JSON --> Routes
  subgraph Backend
    Routes[api/routes] --> AnalysisService & Simulator & ReportService
    AnalysisService --> Collector --> GitHubClient
    AnalysisService --> MetricEngine --> RiskEngine --> RecommendationEngine
    AnalysisService --> MLModule
    Routes & AnalysisService --> ORM[SQLAlchemy models]
  end
  ORM --> PG[(PostgreSQL)]
  GitHubClient --> GH[(GitHub API)]
```

## Deployment diagram

```mermaid
flowchart TB
  subgraph Client device
    B[Web browser]
  end
  subgraph Docker host / PaaS
    subgraph frontend container
      N[nginx 1.27<br/>static SPA + /api reverse proxy<br/>:8080]
    end
    subgraph backend container
      U[uvicorn + FastAPI<br/>Python 3.12, non-root<br/>:8000]
    end
    subgraph db container
      P[(PostgreSQL 16<br/>volume pgdata)]
    end
  end
  GH[(api.github.com)]
  B -- HTTPS --> N
  N -- HTTP /api --> U
  U -- TCP 5432 private network --> P
  U -- HTTPS + token --> GH
```
