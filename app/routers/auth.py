# Auth routes (login)
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import (
    create_access_token,
    hash_password,
    verify_password,
    verify_refresh_token,
)
from app.database import get_db
from app.models.user import User
from app.schemas.ops import GoogleOAuthConnectResponse
from app.schemas.user import (
    GoogleTicketRequest,
    RefreshTokenRequest,
    TokenResponse,
    UserCreate,
    UserLogin,
    UserResponse,
)
from app.services.auth_tokens import issue_auth_tokens
from app.services.google_oauth import exchange_login_ticket, login_connect

router = APIRouter(
    prefix="/auth",
    tags=["Authentication"],
)

# User Create API
@router.post(
    "/register",
    response_model=UserResponse, 
    status_code=status.HTTP_201_CREATED
)
def register_user(
    user_data: UserCreate,
    db: Session = Depends(get_db)
): 
    #check whether email already exists
    existing_user = (
        db.query(User)
        .filter(User.email == user_data.email)
        .first()
    )
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered"
        )

    # Hash the password
    hashed_password = hash_password(
        user_data.password
    )

    # Create a new user instance
    new_user = User(
        name=user_data.name,
        email=user_data.email,
        password_hash=hashed_password
    )

    # Add the new user to the database
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return new_user

# Login API
@router.post(
    "/login",
    response_model=TokenResponse
)
def login_user(
    user_data: UserLogin,
    db: Session = Depends(get_db)
):
    # Find user
    user = db.query(User).filter(User.email == user_data.email).first()
    # User not found or password does not match
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )
    # Verify password
    if not user.password_hash:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="This account uses Google sign-in.",
        )
    if not verify_password(
        user_data.password,
        user.password_hash
    ): 
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )

    # Check ativate status
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is not active"
        )

    return issue_auth_tokens(user)

@router.get(
    "/google/",
    response_model=GoogleOAuthConnectResponse,
)
@router.get(
    "/google/connect/",
    response_model=GoogleOAuthConnectResponse,
    include_in_schema=False,
)
def get_google_login_url():
    return login_connect()


@router.post(
    "/google/ticket",
    response_model=TokenResponse,
)
@router.post(
    "/google/ticket/",
    response_model=TokenResponse,
    include_in_schema=False,
)
def exchange_google_login_ticket(
    payload: GoogleTicketRequest,
    db: Session = Depends(get_db),
):
    user = exchange_login_ticket(db, payload.ticket)
    return issue_auth_tokens(user)


# Refresh Token API
@router.post("/refresh")
def refresh_access_token(
    token_data: RefreshTokenRequest
):
    payload = verify_refresh_token(
        token_data.refresh_token
    )
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token"
        )

    user_id = payload.get("sub")
    email = payload.get("email")

    access_token = create_access_token(
        data={
            "sub" : user_id,
            "email": email       
        }
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES
    }