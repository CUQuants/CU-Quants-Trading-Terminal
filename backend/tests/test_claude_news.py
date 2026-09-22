import json
import os
import sys
from datetime import datetime, timezone

import httpx
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from news.claude import ClaudeClient, ClaudeRejectedError, ClaudeUnavailableError
from news.grouping import group_articles
from news.models import Article


def event():
    article = Article(
        id="article-1",
        canonical_url="https://news.test/1",
        source="Test Wire",
        title="Exchange suspends Bitcoin withdrawals after outage",
        excerpt="The exchange reported a temporary infrastructure outage.",
        published_at_utc=datetime(2026, 9, 22, 12, tzinfo=timezone.utc),
        category="Crypto",
        assets=["BTC"],
        matched_pairs=["BTC/USD"],
        provider_metadata={"secret": "must-not-be-sent"},
    )
    return group_articles([article])[0]


def response_body(**overrides):
    output = {
        "status": "ready",
        "factual_summary": "The exchange reported a temporary withdrawal outage.",
        "market_context": "The outage may affect short-term venue liquidity.",
        "affected_assets": ["BTC"],
        "what_to_watch": ["Withdrawal status", "Venue spreads"],
        "time_horizon": "immediate",
        "impact_level": "medium",
        "confidence": "medium",
        "evidence_article_ids": ["article-1"],
    }
    output.update(overrides)
    return {
        "model": "claude-test",
        "stop_reason": "end_turn",
        "usage": {"input_tokens": 100, "output_tokens": 50},
        "content": [{"type": "text", "text": json.dumps(output)}],
    }


@pytest.mark.asyncio
async def test_builds_grounded_insight_and_sends_only_allowed_fields():
    captured = {}

    async def handler(request: httpx.Request):
        captured.update(json.loads(request.content))
        return httpx.Response(200, json=response_body())

    http_client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    client = ClaudeClient("key", "claude-test", client=http_client)

    insight = await client.create_insight(event())

    prompt = json.loads(captured["messages"][0]["content"])
    schema = captured["output_config"]["format"]["schema"]
    assert insight.status == "ready"
    assert insight.evidence_article_ids == ["article-1"]
    assert insight.input_tokens == 100
    assert schema["additionalProperties"] is False
    assert "temperature" not in captured
    assert "canonical_url" not in prompt["articles"][0]
    assert "provider_metadata" not in prompt["articles"][0]
    await http_client.aclose()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "override",
    [
        {"evidence_article_ids": ["missing-article"]},
        {"affected_assets": ["DOGE"]},
        {"market_context": "Buy immediately."},
    ],
)
async def test_rejects_ungrounded_or_advisory_output(override):
    async def handler(request: httpx.Request):
        return httpx.Response(200, json=response_body(**override))

    http_client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    client = ClaudeClient("key", "claude-test", client=http_client)

    with pytest.raises(ClaudeRejectedError):
        await client.create_insight(event())

    await http_client.aclose()


@pytest.mark.asyncio
async def test_timeout_becomes_unavailable_error():
    async def handler(request: httpx.Request):
        raise httpx.ReadTimeout("slow", request=request)

    http_client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    client = ClaudeClient("key", "claude-test", client=http_client, max_retries=0)

    with pytest.raises(ClaudeUnavailableError):
        await client.create_insight(event())

    await http_client.aclose()


@pytest.mark.asyncio
@pytest.mark.parametrize("stop_reason", ["refusal", "max_tokens"])
async def test_refusal_or_truncation_is_rejected(stop_reason):
    async def handler(request: httpx.Request):
        body = response_body()
        body["stop_reason"] = stop_reason
        return httpx.Response(200, json=body)

    http_client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    client = ClaudeClient("key", "claude-test", client=http_client)

    with pytest.raises(ClaudeRejectedError):
        await client.create_insight(event())

    await http_client.aclose()


@pytest.mark.asyncio
async def test_accepts_insufficient_evidence_state():
    async def handler(request: httpx.Request):
        return httpx.Response(200, json=response_body(
            status="insufficient_evidence",
            factual_summary="The available report is not confirmed.",
            market_context="The market effect is unclear.",
            affected_assets=[],
            what_to_watch=["Additional confirmation"],
            time_horizon="unclear",
            impact_level="unclear",
            confidence="low",
            evidence_article_ids=[],
        ))

    http_client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    client = ClaudeClient("key", "claude-test", client=http_client)

    insight = await client.create_insight(event())

    assert insight.status == "insufficient_evidence"
    assert insight.evidence_article_ids == []
    await http_client.aclose()
