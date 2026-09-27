# Data Flow Diagrams

## DFD Level 0 (context)

```mermaid
flowchart LR
  U([Analyst]) -- repository URL, analysis request, what-if values --> P((0. PROSPECT))
  P -- risk score, factors, recommendations, charts, PDF report --> U
  P -- authenticated API requests --> G([GitHub REST API])
  G -- repository, commits, issues, PRs, contributors, releases --> P
```

## DFD Level 1

```mermaid
flowchart LR
  U([Analyst])
  G([GitHub REST API])
  D1[(D1 Projects)]
  D2[(D2 Raw activity: commits, issues, PRs, releases, contributors)]
  D3[(D3 Runs and metrics)]
  D4[(D4 Assessments, factors, recommendations)]
  D5[(D5 Scenarios)]

  U -- URL --> P1((1.0 Register repository))
  P1 -- validate + lookup --> G
  P1 --> D1
  U -- analyze --> P2((2.0 Collect and normalise))
  D1 --> P2
  G -- paginated JSON --> P2
  P2 --> D2
  D2 --> P3((3.0 Compute metrics))
  P3 --> D3
  D3 --> P4((4.0 Assess risk and recommend))
  P4 --> D4
  D2 --> P5((5.0 Experimental ML))
  P5 --> D3
  U -- changed metric values --> P6((6.0 Simulate))
  D3 --> P6
  P6 --> D5
  P6 -- simulated score --> U
  D1 & D3 & D4 & D5 --> P7((7.0 Present dashboard and report))
  P7 -- dashboard, history, PDF --> U
```
