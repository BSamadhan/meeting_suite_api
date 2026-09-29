import json
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from fastapi import HTTPException, status
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.google_oauth import GoogleCalendarConnection, GoogleLoginTicket
from app.models.user import User

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v3/userinfo"
GOOGLE_FREEBUSY_URL = "https://www.googleapis.com/calendar/v3/freeBusy"
GOOGLE_EVENTS_URL = "https://www.googleapis.com/calendar/v3/calendars/primary/events"

LOGIN_SCOPES = "openid email profile"
CALENDAR_SCOPE = "https://www.googleapis.com/auth/calendar"
CALENDAR_EVENTS_SCOPE = "https://www.googleapis.com/auth/calendar.events"
CALENDAR_SCOPES = (
    f"{CALENDAR_SCOPE} "
    f"{CALENDAR_EVENTS_SCOPE} "
    "https://www.googleapis.com/auth/calendar.freebusy "
    "https://www.googleapis.com/auth/userinfo.email"
)


def _setting_present(value: str | None) -> bool:
    text = str(value or "").strip()
    if not text:
        return False
    return text.lower() not in {".", "...", "changeme", "your-client-id"}


def _redirect_uri() -> str:
    return str(settings.GOOGLE_REDIRECT_URI or "").strip()


def _google_configured() -> bool:
    return (
        _setting_present(settings.GOOGLE_CLIENT_ID)
        and _setting_present(settings.GOOGLE_CLIENT_SECRET)
        and _setting_present(_redirect_uri())
    )


def _not_configured_connect() -> dict:
    return {
        "connected": False,
        "auth_url": None,
        "detail": "Google OAuth is not configured.",
    }


def _frontend_url(path: str) -> str:
    base = (settings.FRONTEND_URL or "http://localhost:5173").rstrip("/")
    if not path.startswith("/"):
        path = f"/{path}"
    return f"{base}{path}"


def _create_state(purpose: str, user_id: Optional[int] = None) -> str:
    payload = {
        "typ": "google_oauth",
        "purpose": purpose,
        "exp": datetime.now(timezone.utc) + timedelta(minutes=10),
    }
    if user_id is not None:
        payload["user_id"] = user_id
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def _parse_state(state: str) -> dict:
    try:
        payload = jwt.decode(
            state,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
        )
    except JWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired Google OAuth state.",
        ) from exc
    if payload.get("typ") != "google_oauth":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid Google OAuth state.",
        )
    return payload


def _post_form(url: str, data: dict) -> dict:
    body = urlencode(data).encode("utf-8")
    request = Request(url, data=body, method="POST")
    request.add_header("Content-Type", "application/x-www-form-urlencoded")
    try:
        with urlopen(request, timeout=20) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Google token exchange failed.",
        ) from exc
    except URLError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Unable to reach Google.",
        ) from exc


def _get_json(url: str, access_token: str) -> dict:
    request = Request(url, method="GET")
    request.add_header("Authorization", f"Bearer {access_token}")
    try:
        with urlopen(request, timeout=20) as response:
            return json.loads(response.read().decode("utf-8"))
    except (HTTPError, URLError) as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unable to load Google profile.",
        ) from exc


def _exchange_code(code: str) -> dict:
    return _post_form(
        GOOGLE_TOKEN_URL,
        {
            "code": code,
            "client_id": settings.GOOGLE_CLIENT_ID,
            "client_secret": settings.GOOGLE_CLIENT_SECRET,
            "redirect_uri": _redirect_uri(),
            "grant_type": "authorization_code",
        },
    )


def _build_auth_url(purpose: str, user_id: Optional[int] = None) -> dict:
    if not _google_configured():
        return _not_configured_connect()

    params = {
        "client_id": settings.GOOGLE_CLIENT_ID.strip(),
        "redirect_uri": _redirect_uri(),
        "response_type": "code",
        "scope": LOGIN_SCOPES if purpose == "login" else CALENDAR_SCOPES,
        "access_type": "offline",
        "prompt": "consent",
        "include_granted_scopes": "true",
        "state": _create_state(purpose, user_id),
    }
    return {
        "connected": False,
        "auth_url": f"{GOOGLE_AUTH_URL}?{urlencode(params)}",
        "detail": None,
        "redirect_uri": _redirect_uri(),
    }


def oauth_status(db: Session, user: User) -> dict:
    row = (
        db.query(GoogleCalendarConnection)
        .filter(GoogleCalendarConnection.user_id == user.id)
        .first()
    )
    configured = _google_configured()
    payload = {
        "connected": False,
        "email": None,
        "configured": configured,
        "redirect_uri": _redirect_uri() if configured else None,
    }
    if not row:
        return payload
    payload.update({"connected": True, "email": row.google_email})
    return payload


