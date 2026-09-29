from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import String

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
