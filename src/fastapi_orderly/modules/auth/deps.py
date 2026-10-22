from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from fastapi_orderly.core.config import Settings, get_settings
from fastapi_orderly.core.db.session import get_session
from fastapi_orderly.modules.auth.hasher import Hasher, get_hasher
from fastapi_orderly.modules.auth.repositories import RefreshTokenRepository, UserRepository
from fastapi_orderly.modules.auth.services import AuthenticationService, UserService
from fastapi_orderly.modules.auth.token import AuthTokenizer, PysetoTokenizer
from fastapi_orderly.modules.otp.deps import get_otp_service
from fastapi_orderly.modules.otp.services import OTPService


def get_tokenizer(
    settings: Annotated[Settings, Depends(get_settings)],
) -> PysetoTokenizer:
    return PysetoTokenizer(settings)


def get_user_repository(session: Annotated[AsyncSession, Depends(get_session)]) -> UserRepository:
    return UserRepository(session=session)


def get_refresh_token_repository(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> RefreshTokenRepository:
    return RefreshTokenRepository(session=session)


def get_user_service(
    user_repository: Annotated[UserRepository, Depends(get_user_repository)],
    hasher: Annotated[Hasher, Depends(get_hasher)],
    otp_service: Annotated[OTPService, Depends(get_otp_service)],
) -> UserService:
    return UserService(
        user_repository=user_repository,
        hasher=hasher,
        otp_service=otp_service,
    )


def get_authentication_service(
    user_repository: Annotated[UserRepository, Depends(get_user_repository)],
    refresh_token_repository: Annotated[
        RefreshTokenRepository, Depends(get_refresh_token_repository)
    ],
    hasher: Annotated[Hasher, Depends(get_hasher)],
    tokenizer: Annotated[AuthTokenizer, Depends(get_tokenizer)],
) -> AuthenticationService:
    return AuthenticationService(
        user_repository=user_repository,
        refresh_token_repository=refresh_token_repository,
        hasher=hasher,
        tokenizer=tokenizer,
    )
