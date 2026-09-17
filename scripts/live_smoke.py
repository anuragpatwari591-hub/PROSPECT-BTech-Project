"""End-to-end smoke test against a RUNNING PROSPECT backend and the REAL GitHub API.

Usage:  python scripts/live_smoke.py --api http://localhost:8000 --repo https://github.com/pallets/click
Exits non-zero if any step fails. Writes the PDF report next to this script's working directory.
"""

import argparse
import json
import sys
import time
import urllib.error
import urllib.request


def call(method: str, url: str, body: dict | None = None) -> tuple[int, bytes]:
    data = json.dumps(body).encode() if body is not None else None
    request = urllib.request.Request(url, data=data, method=method, headers={"Content-Type": "application/json"})  # noqa: S310
    try:
        with urllib.request.urlopen(request, timeout=120) as response:  # noqa: S310
            return response.status, response.read()
    except urllib.error.HTTPError as err:
        return err.code, err.read()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--api", default="http://localhost:8000")
    parser.add_argument("--repo", action="append", required=True)
    args = parser.parse_args()
    ok = True
    for repo in args.repo:
        print(f"\n=== {repo}")
        status, body = call("POST", f"{args.api}/api/projects", {"repository_url": repo})
        payload = json.loads(body)
        if status == 409:
            project_id = payload["error"]["project_id"]
        elif status == 201:
            project_id = payload["id"]
        else:
            print("create failed:", status, payload)
            ok = False
            continue
        status, body = call("POST", f"{args.api}/api/projects/{project_id}/analyze?force=true")
        run = json.loads(body)
        print("analyze:", status, run.get("status"))
        for _ in range(120):
            status, body = call("GET", f"{args.api}/api/projects/{project_id}/runs/{run['id']}")
            run = json.loads(body)
            if run["status"] in ("COMPLETED", "FAILED"):
                break
            time.sleep(2)
        print("run:", json.dumps({k: run[k] for k in ("status", "error_code", "error_message", "api_calls",
                                                       "data_truncated", "collection_notes")}, indent=1))
        if run["status"] != "COMPLETED":
            ok = False
            continue
        risk = json.loads(call("GET", f"{args.api}/api/projects/{project_id}/risk")[1])
        print(f"risk_score={risk['risk_score']} level={risk['risk_level']} health={risk['health_score']} "
              f"coverage={risk['coverage']}")
        for d in risk["dimensions"]:
            print(f"  {d['label']:<30} score={d['score']} contribution={d['contribution']} {d['status']}")
        for f in risk["top_factors"]:
            print(f"  + {f['contribution']:>5} {f['signal_key']}: {f['explanation']}")
        metrics = json.loads(call("GET", f"{args.api}/api/projects/{project_id}/metrics")[1])["metrics"]
        print("  metrics:", {m["key"]: m["value"] for m in metrics})
        for r in json.loads(call("GET", f"{args.api}/api/projects/{project_id}/recommendations")[1]):
            print(f"  REC [{r['priority']}] {r['title']} <- {r['signal_key']}")
        print("  ml:", json.dumps(risk["ml"])[:700])
        sim_status, sim = call("POST", f"{args.api}/api/projects/{project_id}/simulate",
                               {"overrides": {"median_pr_turnaround_days": 1, "top_contributor_share": 0.3}})
        print("  simulate:", sim_status, sim[:300])
        status, pdf = call("GET", f"{args.api}/api/projects/{project_id}/report")
        name = f"live-report-{project_id}.pdf"
        open(name, "wb").write(pdf)
        print("  report:", status, len(pdf), "bytes ->", name, "valid" if pdf.startswith(b"%PDF") else "INVALID")
        ok = ok and status == 200 and sim_status == 200
    print("\nLIVE SMOKE", "PASSED" if ok else "FAILED")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