def oauth_connect(user: User) -> dict:
    return _build_auth_url("calendar", user.id)


def login_connect() -> dict:
    return _build_auth_url("login")


def _upsert_calendar_connection(
    db: Session,
    user_id: int,
    tokens: dict,
    google_email: Optional[str],
) -> None:
    expires_in = tokens.get("expires_in")
    expiry = None
    if expires_in is not None:
        expiry = datetime.now(timezone.utc) + timedelta(seconds=int(expires_in))

    row = (
        db.query(GoogleCalendarConnection)
        .filter(GoogleCalendarConnection.user_id == user_id)
        .first()
    )
    access_token = tokens.get("access_token")
    if not access_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Google did not return an access token.",
        )

    if row is None:
        row = GoogleCalendarConnection(
            user_id=user_id,
            access_token=access_token,
            refresh_token=tokens.get("refresh_token"),
            token_expiry=expiry,
            google_email=google_email,
            scopes=tokens.get("scope") or CALENDAR_SCOPES,
        )
        db.add(row)
    else:
        row.access_token = access_token
        if tokens.get("refresh_token"):
            row.refresh_token = tokens.get("refresh_token")
        row.token_expiry = expiry
        row.google_email = google_email or row.google_email
        if tokens.get("scope"):
            row.scopes = tokens.get("scope")
    db.commit()


def _find_or_create_google_user(db: Session, profile: dict) -> User:
    email = str(profile.get("email") or "").strip().lower()
    if not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Google account has no email.",
        )

    user = db.query(User).filter(User.email == email).first()
    name = (profile.get("name") or email.split("@")[0]).strip()[:100]
    if user is None:
        user = User(
            name=name or "Google user",
            email=email,
            password_hash=None,
            is_active=True,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is not active",
        )
    if name and user.name != name and not user.password_hash:
        user.name = name
        db.commit()
        db.refresh(user)
    return user


def _create_login_ticket(db: Session, user: User) -> str:
    ticket = secrets.token_urlsafe(32)
    db.add(
        GoogleLoginTicket(
            ticket=ticket,
            user_id=user.id,
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=5),
        )
    )
    db.commit()
    return ticket


def exchange_login_ticket(db: Session, ticket: str) -> User:
    row = (
        db.query(GoogleLoginTicket)
        .filter(GoogleLoginTicket.ticket == ticket)
        .first()
    )
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid Google sign-in ticket.",
        )

    expires_at = row.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at < datetime.now(timezone.utc):
        db.delete(row)
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Google sign-in ticket expired.",
        )

    user = db.query(User).filter(User.id == row.user_id).first()
    db.delete(row)
    db.commit()
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is not active",
        )
    return user


def handle_oauth_callback(db: Session, code: str, state: str) -> str:
    payload = _parse_state(state)
    purpose = payload.get("purpose")
    tokens = _exchange_code(code)
    access_token = tokens.get("access_token")
    if not access_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Google did not return an access token.",
        )
    profile = _get_json(GOOGLE_USERINFO_URL, access_token)
    google_email = str(profile.get("email") or "").strip().lower() or None

    if purpose == "calendar":
        user_id = payload.get("user_id")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Google Calendar connect is missing user context.",
            )
        _upsert_calendar_connection(db, int(user_id), tokens, google_email)
        return _frontend_url("/meetings?google=connected")

    if purpose == "login":
        user = _find_or_create_google_user(db, profile)
        ticket = _create_login_ticket(db, user)
        return _frontend_url(f"/auth/google/callback?ticket={ticket}")

    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Unknown Google OAuth purpose.",
    )


def callback_error_redirect(purpose: str | None, detail: str) -> str:
    message = urlencode({"google_error": detail})
    if purpose == "calendar":
        return _frontend_url(f"/meetings?{message}")
    return _frontend_url(f"/login?{message}")


def peek_oauth_purpose(state: str | None) -> str | None:
    if not state:
        return None
    try:
        return _parse_state(state).get("purpose")
    except HTTPException:
        return None


def _try_post_form(url: str, data: dict) -> dict | None:
    body = urlencode(data).encode("utf-8")
    request = Request(url, data=body, method="POST")
    request.add_header("Content-Type", "application/x-www-form-urlencoded")
    try:
        with urlopen(request, timeout=20) as response:
            return json.loads(response.read().decode("utf-8"))
    except (HTTPError, URLError, json.JSONDecodeError, ValueError):
        return None


