"""
Integration tests for the DataWiser API.

These tests make real HTTP requests to the DataWiser API and require a valid
DATAWISER_API_KEY environment variable to be set. They are skipped automatically
if the key is not present.

Run locally with:
    DATAWISER_API_KEY=your_key pytest tests/integration/ -v
"""

from __future__ import annotations

import os

import pytest

from datawiserai import (
    Client,
    FreeFloat,
    FreeFloatEvents,
    Reference,
    SharesOutstanding,
    TickerNotFoundError,
    Universe,
)
from datawiserai._exceptions import DatawiserAPIError

# ---------------------------------------------------------------------------
# Skip all tests in this module if no API key is configured
# ---------------------------------------------------------------------------

pytestmark = pytest.mark.skipif(
    not os.environ.get("DATAWISER_API_KEY"),
    reason="DATAWISER_API_KEY environment variable not set",
)

# Use a well-known, stable ticker for integration tests
TEST_TICKER = "MSFT"


@pytest.fixture(scope="module")
def client():
    """Return a DataWiser client using the real API key."""
    return Client(os.environ["DATAWISER_API_KEY"])


# ---------------------------------------------------------------------------
# Universe
# ---------------------------------------------------------------------------

class TestUniverseIntegration:
    def test_returns_universe_object(self, client):
        result = client.universe("free-float")
        assert isinstance(result, Universe)

    def test_universe_is_non_empty(self, client):
        result = client.universe("free-float")
        assert len(result.tickers) > 0

    def test_universe_contains_known_ticker(self, client):
        result = client.universe("free-float")
        assert TEST_TICKER in result.tickers

    def test_underscore_alias_accepted(self, client):
        result = client.universe("free_float")
        assert isinstance(result, Universe)
        assert result.endpoint == "free-float"


# ---------------------------------------------------------------------------
# Free Float
# ---------------------------------------------------------------------------

class TestFreeFloatIntegration:
    def test_returns_free_float_object(self, client):
        result = client.free_float(TEST_TICKER)
        assert isinstance(result, FreeFloat)

    def test_ticker_matches(self, client):
        result = client.free_float(TEST_TICKER)
        assert result.ticker == TEST_TICKER

    def test_has_events(self, client):
        result = client.free_float(TEST_TICKER)
        assert len(result.events) > 0

    def test_free_float_factor_is_valid(self, client):
        result = client.free_float(TEST_TICKER)
        for event in result.events:
            assert 0.0 <= event.free_float_factor <= 1.0

    def test_free_float_pct_is_valid(self, client):
        result = client.free_float(TEST_TICKER)
        for event in result.events:
            assert 0.0 <= event.free_float_pct <= 100.0

    def test_ticker_not_found_raises_error(self, client):
        with pytest.raises(TickerNotFoundError):
            client.free_float("XXXXXXXXXX_INVALID")


# ---------------------------------------------------------------------------
# Shares Outstanding
# ---------------------------------------------------------------------------

class TestSharesOutstandingIntegration:
    def test_returns_correct_type(self, client):
        result = client.shares_outstanding(TEST_TICKER)
        assert isinstance(result, SharesOutstanding)

    def test_ticker_matches(self, client):
        result = client.shares_outstanding(TEST_TICKER)
        assert result.ticker == TEST_TICKER

    def test_has_events(self, client):
        result = client.shares_outstanding(TEST_TICKER)
        assert len(result.events) > 0

    def test_shares_are_positive(self, client):
        result = client.shares_outstanding(TEST_TICKER)
        for event in result.events:
            assert event.shares > 0

    def test_ticker_not_found_raises_error(self, client):
        with pytest.raises(TickerNotFoundError):
            client.shares_outstanding("XXXXXXXXXX_INVALID")


# ---------------------------------------------------------------------------
# Reference
# ---------------------------------------------------------------------------

class TestReferenceIntegration:
    def test_returns_reference_object(self, client):
        result = client.reference(TEST_TICKER)
        assert isinstance(result, Reference)

    def test_ticker_matches(self, client):
        result = client.reference(TEST_TICKER)
        assert result.ticker == TEST_TICKER

    def test_has_company_name(self, client):
        result = client.reference(TEST_TICKER)
        assert result.company_name and len(result.company_name) > 0

    def test_has_security_id(self, client):
        result = client.reference(TEST_TICKER)
        assert result.security_id and len(result.security_id) > 0

    def test_ticker_not_found_raises_error(self, client):
        with pytest.raises(TickerNotFoundError):
            client.reference("XXXXXXXXXX_INVALID")


# ---------------------------------------------------------------------------
# Free Float Events
# ---------------------------------------------------------------------------

class TestFreeFloatEventsIntegration:
    def test_returns_free_float_events_object(self, client):
        result = client.free_float_events(TEST_TICKER)
        assert isinstance(result, FreeFloatEvents)

    def test_ticker_matches(self, client):
        result = client.free_float_events(TEST_TICKER)
        assert result.ticker == TEST_TICKER

    def test_has_owners(self, client):
        result = client.free_float_events(TEST_TICKER)
        assert len(result.owners) >= 1

    def test_ticker_not_found_raises_error(self, client):
        with pytest.raises(TickerNotFoundError):
            client.free_float_events("XXXXXXXXXX_INVALID")


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------

class TestErrorHandlingIntegration:
    def test_invalid_api_key_raises_api_error(self):
        bad_client = Client("invalid-key-00000000")
        with pytest.raises(DatawiserAPIError) as exc_info:
            bad_client.universe("free-float")
        assert exc_info.value.status_code in (401, 403)