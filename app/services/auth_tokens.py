from app.core.config import settings
from app.core.security import create_access_token, create_refresh_token
from app.models.user import User


def issue_auth_tokens(user: User) -> dict:
    access_token = create_access_token(
        data={
            "sub": str(user.id),
            "email": user.email,
        }
    )
    refresh_token = create_refresh_token(
        data={
            "sub": str(user.id),
            "email": user.email,
        }
    )
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "refresh_token": refresh_token,
        "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        "user": user,
    }
