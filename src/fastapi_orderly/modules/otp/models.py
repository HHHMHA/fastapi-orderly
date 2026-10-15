from datetime import datetime

from sqlalchemy import DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.schema import ForeignKey

from fastapi_orderly.core.db.base import Base
from fastapi_orderly.core.db.mixins import ModelsMixin
from fastapi_orderly.modules.auth.models.user import UserAccount


class OneTimePassword(ModelsMixin, Base):
    user_id: Mapped[int] = mapped_column(
        ForeignKey("user_account.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        unique=True,
    )
    user: Mapped["UserAccount"] = relationship(
        "UserAccount",
        back_populates="otp",
        lazy="raise",
    )
    code_hash: Mapped[str] = mapped_column(nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
