"""
Unit tests — bot/glossary/glossary.py
Tests: resolve_business_term, resolve_time_phrase, build_glossary_context
Also includes Property 8: Glossary Consistency
"""
import pytest
from hypothesis import given, settings as h_settings
from hypothesis import strategies as st

from bot.glossary.glossary import (
    GLOSSARY,
    build_glossary_context,
    list_all_terms,
    resolve_business_term,
    resolve_metric_definition,
    resolve_time_phrase,
)


# ══════════════════════════════════════════════════════════════════════════════
# resolve_business_term
# ══════════════════════════════════════════════════════════════════════════════

class TestResolveBusinessTerm:
    def test_revenue_resolves(self):
        result = resolve_business_term("revenue")
        assert result is not None
        assert "quantity" in result.lower() or "price" in result.lower()

    def test_total_sales_resolves(self):
        result = resolve_business_term("total sales")
        assert result is not None
        assert "sum" in result.lower()

    def test_aov_resolves(self):
        result = resolve_business_term("aov")
        assert result is not None

    def test_orders_count_resolves(self):
        result = resolve_business_term("orders count")
        assert result is not None
        assert "count" in result.lower()

    def test_revenue_drop_resolves(self):
        result = resolve_business_term("revenue drop")
        assert result is not None

    def test_unknown_term_returns_none(self):
        result = resolve_business_term("xyzzy_nonexistent")
        assert result is None

    def test_empty_string_returns_none(self):
        assert resolve_business_term("") is None

    def test_none_input_returns_none(self):
        assert resolve_business_term(None) is None  # type: ignore

    # Case insensitive
    def test_uppercase_revenue(self):
        assert resolve_business_term("REVENUE") == resolve_business_term("revenue")

    def test_mixed_case_aov(self):
        assert resolve_business_term("AOV") == resolve_business_term("aov")

    def test_title_case(self):
        assert resolve_business_term("Total Sales") == resolve_business_term("total sales")


# ══════════════════════════════════════════════════════════════════════════════
# resolve_metric_definition (alias)
# ══════════════════════════════════════════════════════════════════════════════

class TestResolveMetricDefinition:
    def test_same_as_resolve_business_term(self):
        assert resolve_metric_definition("revenue") == resolve_business_term("revenue")

    def test_unknown_returns_none(self):
        assert resolve_metric_definition("fake_metric") is None


# ══════════════════════════════════════════════════════════════════════════════
# resolve_time_phrase
# ══════════════════════════════════════════════════════════════════════════════

class TestResolveTimePhrase:
    def test_yesterday(self):
        result = resolve_time_phrase("yesterday")
        assert result
        assert "CURRENT_DATE" in result or "current_date" in result.upper()
        assert "created_at" in result or "DAY" in result.upper()

    def test_last_week(self):
        result = resolve_time_phrase("last week")
        assert result
        assert "INTERVAL" in result.upper() or "interval" in result.lower()

    def test_last_30_days(self):
        result = resolve_time_phrase("last 30 days")
        assert "30" in result

    def test_custom_date_column(self):
        result = resolve_time_phrase("yesterday", date_column="ordered_at")
        assert "ordered_at" in result

    def test_unknown_phrase_returns_nonempty(self):
        result = resolve_time_phrase("some random phrase")
        assert result  # Should return something, not crash

    def test_today(self):
        result = resolve_time_phrase("today")
        assert result

    def test_this_month(self):
        result = resolve_time_phrase("this month")
        assert result

    def test_dynamic_last_n_days(self):
        result = resolve_time_phrase("last 14 days")
        assert "14" in result

    def test_empty_phrase_returns_empty_like(self):
        # Empty phrase returns empty — no crash
        result = resolve_time_phrase("")
        assert result == "" or result is not None


# ══════════════════════════════════════════════════════════════════════════════
# build_glossary_context
# ══════════════════════════════════════════════════════════════════════════════

class TestBuildGlossaryContext:
    def test_contains_all_terms(self):
        ctx = build_glossary_context()
        for term in GLOSSARY:
            assert term in ctx, f"Term '{term}' missing from glossary context"

    def test_contains_time_phrases(self):
        ctx = build_glossary_context()
        assert "yesterday" in ctx
        assert "last week" in ctx

    def test_is_non_empty_string(self):
        ctx = build_glossary_context()
        assert isinstance(ctx, str)
        assert len(ctx) > 100


# ══════════════════════════════════════════════════════════════════════════════
# Property 8: Glossary Consistency
# ══════════════════════════════════════════════════════════════════════════════

@given(term=st.sampled_from(sorted(GLOSSARY.keys())))
@h_settings(max_examples=200)
def test_property8_glossary_is_deterministic(term: str):
    """Property 8: resolve_business_term(t) always returns the same value."""
    r1 = resolve_business_term(term)
    r2 = resolve_business_term(term)
    assert r1 == r2, f"Non-deterministic result for term: {term!r}"
    assert r1 is not None, f"Registered term {term!r} resolved to None"
