"""
DataWiser API smoke test - checks we can make a basic request.

Exits 0 on success, 1 on failure.
Never prints the API key.

Run with:
    python -m src.datawiser_smoke_test
"""

import os
import sys


def main() -> None:
    api_key = os.environ.get("DATAWISER_API_KEY", "")

    if not api_key:
        print("FAIL datawiser_smoke missing credentials (DATAWISER_API_KEY not set)")
        sys.exit(1)

    try:
        from datawiserai import Client

        client = Client(api_key)
        universe = client.universe("free-float")
        count = len(universe.tickers)
        print(f"PASS datawiser_smoke universe=free-float tickers={count}")
        sys.exit(0)
    except Exception as exc:  # noqa: BLE001
        reason = str(exc).replace(api_key, "***")[:200]
        print(f"FAIL datawiser_smoke {reason}")
        sys.exit(1)


if __name__ == "__main__":
    main()