from abc import abstractmethod
from typing import Protocol, override

from argon2 import PasswordHasher


class Hasher(Protocol):
    @abstractmethod
    def hash(self, password: str) -> str: ...

    @abstractmethod
    def verify(self, password: str, hashed: str) -> bool: ...


class Argon2Hasher(Hasher):
    def __init__(self) -> None:
        self._hasher = PasswordHasher()

    @override
    def hash(self, password: str) -> str:
        return self._hasher.hash(password)

    @override
    def verify(self, password: str, hashed: str) -> bool:
        return self._hasher.verify(hashed, password)


def get_hasher() -> Hasher:
    return Argon2Hasher()
