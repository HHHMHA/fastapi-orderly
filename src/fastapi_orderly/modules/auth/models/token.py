import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKey, Uuid
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
        nullable=False,
        unique=True,
    )

    family_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        nullable=False,
        index=True,
    )

    is_used: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
    )

    user: Mapped["UserAccount"] = relationship(
        "UserAccount",
        lazy="noload",
        uselist=False,
    )
