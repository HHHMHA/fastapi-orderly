from pydantic import BaseModel


class EmailSettings(BaseModel):
    from_email: str
