from fastapi import status

from fastapi_orderly.core.errors import BaseAPIError


class UserAlreadyRegisteredError(BaseAPIError):
    def __init__(
        self,
        *,
        email: str | None = None,
        username: str | None = None,
    ) -> None:
        if email is not None:
            detail = "A user with this email is already registered."
        elif username is not None:
            detail = "A user with this username is already registered."
        else:
            raise ValueError("Either email or username must be provided.")

        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            detail=detail,
        )
