import re
from dataclasses import dataclass
from datetime import date, datetime, timedelta

from app.services.ai.extractive import TranscriptLine

_DECISION_CUES = (
    "we decided",
    "we have decided",
    "it was decided",
    "the decision is",
    "decision:",
    "we agreed",
    "agreed to",
    "we agree to",
    "we will go with",
    "let's go with",
    "lets go with",
)
_ACTION_CUES = (
    "action item",
    "action:",
    "assigned to",
    "can you ",
    "could you ",
    "please ",
    "need to ",
    "needs to ",
    "follow up",
    "follow-up",
)
_TASK_VERBS = (
    "review",
    "send",
    "check",
    "inspect",
    "order",
    "update",
    "prepare",
    "call",
    "email",
    "fix",
    "complete",
    "submit",
    "confirm",
    "schedule",
    "investigate",
    "replace",
    "test",
)
_RISK_CUES = (
    "risk",
    "risky",
    "concern",
    "worried",
    "might fail",
    "could fail",
    "could delay",
    "may delay",
    "hazard",
    "at risk",
)
_NOT_OWNERS = {
    "We",
    "I",
    "The",
    "This",
    "That",
    "It",
    "Please",
    "Speaker",
    "Notes",
    "Action",
    "Risk",
    "Decision",
    "Today",
    "Tomorrow",
    "Monday",
    "Tuesday",
    "Wednesday",
    "Thursday",
    "Friday",
    "Saturday",
    "Sunday",
    "Someone",
    "Anyone",
    "Everyone",
    "They",
    "He",
    "She",
    "You",
    "Our",
    "Their",
}
_NAME = r"[A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,2}"
_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+")


@dataclass(frozen=True)
class ExtractedDecision:
    text: str
    owner: str | None
    start_seconds: float | None


@dataclass(frozen=True)
class ExtractedAction:
    description: str
    assigned_to: str | None
    deadline: date | None
    start_seconds: float | None


@dataclass(frozen=True)
class ExtractedRisk:
    description: str
    impact: str | None
    owner: str | None
    mitigation: str | None
    start_seconds: float | None


@dataclass(frozen=True)
class TranscriptFindings:
    decisions: list[ExtractedDecision]
    actions: list[ExtractedAction]
    risks: list[ExtractedRisk]


def extract_findings(
    lines: list[TranscriptLine],
    meeting_date: date | None = None,
) -> TranscriptFindings:
    decisions: list[ExtractedDecision] = []
    actions: list[ExtractedAction] = []
    risks: list[ExtractedRisk] = []
    for line in sorted(lines, key=lambda item: item.sequence):
        start_seconds = getattr(line, "start_seconds", None)
        for sentence in _sentences(line.text):
            kind = _classify(sentence)
            if kind == "decision":
                decisions.append(
                    ExtractedDecision(
                        text=sentence,
                        owner=_owner(sentence),
                        start_seconds=start_seconds,
                    )
                )
            elif kind == "action":
                actions.append(
                    ExtractedAction(
                        description=sentence,
                        assigned_to=_owner(sentence),
                        deadline=_deadline(sentence, meeting_date),
                        start_seconds=start_seconds,
                    )
                )
            elif kind == "risk":
                risks.append(
                    ExtractedRisk(
                        description=sentence,
                        impact=_impact(sentence),
                        owner=_owner(sentence),
                        mitigation=_mitigation(sentence),
                        start_seconds=start_seconds,
                    )
                )
    return TranscriptFindings(decisions=decisions, actions=actions, risks=risks)


def _sentences(text: str) -> list[str]:
    cleaned = (text or "").strip()
    if not cleaned:
        return []
    parts = [part.strip() for part in _SENTENCE_SPLIT.split(cleaned) if part.strip()]
    return parts or [cleaned]


def _classify(sentence: str) -> str | None:
    lowered = sentence.lower()
    if _is_decision(lowered):
        return "decision"
    if _is_action(sentence, lowered):
        return "action"
    if _is_risk(lowered):
        return "risk"
    return None


def _is_decision(lowered: str) -> bool:
    if re.search(r"\bnot (approved|decided|agreed)\b", lowered):
        return False
    if "approved" in lowered and "not approved" not in lowered:
        return True
    return any(cue in lowered for cue in _DECISION_CUES)


def _is_action(sentence: str, lowered: str) -> bool:
    has_task = any(re.search(rf"\b{verb}\b", lowered) for verb in _TASK_VERBS)
    has_follow_up = "follow up" in lowered or "follow-up" in lowered
    explicit = any(cue in lowered for cue in _ACTION_CUES)
    if explicit and (has_task or has_follow_up or lowered.startswith("please ")):
        if lowered.startswith("please ") and not has_task and not has_follow_up:
            return False
        return True
    owner = _owner(sentence)
    return bool(
        owner
        and re.search(r"\b(will|needs to|should|must)\b", lowered)
        and has_task
    )


def _is_risk(lowered: str) -> bool:
    if re.search(r"\bno (risk|concern)\b", lowered):
        return False
    return any(cue in lowered for cue in _RISK_CUES)


def _owner(text: str) -> str | None:
    patterns = (
        rf"\bassigned to ({_NAME})\b",
        rf"\bowner is ({_NAME})\b",
        rf"\b({_NAME}) (?:will|needs to|should|must)\b",
    )
    for pattern in patterns:
        match = re.search(pattern, text)
        if match is None:
            continue
        name = match.group(1).strip()
        if name.split()[0] in _NOT_OWNERS:
            continue
        return name
    return None


def _deadline(text: str, meeting_date: date | None) -> date | None:
    iso = re.search(r"\b(20\d{2}-\d{2}-\d{2})\b", text)
    if iso:
        try:
            return date.fromisoformat(iso.group(1))
        except ValueError:
            return None
    day_first = re.search(
        r"\b(\d{1,2})\s+(January|February|March|April|May|June|July|August|September|October|November|December)\s+(20\d{2})\b",
        text,
        flags=re.IGNORECASE,
    )
    if day_first:
        return _parsed_date(f"{day_first.group(1)} {day_first.group(2)} {day_first.group(3)}", "%d %B %Y")
    month_first = re.search(
        r"\b(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{1,2}),?\s+(20\d{2})\b",
        text,
        flags=re.IGNORECASE,
    )
    if month_first:
        return _parsed_date(
            f"{month_first.group(1)} {month_first.group(2)} {month_first.group(3)}",
            "%B %d %Y",
        )
    if meeting_date is None:
        return None
    if re.search(r"\b(?:by|due|before)\s+tomorrow\b", text, flags=re.IGNORECASE):
        return meeting_date + timedelta(days=1)
    if re.search(r"\b(?:by|due|before)\s+today\b", text, flags=re.IGNORECASE):
        return meeting_date
    return None


def _parsed_date(value: str, pattern: str) -> date | None:
    try:
        return datetime.strptime(value, pattern).date()
    except ValueError:
        return None


def _impact(text: str) -> str | None:
    match = re.search(r"\b(high|medium|low) impact\b", text, flags=re.IGNORECASE)
    if match is None:
        return None
    return match.group(0)


def _mitigation(text: str) -> str | None:
    match = re.search(
        r"\b(?:mitigation is|mitigate by|mitigated by)\s+([^.]{3,120})",
        text,
        flags=re.IGNORECASE,
    )
    if match is None:
        return None
    return match.group(1).strip() or None
