from __future__ import annotations

from mangroveai import MangroveAI
from mangroveai._transport._mock import MockTransport
from mangroveai.models.kb import (
    KBBacklinksResponse,
    KBComputeResult,
    KBDocument,
    KBDocumentSections,
    KBDocumentSummary,
    KBGlossaryEntry,
    KBGlossaryResponse,
    KBIndicator,
    KBSearchResponse,
    KBSignal,
    KBTag,
    KBTagDocuments,
)


def _make_client(mock: MockTransport) -> MangroveAI:
    return MangroveAI(api_key="test_abc123", environment="local", httpx_client=mock)


# -- Documents --

class TestKBDocuments:
    def test_list(self) -> None:
        mock = MockTransport()
        mock.add_response("GET", "/documents", json={
            "total": 2,
            "documents": [
                {"slug": "risk-management", "title": "Risk Management", "summary": "Guide to risk", "tags": ["risk"], "section_count": 5},
                {"slug": "signals-quick-ref", "title": "Signals Quick Reference", "summary": "All signals", "tags": ["signals"], "section_count": 12},
            ],
        })
        client = _make_client(mock)

        result = client.kb.documents.list()

        assert len(result) == 2
        assert isinstance(result[0], KBDocumentSummary)
        assert result[0].slug == "risk-management"
        assert result[1].section_count == 12

    def test_get(self) -> None:
        mock = MockTransport()
        mock.add_response("GET", "/documents/risk-management", json={
            "slug": "risk-management",
            "title": "Risk Management",
            "content": "# Risk Management\n\nFull content here...",
            "tags": ["risk", "trading"],
            "sections": [{"anchor": "overview", "title": "Overview", "level": 2}],
        })
        client = _make_client(mock)

        result = client.kb.documents.get("risk-management")

        assert isinstance(result, KBDocument)
        assert result.content.startswith("# Risk")
        assert len(result.sections) == 1

    def test_get_sections(self) -> None:
        mock = MockTransport()
        mock.add_response("GET", "/documents/risk-management/sections", json={
            "document_slug": "risk-management",
            "document_title": "Risk Management",
            "sections": [
                {"anchor": "overview", "title": "Overview", "level": 2},
                {"anchor": "position-sizing", "title": "Position Sizing", "level": 2},
            ],
        })
        client = _make_client(mock)

        result = client.kb.documents.get_sections("risk-management")

        assert isinstance(result, KBDocumentSections)
        assert result.document_slug == "risk-management"
        assert len(result.sections) == 2


# -- Search --

class TestKBSearch:
    def test_query(self) -> None:
        mock = MockTransport()
        mock.add_response("GET", "/search", json={
            "query": "RSI divergence",
            "total": 3,
            "results": [
                {"title": "RSI Signals", "document_slug": "signals-quick-ref", "relevance_score": 0.95, "snippet": "RSI divergence occurs when..."},
            ],
        })
        client = _make_client(mock)

        result = client.kb.search.query("RSI divergence", tags=["signals"], limit=10)

        assert isinstance(result, KBSearchResponse)
        assert result.total == 3
        assert result.results[0].relevance_score == 0.95
        assert mock.requests[0].params["q"] == "RSI divergence"
        assert mock.requests[0].params["tags"] == "signals"


# -- Tags --

class TestKBTags:
    def test_list(self) -> None:
        mock = MockTransport()
        mock.add_response("GET", "/tags", json={
            "total": 3,
            "tags": [
                {"name": "risk", "count": 4},
                {"name": "signals", "count": 8},
                {"name": "trading", "count": 6},
            ],
        })
        client = _make_client(mock)

        result = client.kb.tags.list()

        assert len(result) == 3
        assert isinstance(result[0], KBTag)
        assert result[1].name == "signals"
        assert result[1].count == 8

    def test_get(self) -> None:
        mock = MockTransport()
        mock.add_response("GET", "/tags/signals", json={
            "tag": "signals",
            "total": 2,
            "documents": [
                {"slug": "signals-quick-ref", "title": "Signals Quick Reference"},
            ],
        })
        client = _make_client(mock)

        result = client.kb.tags.get("signals")

        assert isinstance(result, KBTagDocuments)
        assert result.tag == "signals"
        assert result.total == 2


# -- Glossary --

