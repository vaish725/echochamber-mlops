import json
import logging
import time
from pathlib import Path

from anthropic import APIConnectionError, APITimeoutError, AsyncAnthropic, InternalServerError
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from app.config import Settings
from app.metrics import errors_total, llm_request_duration_seconds
from app.schemas import Detection, LLMClassification, MisinformationLabel, Post

logger = logging.getLogger(__name__)

_PROMPT_DIR = Path(__file__).parent.parent / "prompts"


def _load_prompt(version: str) -> str:
    return (_PROMPT_DIR / f"{version}_misinformation.txt").read_text(encoding="utf-8")


class MisinformationDetector:
    def __init__(self, settings: Settings) -> None:
        self._client = AsyncAnthropic(api_key=settings.anthropic_api_key)
        self._model = settings.llm_model
        self._prompt_version = settings.prompt_version
        self._system_prompt = _load_prompt(settings.prompt_version)

    # Only retry on transient network/server errors — not on refusals or parse failures
    @retry(
        retry=retry_if_exception_type((APIConnectionError, APITimeoutError, InternalServerError)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        reraise=True,
    )
    async def _call_llm(self, post_text: str) -> LLMClassification:
        response = await self._client.messages.create(
            model=self._model,
            max_tokens=512,
            system=self._system_prompt,
            messages=[{
                "role": "user",
                "content": f"Classify this social media post:\n\n<post>\n{post_text}\n</post>",
            }],
        )
        if response.stop_reason == "refusal":
            logger.warning("Claude declined to classify post — returning UNCERTAIN", extra={"post_snippet": post_text[:80]})
            return LLMClassification(
                label=MisinformationLabel.UNCERTAIN,
                confidence=0.0,
                reasoning="Classification declined by content safety system.",
            )
        text_blocks = [b for b in response.content if b.type == "text"]
        if not text_blocks:
            raise ValueError(
                f"No text block in response "
                f"(stop_reason={response.stop_reason}, "
                f"block_types={[b.type for b in response.content]})"
            )
        return LLMClassification(**json.loads(text_blocks[0].text))

    async def classify(self, post: Post) -> Detection:
        start = time.monotonic()
        try:
            classification = await self._call_llm(post.post_text)
            llm_request_duration_seconds.observe(time.monotonic() - start)
            return Detection(
                post_id=post.user_id,
                post_text=post.post_text,
                label=classification.label,
                confidence=classification.confidence,
                reasoning=classification.reasoning,
                model_version=self._model,
                prompt_version=self._prompt_version,
            )
        except Exception:
            llm_request_duration_seconds.observe(time.monotonic() - start)
            errors_total.labels(error_type="llm_error").inc()
            logger.exception(
                "LLM classification failed after retries",
                extra={"post_snippet": post.post_text[:80]},
            )
            raise
