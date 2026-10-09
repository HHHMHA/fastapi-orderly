from pydantic import BaseModel


class RegisterUserRequest(BaseModel):
    username: str
    password: str
    email: str


class UserContactInfo(BaseModel):
    username: str
    email: str
