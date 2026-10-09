from dataclasses import dataclass

import pytest

from fastapi_orderly.modules.auth.dtos import UserContactInfo
from fastapi_orderly.modules.notifications.channels.base import ChannelOptions
from fastapi_orderly.modules.notifications.channels.email.channel import (
    EmailChannel,
    EmailChannelOptions,
)
from fastapi_orderly.modules.notifications.channels.email.utils import EmailAttachment
from fastapi_orderly.modules.notifications.notification_type import NotificationType


@dataclass
class FakeNotificationType(NotificationType):
    slug = "fake-notification"
    title = "Fake notification"

    @property
    def channel_options_tuple(self) -> tuple[ChannelOptions, ...]:
        return (
            EmailChannelOptions(
                from_email="sender@example.com",
                body="Hello {{ username }}",
                cc=["cc@example.com"],
                bcc=["bcc@example.com"],
                reply_to="reply@example.com",
                html=True,
                attachments=[
                    EmailAttachment(
                        filename="test.txt",
                        content=b"test content",
                        content_type="text/plain",
                    )
                ],
            ),
        )


@dataclass
class SentEmail:
    from_email: str
    recipients: list[str]
    subject: str
    body: str
    cc: list[str] | None
    bcc: list[str] | None
    reply_to: str | None
    html: bool
    attachments: list[EmailAttachment] | None


class FakeEmailSender:
    def __init__(self) -> None:
        self.sent_emails: list[SentEmail] = []

    def send_email(
        self,
        *,
        from_email: str,
        recipients: list[str],
        subject: str,
        body: str,
        cc: list[str] | None = None,
        bcc: list[str] | None = None,
        reply_to: str | None = None,
        html: bool = False,
        attachments: list[EmailAttachment] | None = None,
    ) -> None:
        self.sent_emails.append(
            SentEmail(
                from_email=from_email,
                recipients=recipients,
                subject=subject,
                body=body,
                cc=cc,
                bcc=bcc,
                reply_to=reply_to,
                html=html,
                attachments=attachments,
            )
        )


@pytest.fixture
def fake_notification() -> FakeNotificationType:
    return FakeNotificationType(
        users=[
            UserContactInfo(email="first@example.com", username="test1"),
            UserContactInfo(email="second@example.com", username="test2"),
        ],
        context={"username": "Test User"},
    )


@pytest.fixture
def fake_sender() -> FakeEmailSender:
    return FakeEmailSender()


@pytest.fixture
def email_channel(fake_sender: FakeEmailSender) -> EmailChannel:
    return EmailChannel(sender=fake_sender)


def test_send_email(
    email_channel: EmailChannel,
    fake_sender: FakeEmailSender,
    fake_notification: FakeNotificationType,
) -> None:
    email_options = fake_notification.channel_options_tuple[0]

    email_channel.send(fake_notification, email_options)

    assert len(fake_sender.sent_emails) == 1

    sent_email = fake_sender.sent_emails[0]

    assert sent_email.from_email == "sender@example.com"
    assert sent_email.recipients == [
        "first@example.com",
        "second@example.com",
    ]
    assert sent_email.subject == "Fake notification"
    assert sent_email.body == "Hello {{ username }}"
    assert sent_email.cc == ["cc@example.com"]
    assert sent_email.bcc == ["bcc@example.com"]
    assert sent_email.reply_to == "reply@example.com"
    assert sent_email.html is True
    assert sent_email.attachments == [
        EmailAttachment(
            filename="test.txt",
            content=b"test content",
            content_type="text/plain",
        )
    ]


def test_send_email_with_default_options(
    email_channel: EmailChannel,
    fake_sender: FakeEmailSender,
    fake_notification: FakeNotificationType,
) -> None:
    options = EmailChannelOptions(
        from_email="sender@example.com",
        body="Hello",
    )

    email_channel.send(fake_notification, options)

    sent_email = fake_sender.sent_emails[0]

    assert sent_email.from_email == "sender@example.com"
    assert sent_email.recipients == [
        "first@example.com",
        "second@example.com",
    ]
    assert sent_email.subject == "Fake notification"
    assert sent_email.body == "Hello"
    assert sent_email.cc is None
    assert sent_email.bcc is None
    assert sent_email.reply_to is None
    assert sent_email.html is False
    assert sent_email.attachments is None


def test_send_rejects_invalid_options(
    email_channel: EmailChannel,
    fake_notification: FakeNotificationType,
) -> None:
    invalid_options = ChannelOptions()

    with pytest.raises(ValueError, match="Invalid options for EmailChannel"):
        email_channel.send(fake_notification, invalid_options)
