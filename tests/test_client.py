"""Tests for the datawiserai Client class.

All HTTP calls are patched so no live network access is required.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

import datawiserai
from datawiserai import (
    Client,
    FreeFloat,
    FreeFloatEvents,
    FreeFloatEventsDetail,
    Reference,
    SharesOutstanding,
    TickerNotFoundError,
    Universe,
)
from datawiserai._exceptions import DatawiserAPIError

# ---------------------------------------------------------------------------
# Sample manifest and payload data
# ---------------------------------------------------------------------------

MANIFEST = {
    "OLP": {
        "ticker": "OLP",
        "security_id": "OLPsec01",
        "last_update": "2024-04-01T00:00:00Z",
        "doc_last_update": "2024-03-20T00:00:00Z",
    },
    "MSFT": {
        "ticker": "MSFT",
        "security_id": "MSFTsec01",
        "last_update": "2024-04-02T00:00:00Z",
        "doc_last_update": None,
    },
}

FREE_FLOAT_PAYLOAD = {
    "ticker": "OLP",
    "securityId": "OLPsec01",
    "events": [
        {
            "asOf": "2024-03-15",
            "freeFloatFactor": 0.85,
            "freeFloatPct": 85.0,
            "sharesOutstanding": 10_000_000.0,
            "excludedShares": 1_500_000.0,
        }
    ],
}

SHARES_OUTSTANDING_PAYLOAD = {
    "ticker": "OLP",
    "securityId": "OLPsec01",
    "events": [
        {
            "asOf": "2024-03-15",
            "shareType": "Common",
            "shares": 10_000_000.0,
            "source": "DEF14A",
            "secType": "CS",
            "lastUpdate": "2024-04-01T00:00:00Z",
        }
    ],
}

REFERENCE_PAYLOAD = {
    "ticker": "OLP",
    "securityId": "OLPsec01",
    "companyName": "One Liberty Properties",
    "cik": "0000726854",
    "lei": "LEIABC123",
    "ccy": "USD",
    "mic": "XNYS",
    "isPrimary": True,
}

FREE_FLOAT_EVENTS_PAYLOAD = {
    "ticker": "OLP",
    "securityId": "OLPsec01",
    "events": [
        {
            "asOf": "2024-03-15",
            "ffFactor": 0.85,
            "excludedShares": 1_500_000.0,
            "deltaShares": 50_000.0,
            "deltaFfFactor": 0.01,
            "isRebalanced": False,
            "sharesOut": 10_000_000.0,
            "components": {
                "owner01": {
                    "name": "John Smith",
                    "shares": 500_000.0,
                    "deltaShares": 10_000.0,
                    "entityType": "Individual",
                    "relType": "Insider",
                    "eventMask": 1,
                    "isOfficer": True,
                    "isExtraOwner": False,
                    "isNewOwner": False,
                    "incompleteEvent": False,
                }
            },
        }
    ],
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_client(tmp_path: Path, use_cache: bool = True) -> Client:
    """Return a Client whose Transport is fully mocked."""
    client = Client("test-api-key", cache_dir=tmp_path / "cache", use_cache=use_cache)
    return client


# ---------------------------------------------------------------------------
# Client initialisation
# ---------------------------------------------------------------------------

class TestClientInit:
    def test_creates_with_api_key(self, tmp_path):
        client = make_client(tmp_path)
        assert client._api_key == "test-api-key"

    def test_default_use_cache_is_true(self, tmp_path):
        client = make_client(tmp_path)
        assert client._use_cache is True

    def test_use_cache_false(self, tmp_path):
        client = Client("key", cache_dir=tmp_path, use_cache=False)
        assert client._use_cache is False

    def test_accepts_string_cache_dir(self, tmp_path):
        client = Client("key", cache_dir=str(tmp_path / "str_cache"))
        assert client._cache._dir == tmp_path / "str_cache"


# ---------------------------------------------------------------------------
# universe()
# ---------------------------------------------------------------------------

class TestUniverse:
    def test_returns_universe_object(self, tmp_path):
        client = make_client(tmp_path)
        client._transport.get_manifest = MagicMock(return_value=MANIFEST)
        uni = client.universe("free-float")
        assert isinstance(uni, Universe)
        assert uni.endpoint == "free-float"

    def test_tickers_present(self, tmp_path):
        client = make_client(tmp_path)
        client._transport.get_manifest = MagicMock(return_value=MANIFEST)
        uni = client.universe("free-float")
        assert "OLP" in uni.tickers
        assert "MSFT" in uni.tickers

    def test_underscore_alias_accepted(self, tmp_path):
        client = make_client(tmp_path)
        client._transport.get_manifest = MagicMock(return_value=MANIFEST)
        uni = client.universe("free_float")
        assert uni.endpoint == "free-float"


# ---------------------------------------------------------------------------
# free_float()
# ---------------------------------------------------------------------------

class TestFreeFloat:
    def test_returns_free_float_object(self, tmp_path):
        client = make_client(tmp_path)
        client._transport.get_manifest = MagicMock(return_value=MANIFEST)
        client._transport.get = MagicMock(return_value=FREE_FLOAT_PAYLOAD)
        result = client.free_float("OLP")
        assert isinstance(result, FreeFloat)
        assert result.ticker == "OLP"

    def test_events_populated(self, tmp_path):
        client = make_client(tmp_path)
        client._transport.get_manifest = MagicMock(return_value=MANIFEST)
        client._transport.get = MagicMock(return_value=FREE_FLOAT_PAYLOAD)
        result = client.free_float("OLP")
        assert len(result.events) == 1
        assert result.events[0].as_of == date(2024, 3, 15)

    def test_raises_ticker_not_found(self, tmp_path):
        client = make_client(tmp_path)
        client._transport.get_manifest = MagicMock(return_value=MANIFEST)
        with pytest.raises(TickerNotFoundError) as exc_info:
            client.free_float("UNKNOWN")
        assert exc_info.value.ticker == "UNKNOWN"
        assert exc_info.value.endpoint == "free-float"


# ---------------------------------------------------------------------------
# shares_outstanding()
# ---------------------------------------------------------------------------

class TestSharesOutstanding:
    def test_returns_shares_outstanding_object(self, tmp_path):
        client = make_client(tmp_path)
        client._transport.get_manifest = MagicMock(return_value=MANIFEST)
        client._transport.get = MagicMock(return_value=SHARES_OUTSTANDING_PAYLOAD)
        result = client.shares_outstanding("OLP")
        assert isinstance(result, SharesOutstanding)
        assert result.ticker == "OLP"

    def test_raises_ticker_not_found(self, tmp_path):
        client = make_client(tmp_path)
        client._transport.get_manifest = MagicMock(return_value=MANIFEST)
        with pytest.raises(TickerNotFoundError):
            client.shares_outstanding("BOGUS")


# ---------------------------------------------------------------------------
# reference()
# ---------------------------------------------------------------------------

class TestReference:
    def test_returns_reference_object(self, tmp_path):
        client = make_client(tmp_path)
        client._transport.get_manifest = MagicMock(return_value=MANIFEST)
        client._transport.get = MagicMock(return_value=REFERENCE_PAYLOAD)
        result = client.reference("OLP")
        assert isinstance(result, Reference)
        assert result.company_name == "One Liberty Properties"

    def test_raises_ticker_not_found(self, tmp_path):
        client = make_client(tmp_path)
        client._transport.get_manifest = MagicMock(return_value=MANIFEST)
        with pytest.raises(TickerNotFoundError):
            client.reference("MISSING")


# ---------------------------------------------------------------------------
# free_float_events()
# ---------------------------------------------------------------------------

class TestFreeFloatEvents:
    def test_returns_free_float_events_object(self, tmp_path):
        client = make_client(tmp_path)
        client._transport.get_manifest = MagicMock(return_value=MANIFEST)
        client._transport.get = MagicMock(return_value=FREE_FLOAT_EVENTS_PAYLOAD)
        result = client.free_float_events("OLP")
        assert isinstance(result, FreeFloatEvents)
        assert result.ticker == "OLP"

    def test_owners_populated(self, tmp_path):
        client = make_client(tmp_path)
        client._transport.get_manifest = MagicMock(return_value=MANIFEST)
        client._transport.get = MagicMock(return_value=FREE_FLOAT_EVENTS_PAYLOAD)
        result = client.free_float_events("OLP")
        assert len(result.owners) >= 1

    def test_raises_ticker_not_found(self, tmp_path):
        client = make_client(tmp_path)
        client._transport.get_manifest = MagicMock(return_value=MANIFEST)
        with pytest.raises(TickerNotFoundError):
            client.free_float_events("NOPE")


# ---------------------------------------------------------------------------
# free_float_events_detail()
# ---------------------------------------------------------------------------

class TestFreeFloatEventsDetail:
    def test_returns_detail_object(self, tmp_path):
        client = make_client(tmp_path)
        client._transport.get_manifest = MagicMock(return_value=MANIFEST)
        client._transport.get = MagicMock(return_value=FREE_FLOAT_EVENTS_PAYLOAD)
        result = client.free_float_events_detail("OLP")
        assert isinstance(result, FreeFloatEventsDetail)
        assert result.ticker == "OLP"

    def test_event_detail_accessible(self, tmp_path):
        client = make_client(tmp_path)
        client._transport.get_manifest = MagicMock(return_value=MANIFEST)
        client._transport.get = MagicMock(return_value=FREE_FLOAT_EVENTS_PAYLOAD)
        result = client.free_float_events_detail("OLP")
        ev = result[0]
        assert "owner01" in ev.owner_names


# ---------------------------------------------------------------------------
# Caching behaviour
# ---------------------------------------------------------------------------

class TestCaching:
    def test_cache_hit_skips_transport_get(self, tmp_path):
        client = make_client(tmp_path)
        client._transport.get_manifest = MagicMock(return_value=MANIFEST)
        transport_get = MagicMock(return_value=FREE_FLOAT_PAYLOAD)
        client._transport.get = transport_get

        # First call — populates cache
        client.free_float("OLP")
        assert transport_get.call_count == 1

        # Second call with same manifest timestamp — should hit cache
        client.free_float("OLP")
        assert transport_get.call_count == 1  # still 1; cache was used

    def test_cache_miss_when_timestamp_changes(self, tmp_path):
        client = make_client(tmp_path)
        transport_get = MagicMock(return_value=FREE_FLOAT_PAYLOAD)
        client._transport.get = transport_get

        old_manifest = {
            "OLP": {**MANIFEST["OLP"], "last_update": "2024-01-01T00:00:00Z"}
        }
        client._transport.get_manifest = MagicMock(return_value=old_manifest)
        client.free_float("OLP")
        assert transport_get.call_count == 1

        # Bump the manifest timestamp → cache is stale → fetch again
        new_manifest = {
            "OLP": {**MANIFEST["OLP"], "last_update": "2024-06-01T00:00:00Z"}
        }
        client._transport.get_manifest = MagicMock(return_value=new_manifest)
        client.free_float("OLP")
        assert transport_get.call_count == 2

    def test_use_cache_false_always_fetches(self, tmp_path):
        client = make_client(tmp_path, use_cache=False)
        client._transport.get_manifest = MagicMock(return_value=MANIFEST)
        transport_get = MagicMock(return_value=FREE_FLOAT_PAYLOAD)
        client._transport.get = transport_get

        client.free_float("OLP")
        client.free_float("OLP")
        assert transport_get.call_count == 2


# ---------------------------------------------------------------------------
# clear_cache()
# ---------------------------------------------------------------------------

class TestClearCache:
    def test_clear_all(self, tmp_path):
        client = make_client(tmp_path)
        client._transport.get_manifest = MagicMock(return_value=MANIFEST)
        client._transport.get = MagicMock(return_value=FREE_FLOAT_PAYLOAD)
        client.free_float("OLP")

        removed = client.clear_cache()
        assert removed >= 1

    def test_clear_specific_endpoint(self, tmp_path):
        client = make_client(tmp_path)
        client._transport.get_manifest = MagicMock(return_value=MANIFEST)
        client._transport.get = MagicMock(return_value=FREE_FLOAT_PAYLOAD)
        client.free_float("OLP")

        removed = client.clear_cache("free-float")
        assert removed >= 1

    def test_clear_underscore_endpoint_alias(self, tmp_path):
        client = make_client(tmp_path)
        client._transport.get_manifest = MagicMock(return_value=MANIFEST)
        client._transport.get = MagicMock(return_value=FREE_FLOAT_PAYLOAD)
        client.free_float("OLP")

        # Underscore alias should resolve correctly
        removed = client.clear_cache("free_float")
        assert removed >= 1