class TestKBGlossary:
    def test_list(self) -> None:
        mock = MockTransport()
        mock.add_response("GET", "/glossary", json={
            "total": 2,
            "entries": [
                {"term": "RSI", "abbreviation": "RSI", "definition": "Relative Strength Index", "anchor": "rsi"},
                {"term": "SMA", "abbreviation": "SMA", "definition": "Simple Moving Average", "anchor": "sma"},
            ],
        })
        client = _make_client(mock)

        result = client.kb.glossary.list()

        assert isinstance(result, KBGlossaryResponse)
        assert result.total == 2
        assert result.entries[0].term == "RSI"

    def test_get(self) -> None:
        mock = MockTransport()
        mock.add_response("GET", "/glossary/RSI", json={
            "term": "RSI",
            "abbreviation": "RSI",
            "definition": "Relative Strength Index",
            "anchor": "rsi",
            "document_slug": "signals-quick-ref",
            "backlinks": [{"source": "risk-management", "anchor": "volatility"}],
        })
        client = _make_client(mock)

        result = client.kb.glossary.get("RSI")

        assert isinstance(result, KBGlossaryEntry)
        assert result.definition == "Relative Strength Index"
        assert len(result.backlinks) == 1

    def test_backlinks(self) -> None:
        mock = MockTransport()
        mock.add_response("GET", "/backlinks/rsi", json={
            "target_anchor": "rsi",
            "total": 3,
            "backlinks": [
                {"source_document": "risk-management", "source_anchor": "volatility"},
            ],
        })
        client = _make_client(mock)

        result = client.kb.glossary.backlinks("rsi")

        assert isinstance(result, KBBacklinksResponse)
        assert result.target_anchor == "rsi"
        assert result.total == 3


# -- Signals --

class TestKBSignals:
    def test_list(self) -> None:
        mock = MockTransport()
        mock.add_response("GET", "/signals", json={
            "total": 96,
            "signals": [
                {"name": "rsi_oversold", "category": "Momentum", "signal_type": "TRIGGER", "description": "RSI below threshold"},
            ],
        })
        client = _make_client(mock)

        result = client.kb.signals.list()

        assert len(result) == 1
        assert isinstance(result[0], KBSignal)
        assert result[0].name == "rsi_oversold"

    def test_list_with_filter(self) -> None:
        mock = MockTransport()
        mock.add_response("GET", "/signals", json={"total": 0, "signals": []})
        client = _make_client(mock)

        client.kb.signals.list(category="Trend", signal_type="FILTER")

        assert mock.requests[0].params["category"] == "Trend"
        assert mock.requests[0].params["signal_type"] == "FILTER"

    def test_get(self) -> None:
        mock = MockTransport()
        mock.add_response("GET", "/signals/rsi_oversold", json={
            "name": "rsi_oversold",
            "category": "Momentum",
            "signal_type": "TRIGGER",
            "description": "RSI below threshold",
            "params": {"window": {"type": "int", "default": 14}, "threshold": {"type": "float", "default": 30}},
        })
        client = _make_client(mock)

        result = client.kb.signals.get("rsi_oversold")

        assert isinstance(result, KBSignal)
        assert result.params["window"]["default"] == 14


# -- Indicators --

class TestKBIndicators:
    def test_list(self) -> None:
        mock = MockTransport()
        mock.add_response("GET", "/indicators", json={
            "total": 70,
            "indicators": [
                {"name": "sma", "category": "Trend", "description": "Simple Moving Average"},
            ],
        })
        client = _make_client(mock)

        result = client.kb.indicators.list()

        assert len(result) == 1
        assert isinstance(result[0], KBIndicator)
        assert result[0].name == "sma"

    def test_get(self) -> None:
        mock = MockTransport()
        mock.add_response("GET", "/indicators/macd", json={
            "name": "macd",
            "category": "Momentum",
            "description": "Moving Average Convergence Divergence",
            "params": {"fast_period": 12, "slow_period": 26, "signal_period": 9},
            "outputs": {"macd_line": "float", "signal_line": "float", "histogram": "float"},
        })
        client = _make_client(mock)

        result = client.kb.indicators.get("macd")

        assert isinstance(result, KBIndicator)
        assert result.outputs["histogram"] == "float"


# -- Compute (x402) --

class TestKBCompute:
    def test_evaluate_signal(self) -> None:
        mock = MockTransport()
        mock.add_response("POST", "/evaluate", json={
            "signal": "rsi_oversold",
            "result": True,
        })
        client = _make_client(mock)

        result = client.kb.compute.evaluate_signal(
            "rsi_oversold",
            ohlcv=[{"open": 100, "high": 105, "low": 95, "close": 98, "volume": 1000}],
            params={"window": 14, "threshold": 30},
        )

        assert isinstance(result, KBComputeResult)
        assert result.signal == "rsi_oversold"
        assert result.result is True

    def test_compute_indicator(self) -> None:
        mock = MockTransport()
        mock.add_response("POST", "/compute", json={
            "indicator": "sma",
            "result": {"sma": [None, None, 100.5, 101.2, 102.0]},
        })
        client = _make_client(mock)

        result = client.kb.compute.compute_indicator(
            "sma",
            data={"close": [100, 101, 102, 103, 104]},
            params={"window": 3},
        )

        assert isinstance(result, KBComputeResult)
        assert result.indicator == "sma"
        assert len(result.result["sma"]) == 5
