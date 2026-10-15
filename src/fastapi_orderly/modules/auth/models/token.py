from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import LargeBinary

from fastapi_orderly.core.db.base import Base
from fastapi_orderly.core.db.mixins import ModelsMixin

if TYPE_CHECKING:
    from fastapi_orderly.modules.auth.models import UserAccount


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
        uselist=False,
    )
