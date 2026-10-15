from pydantic.main import BaseModel


class AuthSettings(BaseModel):
    otp_expire_time_seconds: int = 300
    otp_length: int = 6
