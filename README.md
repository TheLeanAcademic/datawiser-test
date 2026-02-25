# datawiser-test

A lightweight test harness repo for the **Datawiser** Python package.

## What’s in this repository

- **`tests/`**: Pytest suite that exercises Datawiser behavior:
  - `test_client.py`
  - `test_models.py`
  - `test_cache.py`
  - `test_exceptions.py`
- **`.github/workflows/tests.yml`**: GitHub Actions workflow that runs the test suite.
- **`requirements-test.txt`**: Test-only dependencies (Datawiser + pytest tooling).

## Running the tests locally

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements-test.txt
pytest
```

## CI

Tests run automatically via GitHub Actions on pushes and pull requests (see `.github/workflows/tests.yml`).