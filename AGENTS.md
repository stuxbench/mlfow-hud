# Repository Guidelines

## Project Structure & Module Organization
Core orchestration lives in `src/controller/`, with `server.py` exposing the MCP server and `cves/` containing scenario-specific helpers. JSON task definitions (`tasks.json`, `single_task.json`) describe evaluation setups, while runnable harnesses (`test_full_info.py`, `test_one_day.py`, `test_zero_day.py`, `run_pentest_task.py`) sit at the repo root. Vulnerability fixtures and reference exploits stay in `minio-cve-2020-11012/`. Keep environment docs (`README.md`, this guide) synchronized with any structural changes.

## Build, Test & Development Commands
Run `hud dev --build` from the repo root to rebuild the HUD container. Use `uv sync` followed by `uv venv` and `source .venv/bin/activate` to prepare the Python toolchain, then copy configuration with `cp .env.example .env`. Execute `python test_full_info.py` (or the `*_one_day.py` / `*_zero_day.py` variants) to drive individual evaluation suites, and `python run_pentest_task.py` for the MinIO auth bypass scenario. Re-run `hud dev . -e --no-cache --build` if you need to flush cached layers.

## Coding Style & Naming Conventions
Target Python 3.11 features and follow PEP 8 with four-space indentation. Favor descriptive module-level names (`mlflow_*`, `hud_*`) that mirror task IDs. Keep functions narrow, document non-obvious behavior with concise docstrings, and prefer explicit imports over wildcards. Maintain JSON files with two-space indentation to match the existing `tasks.json` format.

## Testing Guidelines
Test scripts wrap HUD evaluations: run them from an activated virtualenv so `.venv/bin/hud-python` is resolvable. When adding new scenarios, provide a companion `test_<scenario>.py` launcher and ensure it restores any temporary files it creates. Validate modified graders by invoking the relevant task script twice—once to apply, once to confirm idempotence—and capture regressions before opening a PR.

## Commit & Pull Request Guidelines
Commits in this repo use short, action-first messages (e.g., `Update top level docs`, `Version up hud`). Follow that tone, limit to ~60 characters, and keep related changes together. Pull requests should summarize the scenario touched, list impacted files or tools, link HUD/issue IDs, and note verification commands run. Include screenshots or logs only when they clarify grader or HUD output, and flag any credential or configuration updates so reviewers can refresh their `.env`.

## Security & Agent Operations
Never check real API secrets into version control—populate `.env` locally and describe required keys in docs. When tweaking MCP tools or graders, confirm they respect the `mlflow_user` sandbox and avoid escalating privileges. Document any new network interactions or restart mechanisms in both the code comments and this guide so future agents can replicate the setup safely.
