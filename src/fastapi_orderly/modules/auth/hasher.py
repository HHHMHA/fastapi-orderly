from abc import abstractmethod
from hashlib import sha256
from typing import Protocol, override

from argon2 import PasswordHasher
from argon2.exceptions import (
    InvalidHashError,
    VerificationError,
    VerifyMismatchError,
)


class Hasher(Protocol):
    @property
    def dummy_hash(self) -> str: ...

    @abstractmethod
    def hash(self, password: str) -> str: ...

    @abstractmethod
    def verify(self, password: str, hashed: str) -> bool: ...

    @abstractmethod
    def hash_token(self, token: str) -> str: ...


class Argon2Hasher(Hasher):
    def __init__(self) -> None:
        self._hasher = PasswordHasher()
        # Generate once per instance, not on every failed login.
        self._dummy_hash = self._hasher.hash("dummy-password-never-valid-for-login")

    @property
    @override
    def dummy_hash(self) -> str:
        return self._dummy_hash

    @override
    def hash(self, password: str) -> str:
        return self._hasher.hash(password)

    @override
    def verify(self, password: str, hashed: str) -> bool:
        try:
            return self._hasher.verify(hashed, password)
        except (
            VerifyMismatchError,
            VerificationError,
            InvalidHashError,
        ):
            return False

    @override
    def hash_token(self, token: str) -> str:
        return sha256(token.encode("utf-8")).hexdigest()


def get_hasher() -> Hasher:
    return Argon2Hasher()
