"""Tests for datawiserai model classes."""

from datetime import date

import pytest

from datawiserai.models.free_float import FreeFloat, FreeFloatEvent
from datawiserai.models.free_float_events import (
    FreeFloatEventDetail,
    FreeFloatEventSummary,
    FreeFloatEvents,
    FreeFloatEventsDetail,
    FreeFloatOwnerSummary,
)
from datawiserai.models.reference import CompanyInfo, Reference, SecurityInfo
from datawiserai.models.shares_outstanding import (
    SharesOutstanding,
    SharesOutstandingEvent,
)
from datawiserai.models.universe import Universe, UniverseEntry


# ---------------------------------------------------------------------------
# Fixtures / sample data
# ---------------------------------------------------------------------------

FREE_FLOAT_EVENT_DICT = {
    "asOf": "2024-03-15",
    "freeFloatFactor": 0.85,
    "freeFloatPct": 85.0,
    "sharesOutstanding": 10_000_000.0,
    "excludedShares": 1_500_000.0,
}

FREE_FLOAT_DICT = {
    "ticker": "OLP",
    "securityId": "OLPsec01",
    "events": [FREE_FLOAT_EVENT_DICT],
}

SHARES_OUTSTANDING_EVENT_DICT = {
    "asOf": "2024-03-15",
    "shareType": "Common",
    "shares": 10_000_000.0,
    "source": "DEF14A",
    "secType": "CS",
    "lastUpdate": "2024-04-01T00:00:00Z",
}

SHARES_OUTSTANDING_DICT = {
    "ticker": "OLP",
    "securityId": "OLPsec01",
    "events": [SHARES_OUTSTANDING_EVENT_DICT],
}

REFERENCE_DICT = {
    "ticker": "OLP",
    "securityId": "OLPsec01",
    "companyName": "One Liberty Properties",
    "cik": "0000726854",
    "lei": "LEIABC123",
    "ccy": "USD",
    "mic": "XNYS",
    "isPrimary": True,
    "companyInfo": {
        "name": "One Liberty Properties",
        "address": "60 Cutter Mill Road",
        "city": "Great Neck",
        "state": "NY",
        "zip": "11021",
        "phoneNumber": "516-466-3100",
        "tin": None,
        "auditorName": "Ernst & Young LLP",
        "auditorLocation": "New York, NY",
    },
    "securityInfo": {
        "name": "One Liberty Properties Inc",
        "ticker": "OLP",
        "securityType": "Equity",
        "securityClass": "Common Stock",
        "exchangeName": "NYSE",
        "normalizedSecType": "CS",
        "Security12bTitle": "Common Shares",
    },
}

