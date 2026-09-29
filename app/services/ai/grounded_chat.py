from app.services.ai.extractive import _tokens

MISSING = "The meeting does not contain that information."


def answer_from_records(
    question: str,
    transcript_lines: list[str],
    summary_text: str | None,
    decisions: list[dict],
    actions: list[dict],
    risks: list[dict],
) -> str:
    """Answer from stored meeting text. Do not add facts that are not in the records."""
    asked = (question or "").strip()
    if not asked:
        return MISSING
    lowered = asked.lower()
    if _asks(lowered, ("decision", "decide", "agreed")):
        return _join(_decision_lines(decisions)) or MISSING
    if _asks(lowered, ("action", "task", "follow-up", "follow up", "to-do", "todo", "assigned")):
        return _join(_action_lines(actions)) or MISSING
    if _asks(lowered, ("risk", "concern")):
        return _join(_risk_lines(risks)) or MISSING
    if _asks(lowered, ("summary", "recap", "summarize")):
        text = (summary_text or "").strip()
        return text or MISSING

    passages = _passages(transcript_lines, summary_text, decisions, actions, risks)
    if not passages:
        return MISSING
    tokens = _tokens(asked)
    if not tokens:
        return MISSING
    ranked = []
    for passage in passages:
        haystack = set(_tokens(passage))
        score = sum(1 for token in tokens if token in haystack)
        if score:
            ranked.append((score, passage))
    if not ranked:
        return MISSING
    ranked.sort(key=lambda item: item[0], reverse=True)
    chosen = []
    for _score, passage in ranked:
        if passage not in chosen:
            chosen.append(passage)
        if len(chosen) == 4:
            break
    return "\n\n".join(chosen)


def _asks(lowered: str, cues: tuple[str, ...]) -> bool:
    return any(cue in lowered for cue in cues)


def _join(lines: list[str]) -> str:
    return "\n\n".join(line for line in lines if line.strip())


def _decision_lines(decisions: list[dict]) -> list[str]:
    lines = []
    for item in decisions:
        text = str(item.get("text") or "").strip()
        if not text:
            continue
        lines.append(f"{text}{_clock(item.get('start_seconds'))}\nOwner: {_owner(item.get('owner'))}")
    return lines


def _action_lines(actions: list[dict]) -> list[str]:
    lines = []
    for item in actions:
        text = str(item.get("description") or "").strip()
        if not text:
            continue
        lines.append(
            f"{text}{_clock(item.get('start_seconds'))}\n"
            f"Owner: {_owner(item.get('assigned_to'))}\n"
            f"Due: {_due(item.get('deadline'))}"
        )
    return lines


def _risk_lines(risks: list[dict]) -> list[str]:
    lines = []
    for item in risks:
        text = str(item.get("description") or "").strip()
        if not text:
            continue
        parts = [f"{text}{_clock(item.get('start_seconds'))}", f"Owner: {_owner(item.get('owner'))}"]
        impact = str(item.get("impact") or "").strip()
        mitigation = str(item.get("mitigation") or "").strip()
        if impact:
            parts.append(f"Impact: {impact}")
        if mitigation:
            parts.append(f"Mitigation: {mitigation}")
        lines.append("\n".join(parts))
    return lines


def _passages(
    transcript_lines: list[str],
    summary_text: str | None,
    decisions: list[dict],
    actions: list[dict],
    risks: list[dict],
) -> list[str]:
    passages = [line.strip() for line in transcript_lines if str(line or "").strip()]
    summary = (summary_text or "").strip()
    if summary:
        passages.append(summary)
    passages.extend(_decision_lines(decisions))
    passages.extend(_action_lines(actions))
    passages.extend(_risk_lines(risks))
    return passages


def _owner(value) -> str:
    text = str(value or "").strip()
    return text or "Not identified"


def _due(value) -> str:
    text = str(value or "").strip()
    return text or "Not specified"


def _clock(seconds) -> str:
    if seconds is None:
        return ""
    try:
        total = max(0, int(float(seconds)))
    except (TypeError, ValueError):
        return ""
    return f" ({total // 60}:{total % 60:02d})"
