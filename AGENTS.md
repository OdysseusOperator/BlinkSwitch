# AGENTS

This document is the operations manual for agentic assistants working inside BlinkSwitch (aka ScreenAssign/Screeny). Follow it exactly; deviations usually break the Windows-focused workflow.

## Repository Orientation
- `backend/` hosts the Flask API, background service, monitor heuristics, and Chrome tab bridge.
- `frontend/` houses the Raylib-powered window switcher plus command palette UI assets.
- `window_stuff/`, `tab_enumerators/`, and `extensions/` contain Win32 integration helpers and browser hooks.
- Root-level scripts `start_assigner.bat` and `start_switcher.bat` orchestrate both halves; they assume Windows paths.
- Logs are rotated into `logs/` (backend) and `frontend/logs/`; configs such as `monitors_config.json` live at repo root.

## Environment Reality
- BlinkSwitch is Windows-only; pywin32, win32gui, and BAT files are required, and Linux/Mac shells are unsupported.
- Use 64-bit Python 3.11+; repo `.python-version` pins interpreter expectations.
- Always operate inside a venv: `.venv` for the backend, `frontend/.venv` for the window switcher.
- Microsoft Visual C++ Build Tools must be available so pip can compile Raylib bindings if binaries are missing.
- Run terminals as Administrator when interacting with Win32 APIs that elevate (window focus, keyboard hooks, registry writes).

## Virtual Environment Workflow
- Backend setup: `python -m venv .venv && .venv\Scripts\activate && python -m pip install -r requirements.txt`.
- Frontend setup: `python -m venv frontend\.venv && frontend\.venv\Scripts\activate && python -m pip install -r frontend\requirements.txt`.
- Prefer running the BAT scripts; they self-heal the envs and install dependencies quietly.
- Keep virtual environments checked out of git (`.gitignore` already excludes them); never commit site-packages artifacts.
- When Raylib or pywin32 wheels break, nuke the affected `.venv` folder and rerun the matching start script to rebuild from scratch.

## Build & Run Commands
- Full backend: `start_assigner.bat` (creates `.venv`, installs `requirements.txt`, runs `python -m backend.backend`).
- Backend without BAT: `.venv\Scripts\activate && python -m backend.backend`.
- Frontend window switcher: `start_switcher.bat` (manages `frontend/.venv`, installs `frontend/requirements.txt`, runs `python -m frontend.frontend-switcher`).
- Frontend without BAT: `frontend\.venv\Scripts\activate && python -m frontend.frontend-switcher`.
- Combined developer loop: run `start_assigner.bat`, wait for port `127.0.0.1:5555`, then `start_switcher.bat`; both consoles must stay open.

## Lint & Static Analysis
- Ruff is the de-facto linter (cache lives in `.ruff_cache` even though no pyproject is present); run `ruff check .` from the repo root.
- Format fixes: `ruff check . --fix` handles import sorting and simple rewrites; review the diff before committing.
- For built-in formatter parity, follow Black-like 120 char lines and double quotes by default unless Windows escape sequences force single quotes.
- Type checking is light-touch; optional mypy passes can be run via `python -m mypy backend frontend window_stuff` if the tool is installed.
- Keep logging noise lint-free by running `ruff check backend/backend.py frontend/frontend-switcher.py` before opening a PR.

## Tests & Diagnostics
- There is no formal pytest suite yet; smoke testing relies on targeted scripts plus manual verification against real windows.
- System smoke test: `python test_placement.py` (ensures Win32 placement heuristics behave on the active foreground window).
- Config verification: `python -m window_stuff.monitor_fingerprint` (confirm monitor fingerprints and IDs) once available.
- API sanity: with backend venv active, `python - <<'PY'` mini-scripts can `requests.get("http://127.0.0.1:5555/screenassign/health")` to confirm readiness.
- When you add pytest modules, follow this pattern for a single test: `.venv\Scripts\activate && python -m pytest backend/tests/test_service.py -k test_apply_rules`.

