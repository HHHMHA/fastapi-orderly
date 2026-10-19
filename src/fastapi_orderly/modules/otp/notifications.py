from dataclasses import dataclass

from fastapi_orderly.core.config import get_settings
from fastapi_orderly.modules.notifications.channels.email.channel import EmailChannelOptions
from fastapi_orderly.modules.notifications.channels.options import ChannelOptions
from fastapi_orderly.modules.notifications.notification_type import NotificationType


@dataclass
class OTPNotification(NotificationType):
    slug = "otp-code"
    title = "Your otp code"

    @property
    def channel_options_tuple(self) -> tuple[ChannelOptions, ...]:
        settings = get_settings()
        # TODO: email template renderer
        template = "Your otp code is {code}"
        body = template.format(**self.context)
        return (EmailChannelOptions(from_email=settings.email.from_email, body=body),)
