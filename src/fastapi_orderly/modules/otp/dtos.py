from pydantic import BaseModel, EmailStr


class OTPResendRequest(BaseModel):
    email: EmailStr


class OTPCheckRequest(BaseModel):
    email: EmailStr
    code: str
