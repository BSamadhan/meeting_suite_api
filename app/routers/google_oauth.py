from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.schemas.ops import GoogleOAuthConnectResponse, GoogleOAuthStatusResponse
from app.services.google_oauth import (
    callback_error_redirect,
    handle_oauth_callback,
    oauth_connect,
    oauth_status,
    peek_oauth_purpose,
)

router = APIRouter(prefix="/google/oauth", tags=["Google OAuth"])


@router.get(
    "/status/",
    response_model=GoogleOAuthStatusResponse,
)
def get_google_oauth_status(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return oauth_status(db, current_user)


@router.get(
    "/connect/",
    response_model=GoogleOAuthConnectResponse,
)
@router.post(
    "/connect/",
    response_model=GoogleOAuthConnectResponse,
)
def connect_google_oauth(current_user: User = Depends(get_current_user)):
    return oauth_connect(current_user)


@router.get("/callback")
@router.get("/callback/", include_in_schema=False)
def google_oauth_callback(
    code: str | None = Query(default=None),
    state: str | None = Query(default=None),
    error: str | None = Query(default=None),
    db: Session = Depends(get_db),
):
    purpose = peek_oauth_purpose(state)
    try:
        if error:
            raise HTTPException(status_code=400, detail=error)
        if not code or not state:
            raise HTTPException(
                status_code=400,
                detail="Google OAuth callback is missing code or state.",
            )
        redirect_to = handle_oauth_callback(db, code, state)
        return RedirectResponse(url=redirect_to, status_code=302)
    except HTTPException as exc:
        detail = exc.detail if isinstance(exc.detail, str) else "Google OAuth failed."
        return RedirectResponse(
            url=callback_error_redirect(purpose, detail),
            status_code=302,
        )
    except Exception:
        return RedirectResponse(
            url=callback_error_redirect(purpose, "Google OAuth failed."),
            status_code=302,
        )
