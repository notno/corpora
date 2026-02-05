"""Batch API handling for bulk term classification.

Uses Anthropic's Batch API for 50% cost savings on bulk classification.
"""

import json
import time
from typing import Callable, Iterator, List, Optional, Union

import anthropic
from anthropic.types.message_create_params import MessageCreateParamsNonStreaming
from anthropic.types.messages.batch_create_params import Request

from corpora.models import AxisScores, ClassifiedTerm
from corpora.classification.prompts import CLASSIFICATION_SYSTEM_PROMPT, build_user_prompt


class BatchClassifier:
    """Batch API classifier for cost-efficient processing.

    Uses Anthropic's Batch API to process multiple terms with 50% cost savings.
    Batches can contain up to 100k requests and typically complete within 1 hour.
    """

    MODEL = "claude-haiku-4-5-20251001"
    MAX_TOKENS = 2048
    DEFAULT_BATCH_SIZE = 50  # Terms per batch request

    def __init__(self, api_key: Optional[str] = None):
        """Initialize the batch classifier.

        Args:
            api_key: Anthropic API key. If None, uses ANTHROPIC_API_KEY env var.
        """
        self.client = anthropic.Anthropic(api_key=api_key)

    def create_batch(
        self,
        terms: List[tuple[str, str, str, str]],  # (term, source, lemma, pos) tuples
    ) -> str:
        """Create a batch request for term classification.

        Args:
            terms: List of (term, source, lemma, pos) tuples to classify

        Returns:
            Batch ID for tracking
        """
        requests = []
        for i, (term, source, lemma, pos) in enumerate(terms):
            requests.append(
                Request(
                    custom_id=f"term-{i}",
                    params=MessageCreateParamsNonStreaming(
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
                            {"role": "user", "content": build_user_prompt(term, lemma=lemma, pos=pos)}
                        ],
                    ),
                )
            )

        batch = self.client.messages.batches.create(requests=requests)
        return batch.id

    def poll_batch(
        self,
        batch_id: str,
        poll_interval: int = 60,
        on_progress: Optional[Callable[[int, int], None]] = None,
    ) -> None:
        """Poll until batch processing completes.

        Args:
            batch_id: Batch ID to poll
            poll_interval: Seconds between polls (default 60)
            on_progress: Optional callback(completed, total) for progress updates
        """
        while True:
            batch = self.client.messages.batches.retrieve(batch_id)
            counts = batch.request_counts

            if on_progress:
                completed = counts.succeeded + counts.errored + counts.expired + counts.canceled
                total = completed + counts.processing
                on_progress(completed, total)

            if batch.processing_status == "ended":
                return

            time.sleep(poll_interval)

    def stream_results(
        self,
        batch_id: str,
        source: str,
    ) -> Iterator[tuple[int, Union[ClassifiedTerm, dict]]]:
        """Stream batch results as ClassifiedTerm objects.

        Args:
            batch_id: Batch ID to retrieve results from
            source: Source document identifier for all terms

        Yields:
            Tuples of (index, ClassifiedTerm) for success
            Tuples of (index, {"error": str}) for failures
        """
        for result in self.client.messages.batches.results(batch_id):
            # Extract index from custom_id "term-{i}"
            idx = int(result.custom_id.split("-")[1])

            if result.result.type == "succeeded":
                content = result.result.message.content[0].text.strip()
                # Strip markdown code blocks if present
                if content.startswith("```"):
                    lines = content.split("\n")
                    content = "\n".join(lines[1:-1]) if lines[-1].strip() == "```" else "\n".join(lines[1:])
                try:
                    data = json.loads(content)
                    data["source"] = source
                    # Handle axes conversion
                    if "axes" in data and isinstance(data["axes"], dict):
                        data["axes"] = AxisScores(**data["axes"])
                    term = ClassifiedTerm.model_validate(data)
                    yield (idx, term)
                except Exception as e:
                    yield (idx, {"error": f"Parse error: {e}"})

            elif result.result.type == "errored":
                yield (idx, {"error": str(result.result.error)})

            elif result.result.type == "expired":
                yield (idx, {"error": "Request expired"})

            elif result.result.type == "canceled":
                yield (idx, {"error": "Request canceled"})

    def get_batch_status(self, batch_id: str) -> dict:
        """Get current batch status.

        Args:
            batch_id: Batch ID to check

        Returns:
            Dict with processing_status and request_counts
        """
        batch = self.client.messages.batches.retrieve(batch_id)
        return {
            "id": batch.id,
            "status": batch.processing_status,
            "counts": {
                "processing": batch.request_counts.processing,
                "succeeded": batch.request_counts.succeeded,
                "errored": batch.request_counts.errored,
                "expired": batch.request_counts.expired,
                "canceled": batch.request_counts.canceled,
            },
        }

    def cancel_batch(self, batch_id: str) -> dict:
        """Cancel a batch that is still processing.

        Args:
            batch_id: Batch ID to cancel

        Returns:
            Updated batch status
        """
        batch = self.client.messages.batches.cancel(batch_id)
        return {
            "id": batch.id,
            "status": batch.processing_status,
        }
