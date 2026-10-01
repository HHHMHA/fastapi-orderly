from fastapi_orderly.modules.auth.hasher import Hasher


class FakeHasher(Hasher):
    def hash(self, password: str) -> str:
        return password

    def verify(self, password: str, hashed: str) -> bool:
        return password == hashed
