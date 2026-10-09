from fastapi_orderly.modules.notifications.channels.base import NotificationChannel
from fastapi_orderly.modules.notifications.channels.options import ChannelType
from fastapi_orderly.modules.notifications.notification_type import NotificationType


class NotificationService:
    def __init__(self, channels: dict[ChannelType, NotificationChannel]) -> None:
        self._channels = channels

    def dispatch(self, notification: NotificationType) -> None:
        for channel_options in notification.channel_options_tuple:
            channel = self._channels.get(channel_options.channel_type)
            if channel:
                channel.send(notification, channel_options)
