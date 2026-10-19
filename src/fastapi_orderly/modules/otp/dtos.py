from pydantic import BaseModel, EmailStr


class OTPResendRequest(BaseModel):
    email: EmailStr
