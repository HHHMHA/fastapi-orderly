from fastapi_orderly.modules.otp.models import OneTimePassword
from fastapi_orderly.shared.mixins.reposotories import RepositoryBase


class OTPRepository(RepositoryBase[OneTimePassword]):
    Model = OneTimePassword
