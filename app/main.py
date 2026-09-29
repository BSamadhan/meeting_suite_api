# FastAPI entrypoint (app creation, CORS, routers)
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.core.config import settings
from app.database import engine, Base
from app.models import (  # noqa: F401
    GoogleCalendarConnection,
    GoogleLoginTicket,
    MeetingAction,
    MeetingAiMessage,
    MeetingDecision,
    MeetingRecording,
    MeetingRisk,
    MeetingSummary,
    Notification,
    MeetingTranscriptSegment,
)
from app.routers import (
    action_items,
    actions,
    auth,
    chat,
    dashboard,
    google_oauth,
    lookups,
    meetings,
    notifications,
    participants,
    recordings,
    summaries,
    transcripts,
    users,
)
from app.services.object_storage import storage_root

app = FastAPI(title="Meeting Suite API", version="0.1.0")

Base.metadata.create_all(bind=engine)

origins = [
    "http://localhost:3000",
    "http://localhost:5000",
    "http://localhost:5173",
    "http://localhost:5174",
    "http://127.0.0.1:5000",
    "http://127.0.0.1:5002",
    "http://127.0.0.1:5173",
    "http://127.0.0.1:5174",
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    allow_private_network=True,
)

app.include_router(auth.router)
app.include_router(dashboard.router, prefix="/dashboard")
app.include_router(users.router)
app.include_router(meetings.router, prefix="/meetings", tags=["Meetings"])
app.include_router(meetings.router, prefix="/meeting", tags=["Meetings"])
app.include_router(recordings.router, prefix="/meetings", tags=["Recordings"])
app.include_router(recordings.router, prefix="/meeting", tags=["Recordings"])
app.include_router(transcripts.router, prefix="/meetings", tags=["Transcript"])
app.include_router(transcripts.router, prefix="/meeting", tags=["Transcript"])
app.include_router(summaries.router, prefix="/meetings", tags=["Summary"])
app.include_router(summaries.router, prefix="/meeting", tags=["Summary"])
app.include_router(chat.router, prefix="/meetings", tags=["Chat"])
app.include_router(chat.router, prefix="/meeting", tags=["Chat"])
app.include_router(participants.router, prefix="/meetings", tags=["Participants"])
app.include_router(participants.router, prefix="/meeting", tags=["Participants"])
app.include_router(actions.router)
app.include_router(action_items.router)
app.include_router(lookups.router)
app.include_router(notifications.router)
app.include_router(google_oauth.router)


@app.get("/")
async def root():
    return {"message": "Welcome to the Meeting Suite API"}


@app.get("/health")
async def health_check():
    return {"status": "healthy"}


app.mount(
    settings.STORAGE_PUBLIC_BASE_URL or "/files",
    StaticFiles(directory=storage_root()),
    name="recording-files",
)
