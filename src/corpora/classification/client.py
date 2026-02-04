"""Claude API client for term classification."""

import json
from typing import Optional

import anthropic
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from corpora.models import AxisScores, ClassifiedTerm
from corpora.classification.prompts import CLASSIFICATION_SYSTEM_PROMPT, build_user_prompt


class ClassificationClient:
    """Claude API client for classifying fantasy vocabulary.

    Uses Claude Haiku 4.5 for cost-effective classification with
    prompt caching enabled on the system prompt.
    """

    MODEL = "claude-3-5-haiku-20241022"  # Cost-effective, fast
    MAX_TOKENS = 2048

    def __init__(self, api_key: Optional[str] = None):
        """Initialize the client.

        Args:
            api_key: Anthropic API key. If None, uses ANTHROPIC_API_KEY env var.
        """
        self.client = anthropic.Anthropic(api_key=api_key)

    @retry(
        retry=retry_if_exception_type(anthropic.RateLimitError),
        wait=wait_exponential(multiplier=2, min=1, max=120),
        stop=stop_after_attempt(5),
    )
    def classify_term(
        self,
        term: str,
        source: str,
        context: str = "",
        lemma: str = "",
        pos: str = "",
    ) -> ClassifiedTerm:
        """Classify a single term using Claude API.

        Args:
            term: The term to classify
            source: Source document identifier
            context: Optional surrounding text
            lemma: Optional lemma form
            pos: Optional part of speech

        Returns:
            ClassifiedTerm with full classification

        Raises:
            anthropic.RateLimitError: After 5 retries with backoff
            ValueError: If response cannot be parsed
        """
        response = self.client.messages.create(
            model=self.MODEL,
            max_tokens=self.MAX_TOKENS,
            system=[
                {
                    "type": "text",
                    "text": CLASSIFICATION_SYSTEM_PROMPT,
                    "cache_control": {"type": "ephemeral"},
                }
            ],
            messages=[
                {"role": "user", "content": build_user_prompt(term, context, lemma, pos)}
            ],
        )

        # Parse JSON response
        content = response.content[0].text
        try:
            data = json.loads(content)
            # Add source if not in response
            data["source"] = source
            # Handle axes conversion - API returns dict, model expects AxisScores
            if "axes" in data and isinstance(data["axes"], dict):
                data["axes"] = AxisScores(**data["axes"])
            return ClassifiedTerm.model_validate(data)
        except (json.JSONDecodeError, Exception) as e:
            raise ValueError(f"Failed to parse classification for '{term}': {e}")

    def estimate_cost(
        self,
        num_terms: int,
        use_batch: bool = True,
    ) -> dict:
        """Estimate API cost for classification.

        Args:
            num_terms: Number of terms to classify
            use_batch: Whether using Batch API (50% discount)

        Returns:
            Dict with estimated input/output tokens and cost
        """
        # Estimates based on RESEARCH.md
        est_input_tokens = num_terms * 200  # ~200 per term prompt
        est_output_tokens = num_terms * 500  # ~500 per classification

        # Haiku 4.5 pricing (per million tokens)
        input_price = 0.80  # $0.80/MTok input
        output_price = 4.00  # $4.00/MTok output

        if use_batch:
            input_price *= 0.5  # 50% batch discount
            output_price *= 0.5

        # First request doesn't benefit from cache, subsequent do
        # Assume 90% cache hit rate after first
        cache_savings = 0.9 * 0.9  # 90% of requests * 90% savings
        effective_input = est_input_tokens * (1 - cache_savings)

        cost = (effective_input * input_price + est_output_tokens * output_price) / 1_000_000

        return {
            "num_terms": num_terms,
            "est_input_tokens": est_input_tokens,
            "est_output_tokens": est_output_tokens,
            "use_batch": use_batch,
            "est_cost_usd": round(cost, 4),
        }
