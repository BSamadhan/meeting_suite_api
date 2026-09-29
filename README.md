# Meeting Suite API

FastAPI backend for Meeting Suite. It handles authentication, meetings, participants, capture actions, lookups, Google Calendar and Meet, recording uploads, speech-to-text, transcripts, extractive summaries, and dashboard counts.

Interactive docs:

- Swagger UI: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- ReDoc: [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)

API version: `0.1.0` (`app/main.py`).

## Stack

| Layer | Choice |
| --- | --- |
| API | FastAPI |
| Server | Uvicorn |
| ORM | SQLAlchemy |
| Database | PostgreSQL (`psycopg2`) |
| Migrations | Alembic |
| Auth | JWT (`python-jose`) + bcrypt (`passlib`) |
| Uploads | `python-multipart` |
| Recording files | Local object storage (`storage/objects`) |
| Speech to text | `faster-whisper` (local Whisper model) |
| Summaries | Extractive summarizer over the transcript |
| Settings | `pydantic-settings` + `.env` |
| Package manager | Pipenv |

Python version: **3.13** (see `Pipfile`).

## Project structure

```text
meeting_suite_api/
├── alembic/
│   ├── env.py
│   └── versions/
├── app/
│   ├── core/                 # Settings, lookups, security
│   ├── dependencies/         # JWT current-user dependency
│   ├── jobs/                 # Background transcription
│   ├── models/               # SQLAlchemy models
│   ├── routers/              # HTTP routes
│   ├── schemas/              # Pydantic request/response models
│   ├── services/             # Business logic, storage, STT, summaries
│   ├── database.py
│   └── main.py
├── storage/objects/          # Uploaded recordings (gitignored)
├── alembic.ini
└── Pipfile
```

Meeting, recording, transcript, and summary routes are mounted twice, at `/meetings` and `/meeting`.

## Prerequisites

- Python 3.13
- [Pipenv](https://pipenv.pypa.io/)
- PostgreSQL with a database created (default name: `meeting_suite`)

Speech-to-text downloads a Whisper model on the first transcription. The default model is `base` and runs on CPU.

## Setup

From `meeting_suite_api/`:

```bash
pipenv install
```

Create a `.env` file in `meeting_suite_api/` (gitignored):

```env
DATABASE_URL=postgresql+psycopg2://postgres:postgres@localhost:5432/meeting_suite

SECRET_KEY=replace-with-a-long-random-string
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

CORS_ORIGINS=http://localhost:3000,http://localhost:5000,http://localhost:5173,http://127.0.0.1:5000,http://127.0.0.1:5002,http://127.0.0.1:5173
FRONTEND_URL=http://localhost:5173

# Used by Alembic (alembic/env.py)
DB_ENGINE=postgresql+psycopg2
DB_NAME=meeting_suite
DB_USER=postgres
DB_PASSWORD=postgres
DB_HOST=localhost
DB_PORT=5432

# Google sign-in and Calendar OAuth
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=
GOOGLE_REDIRECT_URI=http://localhost:8000/google/oauth/callback

# Recording object storage (local disk)
STORAGE_LOCAL_DIR=storage/objects
STORAGE_PUBLIC_BASE_URL=/files

# Speech to text
STT_PROVIDER=faster_whisper
STT_MODEL=base
STT_DEVICE=cpu
STT_COMPUTE_TYPE=int8

# Summaries. Only "extractive" is implemented.
AI_PROVIDER=extractive
```

Notes:

- `SECRET_KEY` must be a strong random value. Do not commit real secrets.
- The FastAPI app reads `DATABASE_URL`. Alembic builds its URL from `DB_ENGINE`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT`, and `DB_NAME`.
- `CORS_ORIGINS` is required in `.env`, but the origins used at runtime are the hardcoded list in `app/main.py` (`localhost` and `127.0.0.1` on ports `3000`, `5000`, `5002`, `5173`, and `5174`). CORS also sets `allow_private_network=True` for local Chrome preflight.
- `STT_PROVIDER` must be `faster_whisper`. Any other value fails when transcription starts.
- `AI_PROVIDER` must be `extractive`. Any other value returns `503` from the analyze endpoint.

Create the database if it does not exist:

```sql
CREATE DATABASE meeting_suite;
```

## Database

On startup, `app/main.py` calls `Base.metadata.create_all()`, which creates tables that do not already exist. Prefer Alembic for schema changes so existing databases pick up new columns and tables.

Run these from `meeting_suite_api/` with the `.env` Alembic variables set (`DB_ENGINE`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT`).

