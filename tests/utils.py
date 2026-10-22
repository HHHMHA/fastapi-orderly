from typing import override

from fastapi_orderly.modules.auth.hasher import Hasher


class FakeHasher(Hasher):
    @override
    def hash(self, password: str) -> str:
        return password

    @override
    def verify(self, password: str, hashed: str) -> bool:
        return password == hashed

    @property
    @override
    def dummy_hash(self) -> str:
        return "dummy"

    @override
    def hash_token(self, token: str) -> str:
        return token