## Running One-Off Commands
- Enumerate connected monitors: `.venv\Scripts\activate && python -m window_stuff.config_manager --list` (if CLI helpers exist).
- Refresh assignment cache: `frontend\.venv\Scripts\activate && python - <<'PY'` imports `frontend.assignment` to rewrite `frontend/assignment.json`.
- Browser tab bridge debug: `.venv\Scripts\activate && python -m tab_enumerators.chrome_listener` while Chrome extension runs.
- Layout diffing: `python compare_styles.py "logs/layout_a.json" "logs/layout_b.json"` to inspect UI tweaks.
- Stress test backend loop: `.venv\Scripts\activate && python -m backend.service --dry-run --iterations 100` (service module includes CLI helpers).

## Import & Module Style
- Standard library imports first, then third-party, then internal modules; group each block with a blank line.
- Avoid wildcard imports; import modules (`import win32gui`) instead of dumping names into the namespace.
- Use explicit relative imports within packages (e.g., `from .service import ScreenAssignService`) to keep tooling aware of package roots.
- When referencing top-level helpers (e.g., `window_stuff`), add the project root to `sys.path` only once per file and comment why.
- Keep HTTP constants, paths, and Win32 magic numbers defined near the top of the module for easier tuning.

## Naming & Structure
- Modules and packages stay snake_case; classes use PascalCase; functions, local vars, and filenames remain snake_case.
- Configuration keys mirror their API payload names exactly (e.g., `layout_name`, `center_mouse_on_switch`).
- Thread/worker names should be explicit (`window_refresh_thread`, `chrome_tab_manager`) so log output is searchable.
- JSON files saved to disk must be lowerCamelCase to match REST payloads consumed by extensions.
- For constants that mirror Win32 flags, keep the Windows prefix (e.g., `SW_RESTORE`, `GWL_STYLE`) to minimize confusion when cross-referencing MSDN docs.

## Typing Guidelines
- Prefer concrete typing (`dict[str, Any]`, `list[Monitor]`) over `typing.Any` when the structure is known.
- Use `Optional[T]` or `T | None` to signal nullable data; guard with early returns.
- Annotate function returns even when they are `None`; this helps AI agents maintain clarity.
- Dataclasses are encouraged for structured payloads, but `TypedDict` is acceptable when serialization/deserialization is required.
- When bridging to Win32 APIs lacking stubs, wrap arguments in helper functions and add inline comments describing the expected HWND or style mask types.

## Error Handling & Logging
- All external actions (Win32 calls, file IO, HTTP requests) must sit inside try/except blocks with clear logging via the module-level logger.
- Never swallow exceptions silently; log at least a warning and include contextual identifiers (monitor id, hwnd, layout name).
- For recoverable failures, return JSON errors with HTTP codes (400 for bad input, 409 for layout conflicts, 503 for missing managers).
- When raising errors server-side, prefer project-specific exceptions (`LayoutError`) so the frontend can branch on message text.
- Keep log lines single-line and ASCII; Windows Event Viewer does not like ANSI art.

## Concurrency & Threads
- Background polling (window enumeration, Chrome tab syncing) uses Python threads; always protect shared lists with `threading.Lock`.
- Long-running loops need `Event` cancellation hooks so Ctrl+C and service restarts exit promptly.
- When sharing Win32 handles between threads, convert them to ints immediately and document the ownership expectations.
- Use the `CHROME_COMMAND_TTL` constant to age out stale tab commands; do not invent new magic numbers without a module-level constant.
- Thread naming: pass `name="WindowCacheRefresher"` into `threading.Thread` for better debug output.

## Backend-Specific Practices
- Flask blueprint lives in `backend/backend.py`; expose new routes through `screenassign_api` and reuse `_require_service()` for service access.
- Keep API responses JSON-serializable; convert datetimes to ISO strings before returning them.
- Monitor detection logic should update `monitors_config.json` atomically (write to temp file, then rename) to avoid corruption.
- Caching endpoints (`/windows-and-tabs`) must stay non-blocking and return stale-but-safe data rather than timing out the frontend.
- Remember to update documentation in `documentation/` whenever you adjust monitor fingerprint algorithms or config schemas.

