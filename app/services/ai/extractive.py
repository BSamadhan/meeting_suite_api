import re
from collections import Counter
from typing import Protocol

_STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "been",
    "but",
    "by",
    "for",
    "from",
    "had",
    "has",
    "have",
    "he",
    "her",
    "his",
    "i",
    "if",
    "in",
    "is",
    "it",
    "its",
    "me",
    "my",
    "of",
    "on",
    "or",
    "our",
    "she",
    "so",
    "that",
    "the",
    "their",
    "them",
    "then",
    "there",
    "they",
    "this",
    "to",
    "was",
    "we",
    "were",
    "what",
    "when",
    "which",
    "who",
    "will",
    "with",
    "you",
    "your",
}
_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+")
_WORD = re.compile(r"[A-Za-z][A-Za-z0-9'-]{2,}")


class TranscriptLine(Protocol):
    speaker: str
    text: str
    sequence: int


class MeetingBrief:
    def __init__(self, summary_text: str, key_topics: list[str]) -> None:
        self.summary_text = summary_text
        self.key_topics = key_topics


class ExtractiveSummarizer:
    """Build a summary only from sentences that are already in the transcript."""

    def summarize(self, lines: list[TranscriptLine]) -> MeetingBrief:
        sentences = _sentences(lines)
        if not sentences:
            raise ValueError("Transcript has no text to summarize.")
        chosen = _select_sentences(sentences)
        summary = "\n".join(
            f"{speaker}: {sentence}" for _index, speaker, sentence in chosen
        )
        topics = _key_topics(" ".join(sentence for _index, _speaker, sentence in sentences))
        return MeetingBrief(summary_text=summary, key_topics=topics)


def _sentences(lines: list[TranscriptLine]) -> list[tuple[int, str, str]]:
    sentences: list[tuple[int, str, str]] = []
    ordered = sorted(lines, key=lambda line: (line.sequence, 0))
    for line in ordered:
        speaker = (line.speaker or "Speaker").strip() or "Speaker"
        text = (line.text or "").strip()
        if not text:
            continue
        parts = [part.strip() for part in _SENTENCE_SPLIT.split(text) if part.strip()]
        for part in parts or [text]:
            sentences.append((len(sentences), speaker, part))
    return sentences


def _tokens(text: str) -> list[str]:
    return [
        match.group(0).lower()
        for match in _WORD.finditer(text)
        if match.group(0).lower() not in _STOPWORDS
    ]


def _select_sentences(
    sentences: list[tuple[int, str, str]],
) -> list[tuple[int, str, str]]:
    if len(sentences) <= 4:
        return sentences
    keep = min(6, max(3, len(sentences) // 3))
    tokenized = [_tokens(sentence) for _index, _speaker, sentence in sentences]
    frequency: Counter[str] = Counter()
    for tokens in tokenized:
        frequency.update(tokens)
    scored = []
    for index, tokens in enumerate(tokenized):
        if not tokens:
            score = 0.0
        else:
            score = sum(frequency[token] for token in tokens) / len(tokens)
        scored.append((score, index))
    picked = sorted(index for _score, index in sorted(scored, reverse=True)[:keep])
    return [sentences[index] for index in picked]


def _key_topics(text: str, limit: int = 6) -> list[str]:
    counts = Counter(_tokens(text))
    topics: list[str] = []
    seen: set[str] = set()
    for word, _count in counts.most_common(limit * 2):
        if word in seen:
            continue
        match = re.search(rf"\b{re.escape(word)}\b", text, flags=re.IGNORECASE)
        label = match.group(0) if match else word
        key = label.lower()
        if key in seen:
            continue
        seen.add(key)
        topics.append(label)
        if len(topics) >= limit:
            break
    return topics
