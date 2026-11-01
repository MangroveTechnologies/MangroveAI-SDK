"""Tests for the X post counts read (mocked transport)."""
from __future__ import annotations

from mangrove_ai.models.social import XPostCountsResponse


def test_get_x_post_counts_parses_buckets_and_sends_params(client):
    client._http.add_response("GET", "/social/x-post-counts/BTC", json={
        "success": True,
        "symbol": "BTC",
        "query": "$BTC",
        "x_query": "all",
        "granularity": "hour",
        "days_back": 2,
        "bucket_count": 2,
        "total_posts": 1500,
        "buckets": [
            {"start": "2026-10-30T00:00:00+00:00", "end": "2026-10-30T01:00:00+00:00", "count": 700},
            {"start": "2026-10-30T01:00:00+00:00", "end": "2026-10-30T02:00:00+00:00", "count": 800},
        ],
        "x_requests": 0,
        "buckets_cached": 2,
    })
    resp = client.social.get_x_post_counts("BTC", days_back=2)

    assert isinstance(resp, XPostCountsResponse)
    assert resp.total_posts == 1500
    assert [b.count for b in resp.buckets] == [700, 800]
    assert resp.buckets[0].start == "2026-10-30T00:00:00+00:00"

    sent = client._http.requests[-1]
    assert sent.method == "GET"
    assert sent.params == {"days_back": 2, "granularity": "hour", "x_query": "all"}


def test_get_x_post_counts_quotes_the_symbol(client):
    client._http.add_response("GET", "/social/x-post-counts/BTC%2FUSD", json={
        "success": True, "symbol": "BTC/USD", "buckets": [],
    })
    resp = client.social.get_x_post_counts("BTC/USD", granularity="day", x_query="en_original")
    assert resp.buckets == []
    assert client._http.requests[-1].params["granularity"] == "day"