def _post_json_with_token(url: str, payload: dict, access_token: str) -> dict:
    body = json.dumps(payload).encode("utf-8")
    request = Request(url, data=body, method="POST")
    request.add_header("Authorization", f"Bearer {access_token}")
    request.add_header("Content-Type", "application/json")
    with urlopen(request, timeout=20) as response:
        return json.loads(response.read().decode("utf-8"))


def _token_needs_refresh(row: GoogleCalendarConnection) -> bool:
    if row.token_expiry is None:
        return False
    expiry = row.token_expiry
    if expiry.tzinfo is None:
        expiry = expiry.replace(tzinfo=timezone.utc)
    return expiry <= datetime.now(timezone.utc) + timedelta(seconds=60)


def _refresh_calendar_token(db: Session, row: GoogleCalendarConnection) -> bool:
    if not row.refresh_token or not _google_configured():
        return False
    tokens = _try_post_form(
        GOOGLE_TOKEN_URL,
        {
            "client_id": settings.GOOGLE_CLIENT_ID,
            "client_secret": settings.GOOGLE_CLIENT_SECRET,
            "refresh_token": row.refresh_token,
            "grant_type": "refresh_token",
        },
    )
    access_token = (tokens or {}).get("access_token")
    if not access_token:
        return False
    row.access_token = access_token
    expires_in = tokens.get("expires_in")
    if expires_in is not None:
        row.token_expiry = datetime.now(timezone.utc) + timedelta(
            seconds=int(expires_in)
        )
    if tokens.get("scope"):
        row.scopes = tokens.get("scope")
    db.commit()
    return True


def _calendar_access_token(db: Session, user_id: int) -> str | None:
    connection = (
        db.query(GoogleCalendarConnection)
        .filter(GoogleCalendarConnection.user_id == user_id)
        .first()
    )
    if connection is None or not connection.access_token:
        return None
    if _token_needs_refresh(connection) and not _refresh_calendar_token(db, connection):
        return None
    return connection.access_token


def _meet_url_from_event(data: dict) -> str | None:
    link = data.get("hangoutLink")
    if link:
        return str(link)
    conference = data.get("conferenceData") or {}
    for entry in conference.get("entryPoints") or []:
        if entry.get("entryPointType") == "video" and entry.get("uri"):
            return str(entry["uri"])
    return None


def _granted_scope_text(access_token: str) -> str:
    request = Request(
        f"https://oauth2.googleapis.com/tokeninfo?access_token={access_token}",
        method="GET",
    )
    try:
        with urlopen(request, timeout=20) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (HTTPError, URLError, json.JSONDecodeError, ValueError):
        return ""
    return str(payload.get("scope") or "")


def _can_create_events(scope_text: str) -> bool:
    granted = set(scope_text.split())
    return CALENDAR_SCOPE in granted or CALENDAR_EVENTS_SCOPE in granted


def _google_error_detail(exc: HTTPError) -> str:
    message = ""
    try:
        payload = json.loads(exc.read().decode("utf-8"))
        error = payload.get("error")
        if isinstance(error, dict):
            message = str(error.get("message") or "")
        elif error:
            message = str(error)
    except (json.JSONDecodeError, OSError, ValueError):
        message = ""
    lowered = message.lower()
    if "insufficient" in lowered or "scope" in lowered:
        return (
            "Google Calendar is connected for availability only. "
            "Open Google Calendar again and allow creating events, then schedule the meeting."
        )
    if message:
        return f"Google Calendar could not create the meeting. {message}"
    if exc.code in {401, 403}:
        return (
            "Google Calendar is connected for availability only. "
            "Open Google Calendar again and allow creating events, then schedule the meeting."
        )
    return "Google Calendar could not create the meeting."


