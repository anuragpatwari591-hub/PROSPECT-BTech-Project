# 12 — Security, Privacy and Ethics

## Threat model (STRIDE summary)
| Threat | Example | Control |
|---|---|---|
| Spoofing | Someone uses the deployed tool | No accounts in v1.0 → deploy privately or behind platform access control (see Authentication decision) |
| Tampering | SQL injection via URL or ids | Regex URL validation; Pydantic types; SQLAlchemy bound parameters only; tests with injection payloads |
| Repudiation | Who deleted a project? | `audit_logs` records project_created/deleted, analysis_requested, report_generated |
| Information disclosure | GitHub token leak; stack traces | Token only in env var as `SecretStr`; never serialised; health reports only a boolean; generic 500 handler; tests scan every response |
| Denial of service | Repeated analyses exhausting GitHub quota | One active run per project (409); cache TTL; page caps; GitHub rate-limit errors surfaced as 429 |
| Elevation of privilege | Container compromise | Backend runs as non-root UID 10001; DB not published to the host in compose |

## Controls implemented
- **Secrets:** `.env` git-ignored; `.env.example` has no values; Render `sync: false` for secrets; `generateValue` for the hash salt; test asserts `.env` is not tracked and no `ghp_`/`github_pat_` strings exist in source.
- **Token scope:** use a fine-grained personal access token with read-only access to public repositories.
- **Input validation:** repository URL regex (owner ≤ 39 chars, repo charset, no path traversal, max length 300); typed path/query params; simulation whitelist + ranges.
- **HTTP headers:** `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy: no-referrer`, API `Content-Security-Policy: default-src 'none'`, HSTS in production; nginx adds a CSP for the SPA.
- **CORS:** explicit allow-list from `CORS_ORIGINS`; no credentials; only GET/POST/DELETE.
- **Errors:** uniform error envelope; stack traces logged server-side only.
- **Outbound links:** `rel="noreferrer noopener"`.
- **Dependencies:** pinned backend versions; `package-lock.json`; Dependabot; `pip-audit` and `npm audit` clean at release.
- **PDF generation:** all user/GitHub text XML-escaped before ReportLab rendering (prevents markup injection in reports).

## Authentication decision
Authentication is **not implemented in v1.0**. Reasons: all analysed data is public; the tool is used by one team; adding accounts would require password hashing, session/JWT management, CSRF considerations and user management — security surface that does not serve the research goal. **Consequence:** anyone who can reach the deployment can add/delete projects and consume the server's GitHub quota. **Mitigation:** run locally, or restrict access at the platform level. **Migration path:** add a `users` table with Argon2/bcrypt hashes, issue short-lived JWTs in HttpOnly cookies, add an `owner_id` to projects and a dependency that checks ownership.

## Privacy
Stores public GitHub logins only; unlinked commit authors become salted hashes; e-mails and names are never written to the database or to the ML dataset; no IP addresses in audit logs.

## Ethics
- PROSPECT assesses **projects, not people.** Contributor concentration indicates organisational dependency; it must not be used to rate individual developers. This is stated in the contributors view.
- Commit counts ignore review, mentoring, design, documentation and triage work; using them for performance evaluation would be unfair.
- Scores are heuristic; presenting them as verdicts about a project's quality could harm maintainers' reputations. The UI and report carry disclaimers.
- The ML model is labelled experimental with measured, including unfavourable, results.

## SDG alignment and social impact
- **SDG 9 (Industry, Innovation and Infrastructure):** open-source software is digital infrastructure; early warning about maintenance risk supports resilient infrastructure.
- **SDG 4 (Quality Education):** gives student teams objective, explainable feedback on engineering practice.
- **SDG 8 (Decent Work):** highlighting over-reliance on one contributor can prompt fairer workload distribution — when used ethically, as above.
Social impact is a potential, not a measured, outcome.
