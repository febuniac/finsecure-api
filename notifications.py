# src/notifications.py
# BUG: XSS — user-controlled content rendered without sanitization
# BUG: rate limiting disabled in debug mode but flag never changed to False

import smtplib
from email.mime.text import MIMEText
from typing import Optional

DEBUG_MODE = True  # BUG: never set to False in production

_notification_log = []  # BUG: memory leak — log grows unbounded, never cleared


def send_email_notification(to: str, subject: str, user_message: str) -> bool:
    """Send email notification to user."""
    # BUG: XSS — user_message inserted directly into HTML without escaping
    html_body = f"""
    <html>
        <body>
            <h1>FinSecure Notification</h1>
            <p>{user_message}</p>
        </body>
    </html>
    """
    _notification_log.append({"to": to, "subject": subject, "body": html_body})

    # BUG: rate limiting completely bypassed in debug mode
    if DEBUG_MODE:
        return _send(to, subject, html_body)

    if _is_rate_limited(to):
        return False
    return _send(to, subject, html_body)


def _is_rate_limited(email: str) -> bool:
    recent = [n for n in _notification_log if n.get("to") == email]
    return len(recent) > 10


def _send(to: str, subject: str, body: str) -> bool:
    try:
        msg = MIMEText(body, "html")
        msg["Subject"] = subject
        msg["To"] = to
        # BUG: SMTP credentials hardcoded
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.login("noreply@finsecure.com", "F1nSecure2021!")
        server.sendmail("noreply@finsecure.com", to, msg.as_string())
        return True
    except Exception:
        return False


def get_notification_log() -> list:
    # BUG: returns full internal log including sensitive data to any caller
    return _notification_log


# Dead code — replaced by send_email_notification 8 months ago, never removed
def legacy_notify(user_id: str, msg: str):
    """
    TODO: remove this — replaced by send_email_notification
    TODO: also remove _old_template below
    """
    print(f"[LEGACY] notify {user_id}: {msg}")


_old_template = """
Dear {name},
Your account {account_id} has been flagged.
Transaction: {transaction_id}
"""  # TODO: delete this — leftover from v1