def create_google_meet_event(
    db: Session,
    *,
    organizer_id: int,
    title: str,
    description: str | None,
    meeting_date,
    start_time,
    end_time,
    timezone_name: str,
    attendee_emails: list[str],
    existing_meet_url: str | None = None,
) -> dict:
    """Create a primary-calendar event. A new Meet link is created when no URL is supplied."""
    access_token = _calendar_access_token(db, organizer_id)
    if not access_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Connect Google Calendar before scheduling an online meeting.",
        )
    granted_scopes = _granted_scope_text(access_token)
    if granted_scopes and not _can_create_events(granted_scopes):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Google Calendar is connected for availability only. "
                "Open Google Calendar again and allow creating events, then schedule the meeting."
            ),
        )

    zone = (timezone_name or "Asia/Kolkata").strip().split()[0] or "Asia/Kolkata"
    start_clock = start_time.strftime("%H:%M:%S")
    end_clock = end_time.strftime("%H:%M:%S")
    day = meeting_date.isoformat()
    attendees = [{"email": email} for email in attendee_emails if email]
    body = {
        "summary": title,
        "description": description or "",
        "start": {"dateTime": f"{day}T{start_clock}", "timeZone": zone},
        "end": {"dateTime": f"{day}T{end_clock}", "timeZone": zone},
        "attendees": attendees,
    }
    if existing_meet_url:
        body["location"] = existing_meet_url
    else:
        body["conferenceData"] = {
            "createRequest": {
                "requestId": secrets.token_hex(16),
                "conferenceSolutionKey": {"type": "hangoutsMeet"},
            }
        }

    query = "conferenceDataVersion=1"
    url = f"{GOOGLE_EVENTS_URL}?{query}"
    if attendees:
        url = f"{url}&sendUpdates=all"

    def _insert_event(target_url: str, token: str) -> dict:
        return _post_json_with_token(target_url, body, token)

    try:
        try:
            data = _insert_event(url, access_token)
        except HTTPError as first_exc:
            if first_exc.code == 403 and attendees and "sendUpdates" in url:
                data = _insert_event(f"{GOOGLE_EVENTS_URL}?{query}", access_token)
            else:
                raise first_exc
    except HTTPError as exc:
        if exc.code in {401, 403}:
            connection = (
                db.query(GoogleCalendarConnection)
                .filter(GoogleCalendarConnection.user_id == organizer_id)
                .first()
            )
            if connection and _refresh_calendar_token(db, connection):
                try:
                    data = _post_json_with_token(url, body, connection.access_token)
                except HTTPError as retry_exc:
                    raise HTTPException(
                        status_code=status.HTTP_502_BAD_GATEWAY,
                        detail=_google_error_detail(retry_exc),
                    ) from retry_exc
            else:
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail=_google_error_detail(exc),
                ) from exc
        else:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=_google_error_detail(exc),
            ) from exc
    except (URLError, json.JSONDecodeError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Unable to reach Google Calendar.",
        ) from exc

    event_id = data.get("id")
    meet_url = existing_meet_url or _meet_url_from_event(data)
    if not event_id or not meet_url:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Google Calendar did not return a Meet link.",
        )
    return {"event_id": str(event_id), "meet_url": meet_url}


def load_calendar_connections(
    db: Session,
    user_ids: set[int],
) -> dict[int, GoogleCalendarConnection]:
    if not user_ids:
        return {}
    rows = (
        db.query(GoogleCalendarConnection)
        .filter(GoogleCalendarConnection.user_id.in_(user_ids))
        .all()
    )
    return {row.user_id: row for row in rows}


def query_freebusy(
    db: Session,
    connection: GoogleCalendarConnection,
    time_min: str,
    time_max: str,
    timezone_name: str,
) -> dict:
    """Return busy intervals for the connected user's primary calendar."""
    empty = {"calendar_accessible": False, "busy_slots": [], "errors": []}
    if connection is None or not connection.access_token:
        return empty

    if _token_needs_refresh(connection):
        if not _refresh_calendar_token(db, connection):
            return {
                **empty,
                "errors": ["Google Calendar token refresh failed."],
            }

    payload = {
        "timeMin": time_min,
        "timeMax": time_max,
        "timeZone": timezone_name,
        "items": [{"id": "primary"}],
    }

    try:
        data = _post_json_with_token(
            GOOGLE_FREEBUSY_URL,
            payload,
            connection.access_token,
        )
    except HTTPError as exc:
        if exc.code in {401, 403} and _refresh_calendar_token(db, connection):
            try:
                data = _post_json_with_token(
                    GOOGLE_FREEBUSY_URL,
                    payload,
                    connection.access_token,
                )
            except (HTTPError, URLError, json.JSONDecodeError, ValueError):
                return {
                    **empty,
                    "errors": ["Unable to read Google Calendar busy times."],
                }
        else:
            return {
                **empty,
                "errors": ["Unable to read Google Calendar busy times."],
            }
    except (URLError, json.JSONDecodeError, ValueError):
        return {
            **empty,
            "errors": ["Unable to reach Google Calendar."],
        }

    calendars = data.get("calendars") or {}
    calendar = calendars.get("primary")
    if calendar is None and calendars:
        calendar = next(iter(calendars.values()))
    calendar = calendar or {}

    errors = []
    for item in calendar.get("errors") or []:
        if isinstance(item, dict):
            errors.append(str(item.get("reason") or item.get("message") or item))
        elif item:
            errors.append(str(item))

    busy_slots = []
    for slot in calendar.get("busy") or []:
        start = slot.get("start")
        end = slot.get("end")
        if start and end:
            busy_slots.append({"start": start, "end": end})

    return {
        "calendar_accessible": not errors,
        "busy_slots": busy_slots,
        "errors": errors,
    }
