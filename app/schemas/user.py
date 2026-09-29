# UserCreate, UserResponse, login schemas
from pydantic import BaseModel, EmailStr, Field, ConfigDict

# Create a new user
class UserCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    email: EmailStr
    password: str = Field(min_length=8, max_length=72)

# User response
class UserResponse(BaseModel):
    id: int
    name: str
    email: str

    model_config = ConfigDict(from_attributes=True)

# login user
class UserLogin(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=72)

# Refresh token request
class RefreshTokenRequest(BaseModel):
    refresh_token: str


class GoogleTicketRequest(BaseModel):
    ticket: str = Field(min_length=1, max_length=64)

# Token response
class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    refresh_token: str
    expires_in: int
    user: UserResponse | None = None
    

