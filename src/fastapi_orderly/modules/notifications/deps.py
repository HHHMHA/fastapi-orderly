from typing import Annotated

from fastapi import Depends

from fastapi_orderly.core.config import Environment, Settings, get_settings
from fastapi_orderly.modules.notifications.channels.base import NotificationChannel
from fastapi_orderly.modules.notifications.channels.email.channel import EmailChannel
from fastapi_orderly.modules.notifications.channels.email.sender import EmailSender, LogEmailSender
from fastapi_orderly.modules.notifications.channels.options import ChannelType
from fastapi_orderly.modules.notifications.services import NotificationService


def get_email_sender(
    settings: Annotated[Settings, Depends(get_settings)],
) -> EmailSender:
    match settings.environment:
        case Environment.LOCAL:
            return LogEmailSender()
        case Environment.PRODUCTION:
            return LogEmailSender()
        case _:
            return LogEmailSender()


def get_default_channels(
    email_sender: Annotated[EmailSender, Depends(get_email_sender)],
) -> dict[ChannelType, NotificationChannel]:
    return {
        ChannelType.EMAIL: EmailChannel(
            sender=email_sender,
        ),
    }


def get_notification_service(
    channels: Annotated[dict[ChannelType, NotificationChannel], Depends(get_default_channels)],
) -> NotificationService:
    return NotificationService(channels)
