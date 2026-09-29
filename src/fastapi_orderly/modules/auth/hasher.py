from functools import lru_cache
from typing import Annotated, Protocol

from argon2 import PasswordHasher
from fastapi import Depends

from fastapi_orderly.core.config import Environment, Settings, get_settings


class Hasher(Protocol):
    def hash(self, password: str) -> str: ...

    def verify(self, password: str, hashed: str) -> bool: ...


class FakeHasher:
    def hash(self, password: str) -> str:
        return password

    def verify(self, password: str, hashed: str) -> bool:
        return password == hashed


class Argon2Hasher:
    def __init__(self) -> None:
        self._hasher = PasswordHasher()

    def hash(self, password: str) -> str:
        return self._hasher.hash(password)

    def verify(self, password: str, hashed: str) -> bool:
        return self._hasher.verify(hashed, password)


@lru_cache(maxsize=1)
def get_hasher(settings: Annotated[Settings, Depends(get_settings)]) -> Hasher:
    # No need to test the hashing algo, only that it calls the hasher.
    if settings.environment == Environment.TEST:
        return FakeHasher()

    return Argon2Hasher()
