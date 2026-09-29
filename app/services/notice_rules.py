from datetime import date, timedelta

from app.services.action_items import normalize_action_status

OPEN_STATUSES = {"pending", "in_progress"}
KIND_ORDER = {"overdue": 0, "due": 1, "upcoming": 2, "assigned": 3}


def build_notices(meetings: list[dict], actions: list[dict], today: date) -> list[dict]:
    notices = []
    tomorrow = today + timedelta(days=1)
    for meeting in meetings:
        if str(meeting.get("status") or "").strip().lower() != "scheduled":
            continue
        meeting_date = meeting.get("meeting_date")
        if meeting_date not in {today, tomorrow}:
            continue
        title = (meeting.get("title") or "Meeting").strip() or "Meeting"
        when = "today" if meeting_date == today else "tomorrow"
        notices.append(
            _notice(
                kind="upcoming",
                dedupe_key=f"upcoming:{meeting['id']}",
                message=f"{title} is coming up {when}.",
                meeting_id=meeting["id"],
                action_id=None,
                href=f"/meetings/{meeting['id']}",
            )
        )

    for action in actions:
        if normalize_action_status(action.get("status")) not in OPEN_STATUSES:
            continue
        description = (action.get("description") or "Action").strip() or "Action"
        meeting_id = action["meeting_id"]
        action_id = action["id"]
        href = f"/meetings/{meeting_id}/outcome/follow-up"
        owner = str(action.get("assigned_to") or "").strip()
        if owner:
            notices.append(
                _notice(
                    kind="assigned",
                    dedupe_key=f"assigned:{action_id}",
                    message=f'"{description}" was assigned to {owner}.',
                    meeting_id=meeting_id,
                    action_id=action_id,
                    href=href,
                )
            )
        deadline = action.get("deadline")
        if deadline == today:
            notices.append(
                _notice(
                    kind="due",
                    dedupe_key=f"due:{action_id}",
                    message=f'"{description}" is due today.',
                    meeting_id=meeting_id,
                    action_id=action_id,
                    href=href,
                )
            )
        elif deadline is not None and deadline < today:
            notices.append(
                _notice(
                    kind="overdue",
                    dedupe_key=f"overdue:{action_id}",
                    message=f'"{description}" is overdue.',
                    meeting_id=meeting_id,
                    action_id=action_id,
                    href=href,
                )
            )

    notices.sort(key=lambda item: (KIND_ORDER.get(item["kind"], 9), item["dedupe_key"]))
    return notices


def _notice(
    kind: str,
    dedupe_key: str,
    message: str,
    meeting_id: int,
    action_id: int | None,
    href: str,
) -> dict:
    return {
        "kind": kind,
        "dedupe_key": dedupe_key,
        "message": message,
        "meeting_id": meeting_id,
        "action_id": action_id,
        "href": href,
    }