**Apply all migrations**

```bash
pipenv run alembic upgrade head
```

**Create a new migration after model changes**

```bash
pipenv run alembic revision --autogenerate -m "describe the change"
pipenv run alembic upgrade head
```

**Other useful commands**

```bash
pipenv run alembic current
pipenv run alembic history
pipenv run alembic downgrade -1
pipenv run alembic downgrade base
```

| Command | What it does |
| --- | --- |
| `alembic upgrade head` | Apply every pending migration |
| `alembic revision --autogenerate -m "..."` | Generate a new migration from model changes |
| `alembic current` | Show the database revision |
| `alembic history` | List migration history |
| `alembic downgrade -1` | Roll back one revision |
| `alembic downgrade base` | Roll back all migrations |

Tables include `users`, `meetings`, `meeting_participants`, `meeting_agendas`, `meeting_actions`, `meeting_recordings`, `meeting_transcript_segments`, `meeting_summaries`, `google_calendar_connections`, and `google_login_tickets`.

## Run the server

From `meeting_suite_api/`:

```bash
pipenv run start
```

That runs `uvicorn app.main:app --reload`. The API listens on [http://127.0.0.1:8000](http://127.0.0.1:8000).

Pipenv uses the virtual environment in `meeting_suite_api/.venv`. `.env` sets `PIPENV_VENV_IN_PROJECT=1`, so closing the app or restarting Windows does not switch back to another environment. Run the command from `meeting_suite_api/` so Pipenv loads that `.env`.

If you are already inside `pipenv shell`, start it directly:

```bash
uvicorn app.main:app --reload
```

Calling `uvicorn` outside the Pipenv environment will fail with “uvicorn is not recognized”.

## Auth

Most routes require `Authorization: Bearer <access_token>`.

| Method | Path | Description |
| --- | --- | --- |
| `POST` | `/auth/register` | Create a user (`201`) |
| `POST` | `/auth/login` | Issue access + refresh tokens |
| `GET` | `/auth/google/` | Google sign-in URL |
| `POST` | `/auth/google/ticket` | Exchange one-time Google ticket for tokens |
| `POST` | `/auth/refresh` | Issue a new access token |

**Register**

```json
{
  "name": "Ada Lovelace",
  "email": "ada@example.com",
  "password": "at-least-8-chars"
}
```

Password length is 8–72 characters. Duplicate emails return `409`.

**Login**

```json
{
  "email": "ada@example.com",
  "password": "at-least-8-chars"
}
```

Success returns `access_token`, `refresh_token`, `token_type`, `expires_in`, and `user`. Inactive users return `403`. Invalid credentials return `401`. A Google-only account (no password) returns `401` with “This account uses Google sign-in.”

Access tokens expire after `ACCESS_TOKEN_EXPIRE_MINUTES` (default 30). Refresh tokens expire after `REFRESH_TOKEN_EXPIRE_DAYS` (default 7). Refresh returns a new access token only.

## Meetings

Meeting routes are mounted at `/meetings` and `/meeting`. List, get, update, and delete are limited to meetings created by the current user for the list endpoint. Get, update, start, end, and cancel look up a meeting by id.

| Method | Path | Description |
| --- | --- | --- |
| `POST` | `/meetings/` | Create a meeting (`201`) |
| `GET` | `/meetings/` | List meetings created by the current user (paginated) |
| `GET` | `/meetings/{id}/` | Get one meeting |
| `PUT` | `/meetings/{id}/` | Update a meeting |
| `DELETE` | `/meetings/{id}/` | Delete a meeting (`204`) |
| `POST` | `/meetings/start/{id}/` | Start (`ongoing`) and stamp `actual_start_at` |
| `POST` | `/meetings/end/{id}/` | End (`completed`) and stamp `actual_end_at` |
| `POST` | `/meetings/cancel/{id}/` | Cancel (`cancelled`) |
| `POST` | `/meetings/check-availability/` | Google Calendar + local busy-time check |
| `GET` | `/meetings/categories/` | Meeting category lookup |
| `GET` | `/meetings/repeat-types/` | Repeat type lookup |

Create accepts nested `participants` and `agendas`. `chair_id` defaults to the current user when omitted. `auto_generate_meeting_link` defaults to `true`. For an online meeting, that creates a Google Calendar event and Meet link on the organizer’s connected calendar. The organizer must have connected Calendar with permission to create events, and the meeting needs a date and start time. The stored `google_event_id` and `meeting_link` come back on the meeting response.

**List query params**

```http
GET /meetings?page=1&page_size=10&search=production&status=COMPLETED&meeting_date=2026-09-21&period=upcoming&meeting_type=ONLINE
```

| Param | Default | Notes |
| --- | --- | --- |
| `page` | `1` | 1-based |
| `page_size` | `10` | Max `100` |
| `search` | — | Matches title, location, host, description, category |
| `status` | — | Case-insensitive (`SCHEDULED`, `ONGOING`, `COMPLETED`, `CANCELLED`) |
| `meeting_date` | — | Exact date (`YYYY-MM-DD`) |
| `period` | — | `upcoming` (scheduled/ongoing) or `past` (completed/cancelled) |
| `meeting_type` | — | `ONLINE` or `OFFLINE` |

**List response**

```json
{
  "items": [],
  "page": 1,
  "page_size": 10,
  "total": 42,
  "total_pages": 5
}
```

Start is allowed from `scheduled`. End is allowed from `ongoing` or `scheduled`. Cancel is allowed from `scheduled` or `ongoing`.

**Check availability**

`timezone` is an IANA name (`Asia/Kolkata`). The UI may send `Asia/Kolkata (IST)`; the API uses the first token. `chair` may also be sent as `chair_id`. `participants` may be user ids or `{ user_id, email, guest_email, role }` objects. `exclude_meeting_id` skips one meeting when checking local overlaps.

```json
{
  "meeting_date": "2026-09-21",
  "start_time": "15:02:00",
  "end_time": "15:32:00",
  "timezone": "Asia/Kolkata",
  "chair": 6,
  "created_by": 6,
  "participants": []
}
```

Busy times come from Google Calendar FreeBusy when the user has connected Calendar, plus overlapping meetings in this app. Chair and creator are always included in `data.participants`.

## Participants

| Method | Path | Description |
| --- | --- | --- |
| `GET` | `/meetings/{id}/participants` | List active participants |
| `POST` | `/meetings/{id}/participants` | Add a registered user (`201`) |
| `DELETE` | `/meetings/{id}/participants/{user_id}` | Remove (sets `left_at`, `204`) |

Roles: `HOST`, `PARTICIPANT`, `ORGANIZER`. `ATTENDEE` is accepted and stored as `PARTICIPANT`.

**Add**

```json
{
  "user_id": 5,
  "role": "PARTICIPANT"
}
```

Response includes `id`, `meeting_id`, `user_id`, `role`, `joined_at`, `left_at`, `name`, and `email`.

## Lookups and users

| Method | Path | Description |
| --- | --- | --- |
| `GET` | `/users/` | Active users, ordered by name |
| `GET` | `/meeting-locations/` | Location lookup |

## Capture actions

| Method | Path | Description |
| --- | --- | --- |
| `GET` | `/capture-actions/?meeting_id=` | List actions. Omit `meeting_id` to list all |
| `POST` | `/capture-actions/` | Create an action (`201`). Default status is `OPEN` |

**Create**

```json
{
  "meeting_id": 12,
  "description": "Send the revised agenda",
  "assigned_to": "Ada Lovelace",
  "deadline": "2026-09-30",
  "department": "Product",
  "priority": "high",
  "agenda_id": null
}
```

## Dashboard

`GET /dashboard/summary` counts meetings created by the current user.

| Field | Meaning |
| --- | --- |
| `today` | Meetings dated today that are not cancelled |
| `upcoming` | Status `scheduled` |
| `in_progress` | Status `ongoing` |
| `completed` | Status `completed` |
| `action_items` | Actions on those meetings |
| `pending_actions` | Actions whose status is `open` or `pending` |
| `open_risks` | Always `0`. Risks are not stored yet |

## Recordings

The file is stored on disk. Postgres stores metadata only.

| Method | Path | Description |
| --- | --- | --- |
| `POST` | `/meetings/{id}/recording` | Upload a recording (`201`) |
| `GET` | `/meetings/{id}/recording` | Latest recording metadata |
| `POST` | `/meetings/{id}/speech-to-text` | Start transcription (`202`) |

Multipart field: `file`. Optional form field: `duration`.

Supported formats: MP3, WAV, M4A, MP4, WEBM. Max size is 500 MB. Uploaded files are served from `/files/...`.

**Upload response**

```json
{
  "recording_id": 1,
  "meeting_id": 12,
  "file_url": "/files/meetings/12/recordings/….mp4",
  "duration": null,
  "status": "UPLOADED",
  "error_message": null,
  "created_at": "2026-09-23T10:00:00"
}
```

Recording statuses: `UPLOADED`, `PROCESSING`, `COMPLETED`, `FAILED`.

**Speech to text**

`POST /meetings/{id}/speech-to-text` sets the latest recording to `PROCESSING` and runs `faster-whisper` in a background task. Poll `GET /meetings/{id}/recording` until status is `COMPLETED` or `FAILED`. A failure stores a short message in `error_message`.

- `400` when the meeting has no recording.
- `409` when speech-to-text is already running.
- Spoken lines are written to the transcript with speaker `Speaker`. There is no speaker diarization.
- Typed notes (speaker `Notes`) are kept when speech-to-text replaces spoken lines.

The first run loads the Whisper model named by `STT_MODEL` (default `base`).

## Transcript

| Method | Path | Description |
| --- | --- | --- |
| `GET` | `/meetings/{id}/transcript` | List segments in sequence order |
| `PUT` | `/meetings/{id}/transcript` | Replace the whole transcript |
| `POST` | `/meetings/{id}/notes` | Append a note (`201`) |

Each segment has `speaker`, `text`, optional `start_seconds`, `end_seconds`, and `confidence`. `PUT` accepts up to 5000 segments and renumbers `sequence` from 1. A note is stored with speaker `Notes`.

**Replace**

```json
{
  "segments": [
    {
      "speaker": "Ada",
      "text": "We will ship the recording flow this week.",
      "start_seconds": 0,
      "end_seconds": 4.2
    }
  ]
}
```

**Note**

```json
{
  "text": "Follow up with finance after the call."
}
```

## Summary

Summaries are built from sentences already in the transcript. The extractive summarizer does not call an external language model.

| Method | Path | Description |
| --- | --- | --- |
| `POST` | `/meetings/{id}/ai/analyze` | Create a new summary (`201`) |
| `GET` | `/meetings/{id}/summary` | Latest summary |

`POST` returns `400` when the transcript has no text, and `503` when `AI_PROVIDER` is not `extractive`. Each analyze inserts a new row. `GET` returns the newest one, or `404` when none exists.

```json
{
  "id": 1,
  "meeting_id": 12,
  "summary_text": "Ada: We will ship the recording flow this week.",
  "key_topics": ["recording", "ship"],
  "created_at": "2026-09-23T10:05:00"
}
```

## Google sign-in and Calendar OAuth

Set `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, and `GOOGLE_REDIRECT_URI` in `.env`. The redirect URI must match the Google Cloud client exactly, for example `http://localhost:8000/google/oauth/callback`.

Set `FRONTEND_URL` to the UI origin (Vite may be `http://localhost:5173` or `http://localhost:5174`).

**Sign-in**

1. UI calls `GET /auth/google/` and sends the user to `auth_url`.
2. Google redirects to `GET /google/oauth/callback`.
3. The API creates or finds the user by email (password is optional for Google-only accounts), stores a short-lived ticket, and redirects to `{FRONTEND_URL}/auth/google/callback?ticket=...`.
4. The UI posts the ticket to `POST /auth/google/ticket` and receives the same JWT payload as password login.

If that email already has a password account, Google sign-in logs into the existing user.

**Calendar**

| Method | Path | Description |
| --- | --- | --- |
| `GET` | `/google/oauth/status/` | `connected`, Google email, and whether OAuth is configured |
| `GET`/`POST` | `/google/oauth/connect/` | Returns `auth_url` (authenticated) |
| `GET` | `/google/oauth/callback` | Google redirect; stores calendar tokens or completes sign-in |

Calendar tokens are stored per user in `google_calendar_connections`. After connect, the UI is sent to `/meetings?google=connected`. `POST /meetings/check-availability/` uses those tokens against Google Calendar FreeBusy. Creating an online meeting uses the same connection to insert a calendar event and Meet link.

## Health

| Method | Path | Description |
| --- | --- | --- |
| `GET` | `/` | Welcome message |
| `GET` | `/health` | Health check |

## Current limitations

- Recording files use local disk, not cloud object storage (S3/MinIO).
- Speech-to-text labels every spoken line as `Speaker`. Speaker diarization is not implemented.
- Summaries quote transcript sentences. They do not generate new prose, decisions, or action items.
- `open_risks` on the dashboard is always `0`. Decisions and risks are not stored.
- Forgot password and `GET /me` are not implemented.
- SQLAlchemy `echo=True` logs SQL to the console. Turn that off for production.
