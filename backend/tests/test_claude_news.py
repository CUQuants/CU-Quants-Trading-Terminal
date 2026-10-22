import json
import os
import sys
from datetime import datetime, timezone

import httpx
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from models import NewsArticle
from news.claude import ClaudeClient, ClaudeRejectedError, ClaudeUnavailableError
from news.grouping import group_articles


def event():
    return group_articles([NewsArticle(
        source="Test Wire",
        title="Exchange suspends Bitcoin withdrawals after outage",
        summary="The exchange reported a temporary infrastructure outage.",
        url="https://news.test/one",
        published_at=datetime(2026, 9, 29, 12, tzinfo=timezone.utc),
        category="Crypto",
        assets=["BTC"],
    )])[0]


def response_body(article_id: str, **overrides):
    output = {
        "status": "ready",
        "affected_assets": ["BTC"],
        "factual_summary": [{
            "text": "The exchange reported a temporary withdrawal outage.",
            "article_ids": [article_id],
        }],
        "market_context": [{
            "text": "The outage may affect short-term venue liquidity.",
            "article_ids": [article_id],
        }],
        "what_to_watch": [{
            "text": "Watch withdrawal status and venue spreads.",
            "article_ids": [article_id],
        }],
        "confidence": "medium",
    }
    output.update(overrides)
    return {
        "model": "claude-test",
        "stop_reason": "end_turn",
        "usage": {"input_tokens": 100, "output_tokens": 50},
        "content": [{"type": "text", "text": json.dumps(output)}],
    }


@pytest.mark.asyncio
async def test_builds_cited_insight_and_sends_only_allowed_fields():
    news_event = event()
    article_id = news_event.articles[0].id
    captured = {}

    async def handler(request: httpx.Request):
        captured.update(json.loads(request.content))
        return httpx.Response(200, json=response_body(article_id))

    http_client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    client = ClaudeClient("key", "claude-test", client=http_client)

    insight = await client.create_insight(news_event)

    prompt = json.loads(captured["messages"][0]["content"])
    schema = captured["output_config"]["format"]["schema"]
    assert insight.validation_status == "validated"
    assert insight.factual_summary[0].article_ids == [article_id]
    assert insight.input_tokens == 100
    assert schema["additionalProperties"] is False
    assert "temperature" not in captured
    assert "url" not in prompt["articles"][0]
    await http_client.aclose()


@pytest.mark.asyncio
@pytest.mark.parametrize("invalid", ["evidence", "asset", "advice"])
async def test_rejects_ungrounded_or_advisory_output(invalid):
    news_event = event()
    article_id = news_event.articles[0].id
    overrides = {}
    if invalid == "evidence":
        overrides["factual_summary"] = [{
            "text": "Unsupported claim.",
            "article_ids": ["missing"],
        }]
    elif invalid == "asset":
        overrides["affected_assets"] = ["DOGE"]
    else:
        overrides["market_context"] = [{
            "text": "Buy immediately.",
            "article_ids": [article_id],
        }]

    async def handler(request: httpx.Request):
        return httpx.Response(200, json=response_body(article_id, **overrides))

    http_client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    client = ClaudeClient("key", "claude-test", client=http_client)

    with pytest.raises(ClaudeRejectedError):
        await client.create_insight(news_event)

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
    news_event = event()
    article_id = news_event.articles[0].id

    async def handler(request: httpx.Request):
        body = response_body(article_id)
        body["stop_reason"] = stop_reason
        return httpx.Response(200, json=body)

    http_client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    client = ClaudeClient("key", "claude-test", client=http_client)

    with pytest.raises(ClaudeRejectedError):
        await client.create_insight(news_event)

    await http_client.aclose()


@pytest.mark.asyncio
async def test_insufficient_evidence_returns_no_insight():
    news_event = event()
    article_id = news_event.articles[0].id

    async def handler(request: httpx.Request):
        return httpx.Response(200, json=response_body(
            article_id,
            status="insufficient_evidence",
            affected_assets=[],
            factual_summary=[],
            market_context=[],
            what_to_watch=[],
            confidence="low",
        ))

    http_client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    client = ClaudeClient("key", "claude-test", client=http_client)

    assert await client.create_insight(news_event) is None
    await http_client.aclose()
