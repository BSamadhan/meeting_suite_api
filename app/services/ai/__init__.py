from app.core.config import settings
from app.services.ai.extractive import ExtractiveSummarizer

_summarizer: ExtractiveSummarizer | None = None


def get_summarizer() -> ExtractiveSummarizer:
    global _summarizer
    provider = (settings.AI_PROVIDER or "extractive").strip().lower()
    if provider != "extractive":
        raise RuntimeError(f"Unsupported summary provider: {provider}")
    if _summarizer is None:
        _summarizer = ExtractiveSummarizer()
    return _summarizer
