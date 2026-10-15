from typing import TYPE_CHECKING

from sqlalchemy import false
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import String

from fastapi_orderly.core.db.base import ActivatableBase
from fastapi_orderly.core.db.mixins import ModelsMixin

if TYPE_CHECKING:
    from fastapi_orderly.modules.auth.models import UserPermissions
    from fastapi_orderly.modules.otp.models import OneTimePassword


class UserAccount(ModelsMixin, ActivatableBase):
    overridden_tablename = "user_account"

    username: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    email: Mapped[str] = mapped_column(
        String(320),
        unique=True,
        index=True,
    )
    password: Mapped[str] = mapped_column()
    permissions: Mapped[list["UserPermissions"]] = relationship(
        "UserPermissions",
        back_populates="user",
        cascade="all, delete-orphan",
        passive_deletes=True,
        lazy="selectin",
    )
    is_admin: Mapped[bool] = mapped_column(
        server_default=false()
    )  # faster than 2 db queries for permissions
    is_email_verified: Mapped[bool] = mapped_column(server_default=false())
    otp: Mapped["OneTimePassword | None"] = relationship(
        "OneTimePassword",
        back_populates="user",
        lazy="raise",
        uselist=False,
    )
