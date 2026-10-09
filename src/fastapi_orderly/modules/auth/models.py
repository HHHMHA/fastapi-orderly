from sqlalchemy import ForeignKey, UniqueConstraint, false
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import LargeBinary, String

from fastapi_orderly.core.db.base import Base
from fastapi_orderly.core.db.mixins import ActivatorMixin, ModelsMixin


class UserAccount(ModelsMixin, ActivatorMixin, Base):
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


class UserPermissions(ModelsMixin, Base):
    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "perm_code",
            name="uq_user_permissions_user_id_per_code",
        ),
    )

    user_id: Mapped[int] = mapped_column(
        ForeignKey("user_account.id", ondelete="CASCADE"),
        nullable=False,
    )

    user: Mapped["UserAccount"] = relationship(
        "UserAccount",
        back_populates="permissions",
        lazy="noload",
    )
    perm_code: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )


class RefreshToken(ModelsMixin, Base):
    user_id: Mapped[int] = mapped_column(
        ForeignKey("user_account.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    token_hash: Mapped[bytes] = mapped_column(
        LargeBinary(32),
        unique=True,
        index=True,
    )

    user: Mapped["UserAccount"] = relationship(
        "UserAccount",
        lazy="noload",
    )
