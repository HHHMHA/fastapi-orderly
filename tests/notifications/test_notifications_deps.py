from typing import cast
from unittest.mock import Mock

import pytest

from fastapi_orderly.core.config import get_settings
from fastapi_orderly.modules.notifications.channels.base import NotificationChannel
from fastapi_orderly.modules.notifications.channels.email.channel import EmailChannel
from fastapi_orderly.modules.notifications.channels.email.sender import (
    EmailSender,
    LogEmailSender,
)
from fastapi_orderly.modules.notifications.channels.options import ChannelType
from fastapi_orderly.modules.notifications.deps import (
    get_default_channels,
    get_email_sender,
    get_notification_service,
)
from fastapi_orderly.modules.notifications.services import NotificationService


def test_get_email_sender_returns_log_sender(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ENVIRONMENT", "prod")
    get_settings.cache_clear()
    settings = get_settings()

    sender = get_email_sender(settings)

    assert isinstance(sender, LogEmailSender)

    monkeypatch.setenv("ENVIRONMENT", "local")
    get_settings.cache_clear()
    settings = get_settings()

    sender = get_email_sender(settings)

    assert isinstance(sender, LogEmailSender)

    monkeypatch.setenv("ENVIRONMENT", "test")
    get_settings.cache_clear()
    settings = get_settings()

    sender = get_email_sender(settings)

    assert isinstance(sender, LogEmailSender)


def test_get_default_channels_configures_email_channel() -> None:
    sender = Mock()

    channels = get_default_channels(sender)

    assert list(channels) == [ChannelType.EMAIL]
    assert isinstance(channels[ChannelType.EMAIL], EmailChannel)


def test_get_default_channels_uses_provided_sender() -> None:
    sender = Mock()

    channels = get_default_channels(sender)
    email_channel = cast(EmailChannel, channels[ChannelType.EMAIL])
    assert email_channel.sender is sender


def test_get_notification_service_uses_provided_channels() -> None:
    channels: dict[ChannelType, NotificationChannel] = {
        ChannelType.EMAIL: EmailChannel(sender=Mock(spec=EmailSender)),
    }

    service = get_notification_service(channels)

    assert isinstance(service, NotificationService)
    assert service._channels is channels
