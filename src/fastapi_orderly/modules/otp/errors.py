from fastapi import status

from fastapi_orderly.core.errors import BaseAPIError


class OTPRateLimitError(BaseAPIError):
    def __init__(
        self,
        *,
        retry_after: str,
    ) -> None:
        super().__init__(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=retry_after,
        )


class OTPCodeInvalidError(BaseAPIError):
    def __init__(
        self,
    ) -> None:
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="OTP Code is invalid",
        )
