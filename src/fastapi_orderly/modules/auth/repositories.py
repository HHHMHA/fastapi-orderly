from fastapi_orderly.modules.auth.models import UserAccount
from fastapi_orderly.shared.mixins.reposotories import RepositoryBase


class UserRepository(RepositoryBase[UserAccount]):
    Model: type[UserAccount] = UserAccount
