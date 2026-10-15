from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import String

from fastapi_orderly.core.db.base import Base
from fastapi_orderly.core.db.mixins import ModelsMixin

if TYPE_CHECKING:
    from fastapi_orderly.modules.auth.models import UserAccount


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