## Frontend-Specific Practices
- Raylib draw calls originate from the main thread; avoid making blocking HTTP requests mid-frame—prefetch via background threads and share data via queues.
- Colors live in `frontend/colors.py`; keep palettes centralized and avoid hardcoding RGBA tuples elsewhere.
- Commands registered through `frontend/commands.py` should describe their purpose in the registry so the palette can auto-document itself.
- HTTP calls use a shared `requests.Session`; reuse it and keep per-call timeouts under one second to maintain responsiveness.
- Persist user actions (layout assignments, settings) through helpers in `frontend/assignment.py` and `frontend/settings_view`; never write JSON manually in UI code.

## Configuration & Data Files
- `monitors_config.json` is the canonical monitor registry; treat it like state, not source—never commit user-local copies.
- `frontend/assignment.json` stores local UI preferences; maintain compatibility by preserving unknown keys when rewriting.
- Logs in `logs/` and `frontend/logs/` rotate daily; path math uses `datetime.now().strftime('%Y%m%d')`—keep that convention for new logs.
- When adding new config toggles, thread them through backend settings endpoints and expose them via the frontend command center.
- Sample configs or fixtures belong under `documentation/` or a future `fixtures/` folder, never mixed into runtime state directories.

## Monitoring & Log Review
- Backend logs live in `logs/screenassign_*.log`; rotate issues by deleting only when the service is stopped.
- Frontend logs live in `frontend/logs/window_switcher_*.log`; inspect them when diagnosing UI hangs or HTTP latency.
- Use `tail -f` alternatives on Windows (`Get-Content -Wait`) if you need streaming output, but prefer structured repro steps.
- When adding new loggers, inherit from the module-level logger and keep `INFO` noise low; rely on `DEBUG` for chatty traces.
- Sanitise personally identifiable info (window titles can leak data)—mask anything sensitive before logging or sharing traces.
- When tests or scripts fail, capture both console output and snippet of the relevant log file in the issue description.

## Documentation Expectations
- When behavior changes, update this `AGENTS.md` plus any relevant `documentation/*.md` explainer before opening a PR.
- Architecture decisions belong in `documentation/IMPLEMENTATION_SUMMARY.md`; include motivation, tradeoffs, and rollback plan.
- CLI additions require usage notes in `documentation/COMMANDS_USAGE.md` so operators have a copy/paste ready sequence.
- UI/UX changes should include screenshots or GIFs stored externally and linked from `layout-redesign.md` or a new doc page.
- Keep README installation steps accurate for new dependencies; spell out Win32 prerequisites explicitly.
- If you touch monitor fingerprint logic, echo the delta in `documentation/QUICK_START.txt` so downstream teams can resync.

## Git & Review Checklist
- Do not commit `.venv` folders, `.ruff_cache`, compiled artifacts, or user logs; verify with `git status` after every change.
- Before requesting review, run `ruff check .`, `python -m backend.backend --help` (verifies module imports), and smoke-test the switcher.
- Ensure BAT scripts still run end-to-end after modifying dependency installation or activation steps.
- Update documentation whenever behavior changes; `AGENTS.md`, `README.md`, and `documentation/` must stay synchronized.
- Summarize Windows-specific caveats in PR descriptions so reviewers understand why cross-platform fixes might not apply.

## Missing Cursor/Copilot Rules
- There are no `.cursor/rules/`, `.cursorrules`, or `.github/copilot-instructions.md` files in this repo; this document is the authoritative rule-set.
- If future automation introduces those files, sync their expectations back into this guide immediately.
- Treat this AGENTS file as source truth for all coding agents and keep its instructions in lockstep with real tooling changes.
- Any deviation must be justified inside the PR description and captured here afterward.
- When in doubt, prefer the practices documented above over personal preference.

Stay disciplined, keep the Win32 focus sharp, and BlinkSwitch will remain stable for every agent that follows these steps.
