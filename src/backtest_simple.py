"""
Simple end-to-end backtest using Datawiser free-float events + Alpaca daily bars.

Run with:
    python -m src.backtest_simple
"""

from __future__ import annotations

import json
import os
import sys
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Optional

# ---------------------------------------------------------------------------
# Config constants
# ---------------------------------------------------------------------------

START_DATE = "2022-01-01"
END_DATE: str = os.environ.get(
    "BACKTEST_END_DATE",
    datetime.now(timezone.utc).strftime("%Y-%m-%d"),
)
THRESHOLD_BPS: float = 50.0
HOLDING_DAYS: int = 5

REPO_ROOT = Path(__file__).resolve().parent.parent
UNIVERSE_FILE = REPO_ROOT / "universe.txt"
CACHE_DIR = REPO_ROOT / "data" / "cache"
OUTPUT_DIR = REPO_ROOT / "outputs"


# ---------------------------------------------------------------------------
# Environment variable validation
# ---------------------------------------------------------------------------

def _require_env(name: str) -> str:
    value = os.environ.get(name, "")
    if not value:
        print(f"ERROR: required environment variable {name} is not set", file=sys.stderr)
        sys.exit(1)
    return value


# ---------------------------------------------------------------------------
# Universe loading
# ---------------------------------------------------------------------------

def load_universe() -> list[str]:
    if not UNIVERSE_FILE.exists():
        print(f"ERROR: universe file not found: {UNIVERSE_FILE}", file=sys.stderr)
        sys.exit(1)
    symbols = []
    for line in UNIVERSE_FILE.read_text().splitlines():
        stripped = line.strip()
        if stripped and not stripped.startswith("#"):
            symbols.append(stripped.upper())
    if not symbols:
        print("ERROR: universe.txt contains no symbols", file=sys.stderr)
        sys.exit(1)
    return symbols


# ---------------------------------------------------------------------------
# Alpaca price data (with parquet cache)
# ---------------------------------------------------------------------------

def _cache_path(symbol: str) -> Path:
    return CACHE_DIR / f"{symbol}_1D_{START_DATE}_{END_DATE}.parquet"


def fetch_bars(symbol: str, api_key: str, secret_key: str):
    """Return a pandas DataFrame with columns [date, close], sorted by date."""
    import pandas as pd
    from alpaca.data.historical import StockHistoricalDataClient  # type: ignore
    from alpaca.data.requests import StockBarsRequest  # type: ignore
    from alpaca.data.timeframe import TimeFrame  # type: ignore

    cache_file = _cache_path(symbol)

    if cache_file.exists():
        df = pd.read_parquet(cache_file)
        return df

    client = StockHistoricalDataClient(api_key, secret_key)
    request = StockBarsRequest(
        symbol_or_symbols=symbol,
        timeframe=TimeFrame.Day,
        start=datetime.fromisoformat(START_DATE),
        end=datetime.fromisoformat(END_DATE),
    )
    bars = client.get_stock_bars(request)

    # bars[symbol] is a list of Bar objects
    records = []
    for bar in bars[symbol]:
        ts = bar.timestamp
        if hasattr(ts, "date"):
            bar_date = ts.date()
        else:
            bar_date = datetime.fromisoformat(str(ts)).date()
        records.append({"date": bar_date, "close": float(bar.close)})

    df = pd.DataFrame(records).sort_values("date").reset_index(drop=True)

    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    df.to_parquet(cache_file, index=False)

    return df


# ---------------------------------------------------------------------------
# Datawiser events
# ---------------------------------------------------------------------------

def fetch_events(symbol: str, dw_api_key: str):
    """Return a normalised DataFrame with columns [as_of, delta_fff_bps, is_rebal]."""
    import pandas as pd
    from datawiserai import Client  # type: ignore

    client = Client(api_key=dw_api_key)
    events_obj = client.free_float_events(symbol)
    df = events_obj.to_event_summary_dataframe()

    # Normalise column types
    df["as_of"] = pd.to_datetime(df["as_of"]).dt.date
    df["delta_fff_bps"] = pd.to_numeric(df["delta_fff_bps"], errors="coerce")
    df["is_rebal"] = df["is_rebal"].astype(bool)

    # Deduplicate by as_of — keep last row per date
    df = df.sort_values("as_of").drop_duplicates(subset=["as_of"], keep="last")

    return df


# ---------------------------------------------------------------------------
# Trade signal logic
# ---------------------------------------------------------------------------

def compute_trades(symbol: str, events_df, bars_df) -> list[dict]:
    """Return a list of trade dicts for the given symbol."""
    trades = []

    # Build sorted list of bar dates and close prices
    bar_dates = list(bars_df["date"])
    bar_closes = list(bars_df["close"])

    for _, row in events_df.iterrows():
        is_rebal = bool(row["is_rebal"])
        delta_bps = row["delta_fff_bps"]

        if is_rebal:
            continue
        try:
            delta_bps = float(delta_bps)
        except (TypeError, ValueError):
            continue
        if delta_bps >= 0 or abs(delta_bps) <= THRESHOLD_BPS:
            # Only long trades: delta_fff_bps < -THRESHOLD_BPS
            continue

        event_date = row["as_of"]
        if isinstance(event_date, str):
            event_date = date.fromisoformat(event_date)

        # Find entry index: first bar date strictly after event_date
        entry_index: Optional[int] = None
        for i, bd in enumerate(bar_dates):
            if bd > event_date:
                entry_index = i
                break

        if entry_index is None:
            continue

        exit_index = entry_index + HOLDING_DAYS
        if exit_index >= len(bar_dates):
            continue

        entry_price = bar_closes[entry_index]
        exit_price = bar_closes[exit_index]

        if not (entry_price and entry_price > 0 and exit_price and exit_price > 0):
            continue

        ret = (exit_price - entry_price) / entry_price

        trades.append({
            "symbol": symbol,
            "event_date": event_date.isoformat(),
            "entry_date": bar_dates[entry_index].isoformat(),
            "exit_date": bar_dates[exit_index].isoformat(),
            "delta_fff_bps": delta_bps,
            "holding_days": HOLDING_DAYS,
            "entry_price": entry_price,
            "exit_price": exit_price,
            "return": ret,
        })

    return trades


