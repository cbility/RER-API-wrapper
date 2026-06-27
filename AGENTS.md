# AGENTS.md

## Repo Shape
- Python 3.12 repo managed with `uv`.
- Importable package code lives in `src/rer_api_wrapper/`; the public wrapper is `RER_wrapper` and the thin service facade is `RERService`.
- Response contracts are Pydantic dataclasses in `src/rer_api_wrapper/models.py`; prefer attributes over dict subscripting in new code.
- `test/rer-python/` is live integration coverage against `rer.ofgem.gov.uk`, not offline unit tests.
- `test/rer-html/` are helper scripts that fetch and save HTML fixtures; they write `*.html` files that are ignored.

## Commands
- Install deps: `uv sync`
- Run all tests: `uv run pytest`
- Run one test file: `uv run pytest test/rer-python/test_user.py`
- Type-check with the repo venv: `.venv/bin/python -m mypy src test/rer-python test/rer-html`
- Regenerate cookies: `uv run python test/bootstrap_rer_cookies.py`

## Live Test Rules
- `test/rer-python/conftest.py` skips the suite if `rer_cookies.json` is missing or invalid.
- Keep `rer_cookies.json`, `gmail_credentials.json`, `gmail_token.json`, and `.env` out of git; they are already ignored.
- Run repo-root-relative scripts from the repository root so cookie and token paths resolve correctly.

## Cookie Bootstrap
- `test/bootstrap_rer_cookies.py` needs `RER_EMAIL` and `RER_PASSWORD` from `.env` or flags.
- The bootstrap flow also needs a valid Gmail OAuth token file at `gmail_token.json` and uses Playwright plus the Gmail API.
- Saved cookies strip `ai_` tracking cookies before writing `rer_cookies.json`.

## Notes
- The package is installable from Git via `pyproject.toml`; keep import paths under `rer_api_wrapper` and avoid test-only `sys.path` hacks.
- Parser field names are the JSON API contract; preserve them when editing models or parsers.
