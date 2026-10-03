import json
from abc import abstractmethod
from datetime import datetime
from typing import Literal, Protocol, override

import pyseto
from pydantic import BaseModel, ConfigDict
from pyseto import Key, KeyInterface

from fastapi_orderly.core.config import Settings


class TokenClaims(BaseModel):
    model_config = ConfigDict(extra="forbid")

    sub: str
    exp: datetime
    iat: datetime
    jti: str
    iss: str | None = None
    aud: str | None = None
    typ: Literal["access", "refresh"]


class AuthTokenizer(Protocol):
    @abstractmethod
    def encode(self, payload: TokenClaims) -> bytes: ...

    @abstractmethod
    def decode(self, token: str) -> TokenClaims: ...


class PysetoTokenizer(AuthTokenizer):
    def __init__(self, settings: Settings) -> None:
        self._key: KeyInterface = Key.new(
            version=4,
            purpose="local",
            key=settings.secret_key.get_secret_value().encode("ascii"),
        )

    @override
    def encode(self, payload: TokenClaims) -> bytes:
        token = pyseto.encode(
            self._key,
            payload=payload.model_dump(mode="json"),
        )
        return token

    @override
    def decode(self, token: str | bytes) -> TokenClaims:
        decoded = pyseto.decode(self._key, token)

        payload = decoded.payload
        if not isinstance(payload, dict):
            payload = json.loads(payload.decode())

        return TokenClaims.model_validate(payload)
