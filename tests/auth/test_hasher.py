from fastapi_orderly.modules.auth.hasher import get_hasher
from tests.utils import FakeHasher


def test_fake_hasher() -> None:
    hasher = FakeHasher()

    hashed = hasher.hash("password")

    assert hashed == "password"
    assert hasher.verify("password", hashed)
    assert not hasher.verify("wrong-password", hashed)

    assert hasher.dummy_hash == "dummy"
    assert hasher.hash_token("token") == "token"


def test_hash_and_verify() -> None:
    hasher = get_hasher()

    hashed = hasher.hash("password")

    assert hashed != "password"
    assert hasher.verify("password", hashed)
    assert hasher.verify("wrong-password", hashed) is False

    assert hasher.dummy_hash is not None
    assert hasher.hash_token("test") != "test"
