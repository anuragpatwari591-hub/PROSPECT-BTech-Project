# PROSPECT — Windows desktop application

The desktop app packages the same React frontend and FastAPI backend as a normal Windows program:
**no Docker, Python or Node.js is needed on the user's PC.**

```
PROSPECT_1.0.0_x64-setup.exe  (NSIS, per-user install to %LOCALAPPDATA%\PROSPECT)
        │
        ▼
app.exe — Tauri 2 shell (Rust, WebView2 window)
        │  starts hidden, from its own folder, with CORS_ORIGINS=http://tauri.localhost,…
        ▼
resources\PROSPECT-Backend\PROSPECT-Backend.exe — PyInstaller-packaged FastAPI backend
        │  runs Alembic migrations, then serves http://127.0.0.1:8000
        ▼
prospect.db — SQLite database next to the backend
```

## What `src-tauri/src/lib.rs` does
1. Resolves `<install>\resources\PROSPECT-Backend\PROSPECT-Backend.exe` (Tauri places bundled resources under
   `resources\`).
2. Starts it hidden (`CREATE_NO_WINDOW`) with its own folder as working directory, so `./prospect.db` and
   `alembic.ini` resolve.
3. Sets `CORS_ORIGINS` so the backend accepts requests from the desktop window (`http://tauri.localhost`).
4. Waits until port 8000 accepts connections and reloads the window once, so the first page load does not show
   "Cannot reach the PROSPECT server" while the backend is still starting.
5. On exit, terminates the backend process tree (`taskkill /T /F`), so port 8000 is freed.
6. Logs start-up steps to `%APPDATA%\com.prospect.desktop\startup.log`.

The frontend is built with `npm run build -- --mode desktop`, which reads `frontend/.env.desktop` and bakes in
`VITE_API_BASE_URL=http://127.0.0.1:8000`. The normal web build is unaffected.

## Building the installer (Windows, Developer PowerShell)
Prerequisites: Rust + MSVC build tools, Node.js, the Tauri CLI (`cargo install tauri-cli`).

1. Package the backend with PyInstaller (one-folder build named `PROSPECT-Backend`, including `alembic.ini`,
   `alembic/` and `app/ml/artifacts/`), and copy the output folder to `desktop/src-tauri/resources/PROSPECT-Backend/`.
2. `cd desktop/src-tauri` → `cargo check` → `cargo tauri build`.
3. The installer is written to `desktop/src-tauri/target/release/bundle/nsis/PROSPECT_1.0.0_x64-setup.exe`.

## Files kept in the team's local build workspace (not in this repository)
The following files exist in the local `prospect-windows-build` workspace that produced the working installer,
but were not available when this repository was updated, so they are **not** included here rather than
guessed: `src-tauri/Cargo.toml`, `src-tauri/build.rs`, `src-tauri/src/main.rs`, `src-tauri/capabilities/`,
`src-tauri/icons/`, the backend launcher `run_server.py` and the PyInstaller spec. Add them from that workspace
to make this folder buildable on its own. Never commit `target/`, the packaged backend binaries or any `.env`.

## GitHub rate limit in the desktop app
Without a token GitHub allows 60 requests per hour per internet connection (about 2–3 analyses). To raise it to
5,000, create a fine-grained token with read-only access to public repositories and save it in
`%LOCALAPPDATA%\PROSPECT\resources\PROSPECT-Backend\.env` as `GITHUB_TOKEN=...`, then restart the app.
Never commit or share the token.
