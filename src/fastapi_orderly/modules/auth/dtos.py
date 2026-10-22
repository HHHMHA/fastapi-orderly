from pydantic import BaseModel, ConfigDict, EmailStr, SecretStr, field_validator


class RegisterUserRequest(BaseModel):
    username: str
    password: SecretStr
    email: EmailStr

    @field_validator("email", mode="after")
    @classmethod
    def normalize_email(cls, value: EmailStr) -> EmailStr:
        return str(value).strip().lower()


class UserContactInfo(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    username: str
    email: str


class UserDetailsResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    username: str
    email: EmailStr
    is_email_verified: bool


class LoginTokenResponse(BaseModel):
    access: str
    refresh: str
