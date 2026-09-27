import os
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

DATABASE_PATH = os.getenv("DATABASE_PATH", os.path.join(BASE_DIR, "prospect.db"))
DATABASE_URL = f"sqlite:///{DATABASE_PATH}"

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "").strip() or None
GITHUB_API_BASE = "https://api.github.com"

# CORS: default allows the Vite dev server on any local port.
CORS_ORIGINS = os.getenv(
    "CORS_ORIGINS",
    "http://localhost:5173,http://127.0.0.1:5173,http://localhost:3000",
).split(",")

# How many pages (of 100 items) to pull for each collection endpoint.
# Kept small and fixed so the tool stays fast and rate-limit friendly while
# still being a statistically meaningful sample for the risk engine.
MAX_PAGES_COMMITS = 3
MAX_PAGES_ISSUES = 3
MAX_PAGES_PULLS = 3
MAX_PAGES_CONTRIBUTORS = 2
MAX_PAGES_RELEASES = 2

STALE_ISSUE_DAYS = 90
STALE_PR_DAYS = 45
