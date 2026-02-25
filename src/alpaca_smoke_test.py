"""
Alpaca smoke test – intended to be run in GitHub Actions only.

Usage:
    python -m src.alpaca_smoke_test

Exits 0 on success, 1 on failure.
Never prints API keys or secrets.
"""

import os
import sys


def main() -> None:
    api_key = os.environ.get("ALPACA_API_KEY", "")
    secret_key = os.environ.get("ALPACA_SECRET_KEY", "")

    if not api_key or not secret_key:
        print("FAIL alpaca_account missing credentials (ALPACA_API_KEY or ALPACA_SECRET_KEY not set)")
        sys.exit(1)

    try:
        from alpaca.trading.client import TradingClient  # type: ignore

        client = TradingClient(
            api_key=api_key,
            secret_key=secret_key,
            paper=True,
            url_override="https://paper-api.alpaca.markets/v2",
        )
        account = client.get_account()
        status = getattr(account, "status", "UNKNOWN")
        currency = getattr(account, "currency", "UNKNOWN")
        print(f"PASS alpaca_account status={{status}} currency={{currency}}")
        sys.exit(0)
    except Exception as exc:  # noqa: BLE001
        # Sanitise the error message so no secrets can leak.
        reason = str(exc)
        for secret in (api_key, secret_key):
            if secret:
                reason = reason.replace(secret, "***")
        # Truncate to avoid accidentally leaking long env-var values.
        reason = reason[:200]
        print(f"FAIL alpaca_account {{reason}}")
        sys.exit(1)


if __name__ == "__main__":
    main()