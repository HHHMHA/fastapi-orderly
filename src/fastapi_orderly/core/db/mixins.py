from datetime import datetime
from typing import ClassVar

import sqlalchemy as sa
from sqlalchemy import DateTime, func
from sqlalchemy.orm import Mapped, declared_attr, mapped_column

from fastapi_orderly.core.db.permissions import PermissionAction, get_perm_code
from fastapi_orderly.shared.utils import camel_to_snake


class ModelsMixin:
    """define a series of common elements that may be applied to mapped
    classes using this class as a mixin class."""

    overridden_tablename: ClassVar[str | None] = None

    @declared_attr.directive
    def __tablename__(cls) -> str:
        if cls.overridden_tablename is not None:
            return cls.overridden_tablename
        return camel_to_snake(cls.__name__)  # type: ignore[attr-defined]

    id: Mapped[int] = mapped_column(primary_key=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    extra_permissions: ClassVar[tuple[str, ...]] = ()

    @classmethod
    def get_permissions(cls) -> tuple[str, ...]:
        """
        Returns a list of permissions for the model, based on the model's

        By default a model has all permissions for all actions. but can be
        overridden by setting `extra_permissions` on the model class.
        """

        actions = [action for action in PermissionAction]
        permissions_list = [get_perm_code(cls.__tablename__, action) for action in actions]
        if cls.extra_permissions:
            permissions_list.extend(cls.extra_permissions)
        return tuple(permissions_list)

    def __str__(self) -> str:
        return f"<Model {self.__tablename__} - id = {self.id}>"

    def __repr__(self) -> str:
        return f"<Model {self.__tablename__} - id = {self.id}>"


class ActivatorMixin:
    is_active: Mapped[bool] = mapped_column(server_default=sa.true())
