import logging
from typing import Protocol

from fastapi_orderly.modules.notifications.channels.email.utils import EmailAttachment

logger = logging.getLogger("email")


class EmailSender(Protocol):
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
    ) -> None: ...


class LogEmailSender(EmailSender):
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
        lines = [
            "",
            "╭──────────────────────────────────────────────╮",
            "│                  EMAIL                       │",
            "├──────────────────────────────────────────────┤",
            f"│ From:    {from_email}",
            f"│ To:      {', '.join(recipients)}",
        ]

        if cc:
            lines.append(f"│ Cc:      {', '.join(cc)}")

        if bcc:
            lines.append(f"│ Bcc:     {', '.join(bcc)}")

        if reply_to:
            lines.append(f"│ Reply-To: {reply_to}")

        lines.extend(
            [
                f"│ Subject: {subject}",
                f"│ Format:  {'HTML' if html else 'Plain text'}",
            ]
        )

        if attachments:
            lines.append(f"│ Attachments: {len(attachments)}")
            for attachment in attachments:
                lines.append(
                    f"│   - {attachment.filename} "
                    f"({attachment.content_type}, {len(attachment.content):,} bytes)"
                )

        lines.extend(
            [
                "├──────────────────────────────────────────────┤",
                "│ Body:",
            ]
        )

        lines.extend(f"│ {line}" for line in body.splitlines())

        lines.extend(
            [
                "╰──────────────────────────────────────────────╯",
                "",
            ]
        )

        logger.info("\n%s", "\n".join(lines))
