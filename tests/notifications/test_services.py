from dataclasses import dataclass

from fastapi_orderly.modules.auth.dtos import UserContactInfo
from fastapi_orderly.modules.notifications.channels.base import (
    ChannelOptions,
)
from fastapi_orderly.modules.notifications.channels.email.channel import (
    EmailChannelOptions,
)
from fastapi_orderly.modules.notifications.channels.options import ChannelType
from fastapi_orderly.modules.notifications.notification_type import NotificationType
from fastapi_orderly.modules.notifications.services import NotificationService


@dataclass
class FakeNotificationType(NotificationType):
    slug = "fake-notification"
    title = "Fake notification"

    @property
    def channel_options_tuple(self) -> tuple[ChannelOptions, ...]:
        return (
            EmailChannelOptions(
                from_email="sender@example.com",
                body="Hello",
            ),
        )


class FakeNotificationChannel:
    def __init__(self) -> None:
        self.calls: list[tuple[NotificationType, ChannelOptions]] = []

    def send(
        self,
        notification_type: NotificationType,
        options: ChannelOptions,
    ) -> None:
        self.calls.append((notification_type, options))


def test_dispatch_sends_notification_to_matching_channel() -> None:
    email_channel = FakeNotificationChannel()

    service = NotificationService(
        channels={
            ChannelType.EMAIL: email_channel,
        }
    )

    notification = FakeNotificationType(
        users=[UserContactInfo(email="test@example.com", username="test1")],
        context={},
    )

    service.dispatch(notification)

    assert len(email_channel.calls) == 1

    sent_notification, options = email_channel.calls[0]

    assert sent_notification is notification
    assert isinstance(options, EmailChannelOptions)
    assert options.from_email == "sender@example.com"
    assert options.body == "Hello"

    assert NotificationType([], {}).channel_options_tuple == ()


def test_dispatch_does_nothing_when_channel_is_not_registered() -> None:
    service = NotificationService(channels={})

    notification = FakeNotificationType(
        users=[UserContactInfo(email="test@example.com", username="test1")],
        context={},
    )

    service.dispatch(notification)


def test_dispatch_does_nothing_when_notification_has_no_channels() -> None:
    class EmptyNotificationType(NotificationType):
        slug = "empty"
        title = "Empty"

        @property
        def channel_options_tuple(self) -> tuple[ChannelOptions, ...]:
            return ()

    service = NotificationService(channels={})

    notification = EmptyNotificationType(
        users=[UserContactInfo(email="test@example.com", username="test1")],
        context={},
    )

    service.dispatch(notification)
