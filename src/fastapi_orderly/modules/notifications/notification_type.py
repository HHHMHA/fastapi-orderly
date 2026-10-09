from dataclasses import dataclass
from typing import ClassVar

from fastapi_orderly.modules.auth.dtos import UserContactInfo
from fastapi_orderly.modules.notifications.channels.options import ChannelOptions


@dataclass
class NotificationType:
    users: list[UserContactInfo]
    slug: ClassVar[str] = ""
    title: ClassVar[str] = ""
    context: dict[str, object]  #  later we will see if we can have an actual type or something

    @property
    def channel_options_tuple(self) -> tuple[ChannelOptions, ...]:
        return ()