MANIFEST_DICT = {
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

FREE_FLOAT_EVENTS_DICT = {
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
# FreeFloatEvent
# ---------------------------------------------------------------------------

class TestFreeFloatEvent:
    def test_from_dict_parses_fields(self):
        ev = FreeFloatEvent._from_dict(FREE_FLOAT_EVENT_DICT)
        assert ev.as_of == date(2024, 3, 15)
        assert ev.free_float_factor == 0.85
        assert ev.free_float_pct == 85.0
        assert ev.shares_outstanding == 10_000_000.0
        assert ev.excluded_shares == 1_500_000.0

    def test_is_frozen(self):
        ev = FreeFloatEvent._from_dict(FREE_FLOAT_EVENT_DICT)
        with pytest.raises((AttributeError, TypeError)):
            ev.free_float_factor = 0.99


# ---------------------------------------------------------------------------
# FreeFloat
# ---------------------------------------------------------------------------

class TestFreeFloat:
    def test_from_dict_parses_ticker_and_security_id(self):
        ff = FreeFloat._from_dict(FREE_FLOAT_DICT)
        assert ff.ticker == "OLP"
        assert ff.security_id == "OLPsec01"

    def test_events_tuple_length(self):
        ff = FreeFloat._from_dict(FREE_FLOAT_DICT)
        assert len(ff.events) == 1
        assert isinstance(ff.events[0], FreeFloatEvent)

    def test_len(self):
        ff = FreeFloat._from_dict(FREE_FLOAT_DICT)
        assert len(ff) == 1

    def test_iter(self):
        ff = FreeFloat._from_dict(FREE_FLOAT_DICT)
        events = list(ff)
        assert len(events) == 1

    def test_latest_returns_most_recent_event(self):
        data = {
            "ticker": "OLP",
            "securityId": "OLPsec01",
            "events": [
                {**FREE_FLOAT_EVENT_DICT, "asOf": "2024-01-01"},
                {**FREE_FLOAT_EVENT_DICT, "asOf": "2024-06-01"},
            ],
        }
        ff = FreeFloat._from_dict(data)
        assert ff.latest().as_of == date(2024, 6, 1)

    def test_latest_returns_none_for_empty_events(self):
        ff = FreeFloat._from_dict({"ticker": "X", "securityId": "Y", "events": []})
        assert ff.latest() is None


# ---------------------------------------------------------------------------
# SharesOutstandingEvent
# ---------------------------------------------------------------------------

class TestSharesOutstandingEvent:
    def test_from_dict_parses_fields(self):
        ev = SharesOutstandingEvent._from_dict(SHARES_OUTSTANDING_EVENT_DICT)
        assert ev.as_of == date(2024, 3, 15)
        assert ev.share_type == "Common"
        assert ev.shares == 10_000_000.0
        assert ev.source == "DEF14A"
        assert ev.sec_type == "CS"
        assert ev.as_of_rs is None

    def test_accepts_asof_date_alias(self):
        d = {**SHARES_OUTSTANDING_EVENT_DICT}
        d.pop("asOf")
        d["asOfDate"] = "2024-03-15"
        ev = SharesOutstandingEvent._from_dict(d)
        assert ev.as_of == date(2024, 3, 15)

    def test_as_of_rs_parsed_when_present(self):
        d = {**SHARES_OUTSTANDING_EVENT_DICT, "asOfDateRs": "2024-03-20"}
        ev = SharesOutstandingEvent._from_dict(d)
        assert ev.as_of_rs == date(2024, 3, 20)


# ---------------------------------------------------------------------------
# SharesOutstanding
# ---------------------------------------------------------------------------

class TestSharesOutstanding:
    def test_from_dict_fields(self):
        so = SharesOutstanding._from_dict(SHARES_OUTSTANDING_DICT)
        assert so.ticker == "OLP"
        assert so.security_id == "OLPsec01"
        assert len(so.events) == 1

    def test_len_and_iter(self):
        so = SharesOutstanding._from_dict(SHARES_OUTSTANDING_DICT)
        assert len(so) == 1
        assert list(so)[0].share_type == "Common"

    def test_latest_returns_most_recent(self):
        data = {
            "ticker": "OLP",
            "securityId": "OLPsec01",
            "events": [
                {**SHARES_OUTSTANDING_EVENT_DICT, "asOf": "2023-01-01"},
                {**SHARES_OUTSTANDING_EVENT_DICT, "asOf": "2024-06-01"},
            ],
        }
        so = SharesOutstanding._from_dict(data)
        assert so.latest().as_of == date(2024, 6, 1)

    def test_latest_returns_none_for_empty(self):
        so = SharesOutstanding._from_dict({"ticker": "X", "securityId": "Y", "events": []})
        assert so.latest() is None


# ---------------------------------------------------------------------------
# CompanyInfo / SecurityInfo / Reference
# ---------------------------------------------------------------------------

class TestCompanyInfo:
    def test_from_dict_parses_fields(self):
        info = CompanyInfo._from_dict(REFERENCE_DICT["companyInfo"])
        assert info.name == "One Liberty Properties"
        assert info.city == "Great Neck"
        assert info.auditor_name == "Ernst & Young LLP"

    def test_from_dict_returns_none_for_empty(self):
        assert CompanyInfo._from_dict(None) is None
        assert CompanyInfo._from_dict({}) is None


class TestSecurityInfo:
    def test_from_dict_parses_fields(self):
        info = SecurityInfo._from_dict(REFERENCE_DICT["securityInfo"])
        assert info.ticker == "OLP"
        assert info.exchange_name == "NYSE"
        assert info.normalized_sec_type == "CS"

    def test_from_dict_returns_none_for_empty(self):
        assert SecurityInfo._from_dict(None) is None
        assert SecurityInfo._from_dict({}) is None


class TestReference:
    def test_from_dict_parses_top_level_fields(self):
        ref = Reference._from_dict(REFERENCE_DICT)
        assert ref.ticker == "OLP"
        assert ref.security_id == "OLPsec01"
        assert ref.company_name == "One Liberty Properties"
        assert ref.cik == "0000726854"
        assert ref.lei == "LEIABC123"
        assert ref.ccy == "USD"
        assert ref.mic == "XNYS"
        assert ref.is_primary is True

    def test_raw_payload_preserved(self):
        ref = Reference._from_dict(REFERENCE_DICT)
        assert ref.raw == REFERENCE_DICT

    def test_company_info_parsed(self):
        ref = Reference._from_dict(REFERENCE_DICT)
        assert isinstance(ref.company_info, CompanyInfo)
        assert ref.company_info.name == "One Liberty Properties"

    def test_security_info_parsed(self):
        ref = Reference._from_dict(REFERENCE_DICT)
        assert isinstance(ref.security_info, SecurityInfo)
        assert ref.security_info.ticker == "OLP"

    def test_falls_back_to_identifiers_dict(self):
        d = {
            "securityId": "sec01",
            "identifiers": {
                "tkr": "TICK",
                "nameFigi": "Corp Name",
                "cik": "12345",
                "lei": "LEIABC",
                "ccy": "USD",
                "mic": "XNYS",
            },
        }
        ref = Reference._from_dict(d)
        assert ref.ticker == "TICK"
        assert ref.company_name == "Corp Name"
        assert ref.cik == "12345"


# ---------------------------------------------------------------------------
# Universe / UniverseEntry
# ---------------------------------------------------------------------------

class TestUniverseEntry:
    def test_fields(self):
        entry = UniverseEntry(
            ticker="OLP",
            security_id="OLPsec01",
            last_update="2024-04-01T00:00:00Z",
        )
        assert entry.ticker == "OLP"
        assert entry.doc_last_update is None


class TestUniverse:
    def test_from_manifest_builds_entries(self):
        uni = Universe._from_manifest("free-float", MANIFEST_DICT)
        assert uni.endpoint == "free-float"
        assert len(uni) == 2

    def test_tickers_sorted(self):
        uni = Universe._from_manifest("free-float", MANIFEST_DICT)
        assert uni.tickers == sorted(uni.tickers)

    def test_contains_by_ticker(self):
        uni = Universe._from_manifest("free-float", MANIFEST_DICT)
        assert "OLP" in uni
        assert "UNKNOWN" not in uni

    def test_contains_by_security_id(self):
        uni = Universe._from_manifest("free-float", MANIFEST_DICT)
        assert "OLPsec01" in uni

    def test_iter(self):
        uni = Universe._from_manifest("free-float", MANIFEST_DICT)
        entries = list(uni)
        assert all(isinstance(e, UniverseEntry) for e in entries)

    def test_deduplication_by_security_id(self):
        manifest = {
            "OLP": {"ticker": "OLP", "security_id": "same_id", "last_update": "2024-01-01"},
            "OLP2": {"ticker": "OLP2", "security_id": "same_id", "last_update": "2024-01-01"},
        }
        uni = Universe._from_manifest("free-float", manifest)
        assert len(uni) == 1


# ---------------------------------------------------------------------------
# FreeFloatEventSummary
# ---------------------------------------------------------------------------

class TestFreeFloatEventSummary:
    def test_from_event_parses_fields(self):
        ev_dict = FREE_FLOAT_EVENTS_DICT["events"][0]
        summary = FreeFloatEventSummary._from_event(ev_dict)
        assert summary.as_of == date(2024, 3, 15)
        assert summary.ff_factor == 0.85
        assert summary.delta_ff_factor == 0.01
        assert summary.is_rebal is False
        assert summary.shares_out == 10_000_000.0

    def test_delta_fff_bps_computed(self):
        ev_dict = {
            "asOf": "2024-03-15",
            "ffFactor": 0.80,
            "deltaFfFactor": 0.02,
            "isRebalanced": False,
        }
        summary = FreeFloatEventSummary._from_event(ev_dict)
        expected_bps = (0.02 / 0.80) * 10000
        assert abs(summary.delta_fff_bps - expected_bps) < 1e-9

    def test_delta_fff_bps_none_when_ff_factor_zero(self):
        ev_dict = {
            "asOf": "2024-03-15",
            "ffFactor": 0.0,
            "deltaFfFactor": 0.01,
        }
        summary = FreeFloatEventSummary._from_event(ev_dict)
        assert summary.delta_fff_bps is None


# ---------------------------------------------------------------------------
# FreeFloatOwnerSummary
# ---------------------------------------------------------------------------

class TestFreeFloatOwnerSummary:
    def test_from_component_parses_fields(self):
        component = FREE_FLOAT_EVENTS_DICT["events"][0]["components"]["owner01"]
        summary = FreeFloatOwnerSummary._from_component(
            date(2024, 3, 15), "owner01", component
        )
        assert summary.as_of == date(2024, 3, 15)
        assert summary.owner_identity_id == "owner01"
        assert summary.name == "John Smith"
        assert summary.shares == 500_000.0
        assert summary.is_officer is True
        assert summary.is_new_owner is False


# ---------------------------------------------------------------------------
# FreeFloatEvents (flat view)
# ---------------------------------------------------------------------------

class TestFreeFloatEvents:
    def test_from_dict_fields(self):
        events = FreeFloatEvents._from_dict(FREE_FLOAT_EVENTS_DICT)
        assert events.ticker == "OLP"
        assert events.security_id == "OLPsec01"

    def test_from_dict_populates_owners(self):
        events = FreeFloatEvents._from_dict(FREE_FLOAT_EVENTS_DICT)
        # At least one row per owner per date
        assert len(events.owners) >= 1
        assert isinstance(events.owners[0], FreeFloatOwnerSummary)


# ---------------------------------------------------------------------------
# FreeFloatEventsDetail (nested view)
# ---------------------------------------------------------------------------

class TestFreeFloatEventsDetail:
    def test_from_dict_fields(self):
        detail = FreeFloatEventsDetail._from_dict(FREE_FLOAT_EVENTS_DICT)
        assert detail.ticker == "OLP"
        assert len(detail) == 1

    def test_dates_property(self):
        detail = FreeFloatEventsDetail._from_dict(FREE_FLOAT_EVENTS_DICT)
        assert date(2024, 3, 15) in detail.dates

    def test_by_date_lookup(self):
        detail = FreeFloatEventsDetail._from_dict(FREE_FLOAT_EVENTS_DICT)
        ev = detail.by_date("2024-03-15")
        assert ev is not None
        assert ev.as_of == date(2024, 3, 15)

    def test_by_date_returns_none_for_missing(self):
        detail = FreeFloatEventsDetail._from_dict(FREE_FLOAT_EVENTS_DICT)
        assert detail.by_date("1999-01-01") is None

    def test_getitem(self):
        detail = FreeFloatEventsDetail._from_dict(FREE_FLOAT_EVENTS_DICT)
        ev = detail[0]
        assert isinstance(ev, FreeFloatEventDetail)

    def test_owner_names_property(self):
        detail = FreeFloatEventsDetail._from_dict(FREE_FLOAT_EVENTS_DICT)
        ev = detail[0]
        assert "owner01" in ev.owner_names
        assert ev.owner_names["owner01"] == "John Smith"
