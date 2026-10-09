from dataclasses import dataclass

from fastapi_orderly.modules.notifications.channels.base import (
    NotificationChannel,
)
from fastapi_orderly.modules.notifications.channels.email.sender import EmailSender
from fastapi_orderly.modules.notifications.channels.email.utils import EmailAttachment
from fastapi_orderly.modules.notifications.channels.options import ChannelOptions, ChannelType
from fastapi_orderly.modules.notifications.notification_type import NotificationType


@dataclass(frozen=True)
class EmailChannelOptions(ChannelOptions):
    channel_type = ChannelType.EMAIL
    from_email: str
    body: str  # must be filled from dev using a template, string and then add the context to it
    cc: list[str] | None = None
    bcc: list[str] | None = None
    reply_to: str | None = None
    html: bool = False
    attachments: list[EmailAttachment] | None = None


class EmailChannel(NotificationChannel):
    def __init__(self, sender: EmailSender) -> None:
        self.sender = sender

    def send(self, notification_type: NotificationType, options: ChannelOptions) -> None:
        if not isinstance(options, EmailChannelOptions):
            raise ValueError("Invalid options for EmailChannel")

        email_options: EmailChannelOptions = options

        # TODO: add rest of options
        self.sender.send_email(
            from_email=email_options.from_email,
            recipients=[user.email for user in notification_type.users],
            subject=notification_type.title,
            body=email_options.body,
            attachments=email_options.attachments,
            html=email_options.html,
            cc=email_options.cc,
            bcc=email_options.bcc,
            reply_to=email_options.reply_to,
        )
