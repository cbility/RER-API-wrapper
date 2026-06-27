# AGENTS.md

## Repo Shape
- Python 3.12 repo managed with `uv`.
- Library code lives directly in `src/rer.py` and `src/rer_parsing.py`; tests import them by adding `src/` to `sys.path`.
- `test/rer-python/` is live integration coverage against `rer.ofgem.gov.uk`, not offline unit tests.
- `test/rer-html/` are helper scripts that fetch and save HTML fixtures; they write `*.html` files that are ignored.

## Commands
- Install deps: `uv sync`
- Run all tests: `uv run pytest`
- Run one test file: `uv run pytest test/rer-python/test_user.py`
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
- The public wrapper is `RER_wrapper` in `src/rer.py`.
- Most parsers return `TypedDict` shapes from `src/rer_parsing.py`; preserve those field names when editing.
