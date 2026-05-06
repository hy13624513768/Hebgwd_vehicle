from pydantic import BaseModel, Field


class SliderStartResponse(BaseModel):
    session_id: str


class SliderCompleteRequest(BaseModel):
    session_id: str = Field(min_length=8, max_length=128)


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1, max_length=128)
    slider_session_id: str = Field(min_length=8, max_length=128)


class UserInfo(BaseModel):
    id: int
    username: str
    display_name: str
    role: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserInfo
