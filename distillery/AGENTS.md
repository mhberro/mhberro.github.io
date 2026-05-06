# AGENTS.md

Guidance for coding agents working in `distillery`.

## Scope

- This file applies to the whole repository.
- Follow existing project config over generic defaults.
- Keep changes minimal, targeted, and test-backed.

## Rule Files Discovery

- Cursor rules: none found (`.cursor/rules/` or `.cursorrules`).
- Copilot rules: none found (`.github/copilot-instructions.md`).
- If these files are added later, treat them as higher-priority guidance.

## Tech Stack Snapshot

- Python package, source under `src/distillery/`.
- CLI powered by `cyclopts`.
- Config powered by `pydantic` + `pydantic-settings`.
- LLM agent client powered by `pydantic-ai`.
- Transcript retrieval via `youtube-transcript-api`.
- Tooling: `uv`, `ruff`, `mypy`, `pytest`, `pytest-cov`, `pre-commit`.

## Environment + Setup Commands

- Sync dependencies (including dev):
  - `uv sync --all-groups`
- Sync only default dependencies:
  - `uv sync`
- Run CLI help:
  - `uv run distil --help`

## Build Commands

- Build wheel/sdist:
  - `uv build`
- Install package in editable mode is typically handled by `uv run` automatically.

## Lint / Format / Typecheck Commands

- Lint check:
  - `uv run ruff check .`
- Lint with auto-fix:
  - `uv run ruff check . --fix`
- Format:
  - `uv run ruff format .`
- Type check:
  - `uv run mypy .`
- Pre-commit all hooks:
  - `uv run pre-commit run --all-files`

## Test Commands

- Full test suite (project default, includes coverage gate):
  - `uv run pytest`
- Verbose test run:
  - `uv run pytest -vv`

### Run a Single Test (Important)

Project `pytest.ini` enforces:
- `--cov=distillery`
- `--cov-fail-under=100`

That means running a single test with default `addopts` can fail coverage.

Use one of these patterns for single-test workflows:

- Single test function, bypass repo addopts:
  - `uv run pytest -o addopts='' tests/test_transcripts.py::test_download_playlist_transcripts_dry_run`
- Single test file, bypass repo addopts:
  - `uv run pytest -o addopts='' tests/test_main.py`
- Single test while still collecting coverage (if desired):
  - `uv run pytest -o addopts='--cov=distillery --cov-report=term-missing' tests/test_main.py::test_main_with_explicit_configs`

## Expected Quality Gates

- Lint: `ruff check .` passes.
- Formatting: `ruff format .` produces no diff.
- Type checking: `mypy .` passes in strict mode.
- Tests: `pytest` passes with 100% coverage threshold.

## Code Style Guidelines

## 1) Formatting and Layout

- Follow `ruff format` output (Black-compatible, 88 columns).
- Use 4-space indentation; no tabs.
- Keep UTF-8 encoding and LF line endings (`.editorconfig`).
- Ensure trailing whitespace is removed and file ends with newline.

## 2) Imports

- Prefer absolute imports from `distillery` package.
- Group imports as stdlib / third-party / local.
- Keep import order Ruff/isort-compliant.
- Avoid unused imports; remove dead imports promptly.

## 3) Typing

- Add type annotations for all public functions and methods.
- Keep functions mypy-strict compatible.
- Avoid `Any` unless justified by boundary code.
- Prefer concrete return types (`list[Path]`, `dict[str, Any]`, etc.).
- Use narrow unions (`str | None`) over loosely typed patterns.

## 4) Naming Conventions

- Modules/functions/variables: `snake_case`.
- Classes/dataclasses: `PascalCase`.
- Constants: `UPPER_SNAKE_CASE`.
- CLI/config field names should be explicit and user-friendly.
- Keep backward-compatible aliases only when required.

## 5) Function Design

- Keep functions focused and composable.
- Prefer dependency injection at boundaries for testability.
  - Example: injectable HTTP fetch function or API client instance.
- Avoid hidden side effects in utility helpers.
- Keep cyclomatic complexity under configured threshold.

## 6) Error Handling and Logging

- Catch exceptions at integration boundaries (I/O, network, external APIs).
- Log meaningful context with `logger.exception(...)` when swallowing errors.
- Avoid broad `except Exception` in core logic unless boundary-specific.
- Do not silently ignore failures without logging or explicit return behavior.
- Prefer fail-fast for invalid configuration.

## 7) Configuration and CLI Behavior

- Put runtime options in `Configs` (pydantic settings).
- Keep environment variable behavior explicit and documented in field metadata.
- Honor precedence: explicit CLI/init values should override env when intended.
- Use `SecretStr` for secrets/API keys.

## 8) File and Path Handling

- Use `pathlib.Path` (not raw string concatenation) for filesystem paths.
- Create directories with `mkdir(parents=True, exist_ok=True)` when needed.
- Keep output naming deterministic and stable.
- Slugify user-provided names for filesystem-safe paths.

## 9) Testing Guidelines

- Add/update unit tests for every behavior change.
- Keep tests isolated: mock network and external APIs.
- Cover both success and failure paths.
- Validate side effects (written files, logged messages, returned paths).
- Maintain 100% coverage target expected by repository config.

## 10) Documentation and Comments

- Add concise docstrings for public modules/functions/classes.
- Keep comments for non-obvious logic; avoid obvious narration.
- Prefer clear naming over explanatory comments where possible.

## Change Management Expectations

- Do not remove or weaken quality gates without explicit request.
- If a change impacts CLI flags/config names, update tests accordingly.
- Preserve existing behavior unless change request explicitly alters it.
- When introducing new defaults, make them explicit in `Configs`.

## Quick Agent Checklist

- Run: `uv run ruff format .`
- Run: `uv run ruff check .`
- Run: `uv run mypy .`
- Run: `uv run pytest`
- Confirm no unintended file changes before finishing.
