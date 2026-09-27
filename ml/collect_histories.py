"""Step 1 of the ML experiment: download commit-only histories of the repositories in data/repositories.txt.

Uses `git clone --bare --filter=tree:0`, which fetches commit objects only (no file trees or blobs), so no
GitHub API quota is used. Output: one CSV per repository in data/commits/ with columns
    authored_ts (unix seconds), author_hash (salted SHA-256 prefix of the author e-mail), is_bot
No names or e-mail addresses are written to disk.

Usage:  python ml/collect_histories.py [--workers 4]
"""

import argparse
import csv
import hashlib
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CLONES = ROOT / "data" / "clones"
COMMITS = ROOT / "data" / "commits"
SALT = "prospect-ml"


def repositories() -> list[str]:
    lines = (ROOT / "data" / "repositories.txt").read_text().splitlines()
    return [ln.strip() for ln in lines if ln.strip() and not ln.startswith("#")]


def fetch(slug: str) -> str:
    name = slug.replace("/", "__")
    out_csv = COMMITS / f"{name}.csv"
    if out_csv.exists():
        return f"cached {slug}"
    target = CLONES / f"{name}.git"
    if not target.exists():
        result = subprocess.run(  # noqa: S603 - fixed arguments, slug comes from our own list
            ["git", "clone", "-q", "--bare", "--filter=tree:0", f"https://github.com/{slug}.git", str(target)],
            capture_output=True, text=True, timeout=900, env={"GIT_TERMINAL_PROMPT": "0", "PATH": "/usr/bin:/bin"})
        if result.returncode != 0:
            return f"FAIL {slug}: {result.stderr.strip()[:120]}"
    log = subprocess.run(  # noqa: S603
        ["git", "-C", str(target), "log", "--all", "--no-merges", "--format=%at|%ae|%an"],
        capture_output=True, text=True, timeout=600, errors="replace")
    rows = []
    for line in log.stdout.splitlines():
        ts, email, name_ = (line.split("|", 2) + ["", ""])[:3]
        if not ts.isdigit():
            continue
        bot = "[bot]" in email or "[bot]" in name_ or "dependabot" in email.lower()
        digest = hashlib.sha256(f"{SALT}:{email.lower()}".encode()).hexdigest()[:10]
        rows.append((int(ts), digest, int(bot)))
    with out_csv.open("w", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(["authored_ts", "author_hash", "is_bot"])
        writer.writerows(sorted(rows))
    return f"ok {slug} ({len(rows)} commits)"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workers", type=int, default=4)
    args = parser.parse_args()
    CLONES.mkdir(parents=True, exist_ok=True)
    COMMITS.mkdir(parents=True, exist_ok=True)
    with ThreadPoolExecutor(args.workers) as pool:
        for message in pool.map(fetch, repositories()):
            print(message, flush=True)
    print("DONE", flush=True)


if __name__ == "__main__":
    sys.exit(main())
