from abc import abstractmethod
from typing import Protocol

from fastapi_orderly.modules.notifications.channels.options import ChannelOptions
from fastapi_orderly.modules.notifications.notification_type import NotificationType


class NotificationChannel(Protocol):
    @abstractmethod
    def send(
        self,
        notification_type: NotificationType,
        options: ChannelOptions,
    ) -> None: ...
