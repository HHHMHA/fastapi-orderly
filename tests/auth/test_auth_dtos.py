import pytest
from pydantic import SecretStr

from fastapi_orderly.modules.auth.dtos import RegisterUserRequest


@pytest.mark.parametrize(
    ("email", "expected"),
    [
        ("Test@Example.COM", "test@example.com"),
        ("  Test@Example.COM  ", "test@example.com"),
        ("USER@DOMAIN.ORG", "user@domain.org"),
    ],
)
def test_normalize_email(email: str, expected: str) -> None:
    request = RegisterUserRequest(
        username="testuser",
        password=SecretStr("secure-password"),
        email=email,
    )

    assert request.email == expected
