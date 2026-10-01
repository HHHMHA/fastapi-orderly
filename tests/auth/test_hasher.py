import argon2
import pytest

from fastapi_orderly.modules.auth.hasher import get_hasher
from tests.utils import FakeHasher


def test_fake_hasher() -> None:
    hasher = FakeHasher()

    hashed = hasher.hash("password")

    assert hashed == "password"
    assert hasher.verify("password", hashed)
    assert not hasher.verify("wrong-password", hashed)


def test_hash_and_verify() -> None:
    hasher = get_hasher()

    hashed = hasher.hash("password")

    assert hashed != "password"
    assert hasher.verify("password", hashed)
    with pytest.raises(argon2.exceptions.VerifyMismatchError):
        hasher.verify("wrong-password", hashed)
