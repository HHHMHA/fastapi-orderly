import logging

import pytest

from fastapi_orderly.modules.notifications.channels.email.sender import LogEmailSender
from fastapi_orderly.modules.notifications.channels.email.utils import EmailAttachment


def test_log_email_sender_logs_basic_email(caplog: pytest.LogCaptureFixture) -> None:
    sender = LogEmailSender()

    with caplog.at_level(logging.INFO):
        sender.send_email(
            from_email="sender@example.com",
            recipients=["recipient@example.com"],
            subject="Test subject",
            body="Hello\nThis is a test.",
        )

    message = caplog.records[-1].message

    assert "EMAIL" in message
    assert "From:    sender@example.com" in message
    assert "To:      recipient@example.com" in message
    assert "Subject: Test subject" in message
    assert "Format:  Plain text" in message
    assert "Body:" in message
    assert "│ Hello" in message
    assert "│ This is a test." in message


def test_log_email_sender_logs_all_optional_fields(caplog: pytest.LogCaptureFixture) -> None:
    sender = LogEmailSender()

    attachment = EmailAttachment(
        filename="document.pdf",
        content=b"pdf-content",
        content_type="application/pdf",
    )

    with caplog.at_level(logging.INFO):
        sender.send_email(
            from_email="sender@example.com",
            recipients=[
                "first@example.com",
                "second@example.com",
            ],
            subject="Test subject",
            body="Hello\nWorld",
            cc=["cc@example.com"],
            bcc=["bcc@example.com"],
            reply_to="reply@example.com",
            html=True,
            attachments=[attachment],
        )

    message = caplog.records[-1].message

    assert "From:    sender@example.com" in message
    assert "To:      first@example.com, second@example.com" in message
    assert "Cc:      cc@example.com" in message
    assert "Bcc:     bcc@example.com" in message
    assert "Reply-To: reply@example.com" in message
    assert "Subject: Test subject" in message
    assert "Format:  HTML" in message
    assert "Attachments: 1" in message
    assert "document.pdf" in message
    assert "(application/pdf, 11 bytes)" in message
    assert "│ Hello" in message
    assert "│ World" in message


def test_log_email_sender_logs_multiple_attachments(caplog: pytest.LogCaptureFixture) -> None:
    sender = LogEmailSender()

    attachments = [
        EmailAttachment(
            filename="first.txt",
            content=b"123",
            content_type="text/plain",
        ),
        EmailAttachment(
            filename="second.json",
            content=b'{"test": true}',
            content_type="application/json",
        ),
    ]

    with caplog.at_level(logging.INFO):
        sender.send_email(
            from_email="sender@example.com",
            recipients=["recipient@example.com"],
            subject="Attachments",
            body="Test",
            attachments=attachments,
        )

    message = caplog.records[-1].message

    assert "Attachments: 2" in message
    assert "first.txt (text/plain, 3 bytes)" in message
    assert "second.json (application/json, 14 bytes)" in message


def test_log_email_sender_handles_empty_body(caplog: pytest.LogCaptureFixture) -> None:
    sender = LogEmailSender()

    with caplog.at_level(logging.INFO):
        sender.send_email(
            from_email="sender@example.com",
            recipients=["recipient@example.com"],
            subject="Empty body",
            body="",
        )

    message = caplog.records[-1].message

    assert "Subject: Empty body" in message
    assert "Body:" in message


def test_log_email_sender_does_not_log_absent_optional_fields(
    caplog: pytest.LogCaptureFixture,
) -> None:
    sender = LogEmailSender()

    with caplog.at_level(logging.INFO):
        sender.send_email(
            from_email="sender@example.com",
            recipients=["recipient@example.com"],
            subject="Test",
            body="Body",
        )

    message = caplog.records[-1].message

    assert "Cc:" not in message
    assert "Bcc:" not in message
    assert "Reply-To:" not in message
    assert "Attachments:" not in message
