from dataclasses import dataclass
from enum import StrEnum
from typing import ClassVar


class ChannelType(StrEnum):
    EMAIL = "email"


@dataclass(frozen=True)
class ChannelOptions:
    channel_type: ClassVar[ChannelType]
