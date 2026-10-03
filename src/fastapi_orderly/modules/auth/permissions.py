# while we can build a dynamic list of models, we'll use a static one
# for now to not build useless choices that will never be used
# maybe we can make it dynamic but with exclude choice later
from functools import lru_cache
from itertools import chain

from fastapi_orderly.core.db.mixins import ModelsMixin
from fastapi_orderly.core.db.registry import UserAccount


@lru_cache
def get_permission_models() -> tuple[type[ModelsMixin], ...]:
    return (UserAccount,)  # pragma: no cover


@lru_cache
def get_all_permissions() -> tuple[str, ...]:
    return (*chain.from_iterable(model.get_permissions() for model in get_permission_models()),)
