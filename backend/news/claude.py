import asyncio
import json
import os
import re
import time
from datetime import datetime, timezone
from typing import Literal

import httpx
from pydantic import BaseModel, ConfigDict, ValidationError

from .models import Insight, NewsEvent

PROMPT_VERSION = "news-insight-v1"
SCHEMA_VERSION = "1"
ANTHROPIC_URL = "https://api.anthropic.com/v1/messages"

_ADVICE_RE = re.compile(
    r"\b(buy|sell|recommend|purchase|dump|enter a position|exit a position|go long|go short)\b",
    re.IGNORECASE,
)


class ClaudeError(RuntimeError):
    pass


class ClaudeUnavailableError(ClaudeError):
    pass


class ClaudeRejectedError(ClaudeError):
    pass


class ClaudeOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["ready", "insufficient_evidence"]
    factual_summary: str
    market_context: str
    affected_assets: list[str]
    what_to_watch: list[str]
    time_horizon: Literal["immediate", "intraday", "multi-day", "unclear"]
    impact_level: Literal["low", "medium", "high", "unclear"]
    confidence: Literal["low", "medium", "high"]
    evidence_article_ids: list[str]


class ClaudeClient:
    def __init__(
        self,
        api_key: str,
        model: str,
        *,
        client: httpx.AsyncClient | None = None,
        max_retries: int = 1,
    ):
        self.api_key = api_key
        self.model = model
        self.max_retries = max_retries
        self._owns_client = client is None
        self._client = client or httpx.AsyncClient(timeout=20.0)

    @classmethod
    def from_env(cls) -> "ClaudeClient | None":
        api_key = os.getenv("ANTHROPIC_API_KEY")
        model = os.getenv("CLAUDE_MODEL")
        if not api_key or not model:
            return None
        return cls(api_key=api_key, model=model)

    async def aclose(self) -> None:
        if self._owns_client:
            await self._client.aclose()

    async def create_insight(self, event: NewsEvent) -> Insight:
        started = time.perf_counter()
        response = await self._request(self._payload(event))
        latency_ms = round((time.perf_counter() - started) * 1000)

        if response.get("stop_reason") in {"refusal", "max_tokens"}:
            raise ClaudeRejectedError(f"Claude stopped with {response['stop_reason']}")

        text = next(
            (
                block.get("text")
                for block in response.get("content", [])
                if block.get("type") == "text"
            ),
            None,
        )
        if not text:
            raise ClaudeRejectedError("Claude returned no structured output")

        try:
            output = ClaudeOutput.model_validate_json(text)
        except (ValidationError, ValueError) as exc:
            raise ClaudeRejectedError("Claude returned invalid structured output") from exc

        self._validate_output(output, event)
        usage = response.get("usage", {})
        return Insight(
            event_id=event.id,
            model_version=response.get("model", self.model),
            generated_at_utc=datetime.now(timezone.utc),
            prompt_version=PROMPT_VERSION,
            schema_version=SCHEMA_VERSION,
            latency_ms=latency_ms,
            input_tokens=usage.get("input_tokens"),
            output_tokens=usage.get("output_tokens"),
            **output.model_dump(),
        )

    async def _request(self, payload: dict) -> dict:
        headers = {
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
            "x-api-key": self.api_key,
        }

        for attempt in range(self.max_retries + 1):
            try:
                response = await self._client.post(
                    ANTHROPIC_URL,
                    headers=headers,
                    json=payload,
                )
            except (httpx.TimeoutException, httpx.TransportError) as exc:
                if attempt == self.max_retries:
                    raise ClaudeUnavailableError("Claude request failed") from exc
                await asyncio.sleep(0.25 * (attempt + 1))
                continue

            if response.status_code == 429 or response.status_code >= 500:
                if attempt < self.max_retries:
                    await asyncio.sleep(0.25 * (attempt + 1))
                    continue
                raise ClaudeUnavailableError(
                    f"Claude returned HTTP {response.status_code}"
                )
            if response.status_code >= 400:
                raise ClaudeUnavailableError(
                    f"Claude returned HTTP {response.status_code}"
                )

            try:
                return response.json()
            except ValueError as exc:
                raise ClaudeRejectedError("Claude returned invalid JSON") from exc

        raise ClaudeUnavailableError("Claude request failed")

    def _payload(self, event: NewsEvent) -> dict:
        source_material = {
            "event_id": event.id,
            "category": event.category,
            "assets": event.assets,
            "matched_pairs": event.matched_pairs,
            "articles": [
                {
                    "id": article.id,
                    "source": article.source,
                    "headline": article.title[:300],
                    "excerpt": article.excerpt[:1000],
                    "published_at_utc": article.published_at_utc.isoformat(),
                }
                for article in event.articles[:8]
            ],
        }
        return {
            "model": self.model,
            "max_tokens": 900,
            "system": (
                "You summarize a grouped financial news event for traders. "
                "Use only the supplied material. Separate facts from possible market context, "
                "preserve uncertainty, and never give trading instructions or use buy/sell language. "
                "Evidence IDs and affected assets must come from the input. Return insufficient_evidence "
                "when the material is weak or contradictory."
            ),
            "messages": [
                {
                    "role": "user",
                    "content": json.dumps(source_material, separators=(",", ":")),
                }
            ],
            "output_config": {
                "format": {
                    "type": "json_schema",
                    "schema": ClaudeOutput.model_json_schema(),
                }
            },
        }

    @staticmethod
    def _validate_output(output: ClaudeOutput, event: NewsEvent) -> None:
        article_ids = {article.id for article in event.articles}
        evidence_ids = set(output.evidence_article_ids)
        known_assets = {asset.upper() for asset in event.assets}
        affected_assets = {asset.upper() for asset in output.affected_assets}

        if not evidence_ids.issubset(article_ids):
            raise ClaudeRejectedError("Insight cites an unknown article")
        if not affected_assets.issubset(known_assets):
            raise ClaudeRejectedError("Insight names an unknown asset")
        if output.status == "ready" and not evidence_ids:
            raise ClaudeRejectedError("Ready insight has no evidence")

        text = " ".join(
            [output.factual_summary, output.market_context, *output.what_to_watch]
        )
        if _ADVICE_RE.search(text):
            raise ClaudeRejectedError("Insight contains trading advice")
