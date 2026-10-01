from datetime import UTC, datetime, timedelta

from fastapi_orderly.core.config import get_settings
from fastapi_orderly.modules.auth.deps import get_tokenizer
from fastapi_orderly.modules.auth.token import TokenClaims


class TestTokenizer:
    tokenizer = get_tokenizer(settings=get_settings())

    def test_encode_decode(self) -> None:
        now = datetime.now(UTC)
        claims = TokenClaims(
            sub="1",
            exp=now + timedelta(minutes=15),
            iat=now,
            jti="550e8400-e29b-41d4-a716-446655440000",
            iss="my-auth-service",
            aud="my-api",
            typ="access",
        )

        token = self.tokenizer.encode(claims)

        assert isinstance(token, bytes)
        assert token.startswith(
            b"v4.local."
        )  # this makes the test dependant on the specific token format

        decoded = self.tokenizer.decode(token)

        assert decoded == claims