# ---------------------------------------------------------------------------
# Output helpers
# ---------------------------------------------------------------------------

def write_outputs(all_trades: list[dict]) -> None:
    import pandas as pd

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # results.csv
    if all_trades:
        results_df = pd.DataFrame(all_trades).sort_values(["symbol", "event_date"])
    else:
        results_df = pd.DataFrame(columns=[
            "symbol", "event_date", "entry_date", "exit_date",
            "delta_fff_bps", "holding_days", "entry_price", "exit_price", "return",
        ])
    results_df.to_csv(OUTPUT_DIR / "results.csv", index=False)

    # summary.json
    returns = [t["return"] for t in all_trades]
    n = len(returns)
    avg_ret: Optional[float] = float(sum(returns) / n) if n > 0 else None
    sorted_ret = sorted(returns)
    if n > 0:
        mid = n // 2
        median_ret: Optional[float] = (
            sorted_ret[mid] if n % 2 == 1
            else (sorted_ret[mid - 1] + sorted_ret[mid]) / 2.0
        )
        win_rate: Optional[float] = sum(1 for r in returns if r > 0) / n
    else:
        median_ret = None
        win_rate = None

    summary = {
        "trades": n,
        "avg_return": avg_ret,
        "median_return": median_ret,
        "win_rate": win_rate,
        "start_date": START_DATE,
        "end_date": END_DATE,
        "threshold_bps": THRESHOLD_BPS,
        "holding_days": HOLDING_DAYS,
    }
    (OUTPUT_DIR / "summary.json").write_text(json.dumps(summary, indent=2))

    # report.md
    _write_report(all_trades, summary)


def _write_report(all_trades: list[dict], summary: dict) -> None:
    n = summary["trades"]
    avg_ret = summary["avg_return"]
    median_ret = summary["median_return"]
    win_rate = summary["win_rate"]

    lines = [
        "# Backtest Report",
        "",
        "## Config",
        "",
        f"- Start date: {summary['start_date']}",
        f"- End date: {summary['end_date']}",
        f"- Threshold (bps): {summary['threshold_bps']}",
        f"- Holding days: {summary['holding_days']}",
        "",
        "## Results",
        "",
        f"- Trades: {n}",
        f"- Avg return: {f'{avg_ret:.4f}' if avg_ret is not None else 'N/A'}",
        f"- Median return: {f'{median_ret:.4f}' if median_ret is not None else 'N/A'}",
        f"- Win rate: {f'{win_rate:.4f}' if win_rate is not None else 'N/A'}",
        "",
    ]

    if all_trades:
        sorted_by_ret = sorted(all_trades, key=lambda t: t["return"], reverse=True)
        top5 = sorted_by_ret[:5]
        worst5 = sorted_by_ret[-5:][::-1]

        lines += [
            "## Top 5 Best Trades",
            "",
            "| Symbol | Event Date | Entry | Exit | Return |",
            "|--------|------------|-------|------|--------|",
        ]
        for t in top5:
            lines.append(
                f"| {t['symbol']} | {t['event_date']} | {t['entry_date']}"
                f" | {t['exit_date']} | {t['return']:.4f} |"
            )
        lines += [
            "",
            "## Top 5 Worst Trades",
            "",
            "| Symbol | Event Date | Entry | Exit | Return |",
            "|--------|------------|-------|------|--------|",
        ]
        for t in worst5:
            lines.append(
                f"| {t['symbol']} | {t['event_date']} | {t['entry_date']}"
                f" | {t['exit_date']} | {t['return']:.4f} |"
            )
        lines.append("")

    (OUTPUT_DIR / "report.md").write_text("\n".join(lines))


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    dw_api_key = _require_env("DATAWISER_API_KEY")
    alpaca_api_key = _require_env("ALPACA_API_KEY")
    alpaca_secret_key = _require_env("ALPACA_SECRET_KEY")

    symbols = load_universe()

    print(f"Config: start={START_DATE} end={END_DATE} threshold_bps={THRESHOLD_BPS} holding_days={HOLDING_DAYS}")
    print(f"Universe: {symbols}")

    all_trades: list[dict] = []

    for symbol in symbols:
        try:
            bars_df = fetch_bars(symbol, alpaca_api_key, alpaca_secret_key)
        except Exception as exc:
            reason = str(exc)
            for secret in (alpaca_api_key, alpaca_secret_key, dw_api_key):
                reason = reason.replace(secret, "***")
            print(f"[{symbol}] ERROR fetching bars: {reason[:200]}")
            continue

        try:
            events_df = fetch_events(symbol, dw_api_key)
        except Exception as exc:
            reason = str(exc)
            for secret in (alpaca_api_key, alpaca_secret_key, dw_api_key):
                reason = reason.replace(secret, "***")
            print(f"[{symbol}] ERROR fetching events: {reason[:200]}")
            continue

        n_events = len(events_df)
        trades = compute_trades(symbol, events_df, bars_df)
        all_trades.extend(trades)
        print(f"[{symbol}] {n_events} events → {len(trades)} trades")

    try:
        write_outputs(all_trades)
    except Exception as exc:
        print(f"ERROR: could not write outputs: {exc}", file=sys.stderr)
        sys.exit(1)

    print(f"DONE trades={len(all_trades)}")


if __name__ == "__main__":
    main()
