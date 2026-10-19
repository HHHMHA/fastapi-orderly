from fastapi_orderly.modules.auth.dtos import UserContactInfo
from fastapi_orderly.modules.otp.notifications import OTPNotification


def test_otp_notification_renders_code() -> None:
    code = "12345"
    notification = OTPNotification(
        users=[UserContactInfo(email="test@gmail.com", username="username")],
        context={"code": code},
    )
    bodies = {n.body for n in notification.channel_options_tuple if hasattr(n, "body")}  # pyright: ignore[reportAttributeAccessIssue]
    assert all(code in body for body in bodies)
