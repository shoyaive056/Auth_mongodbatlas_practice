from html import escape


def _wrap(title: str, intro: str, button_text: str, link: str, footer: str) -> tuple[str, str]:
    text = f"{title}\n\n{intro}\n\n{button_text}: {link}\n\n{footer}\n"
    html = f"""\
<div style="font-family:Arial,sans-serif;max-width:480px;margin:auto;padding:24px;color:#1f2937">
  <h2 style="margin-top:0">{escape(title)}</h2>
  <p>{escape(intro)}</p>
  <p><a href="{escape(link)}" style="display:inline-block;background:#4f46e5;color:#fff;
     padding:12px 20px;border-radius:8px;text-decoration:none">{escape(button_text)}</a></p>
  <p style="font-size:13px;color:#6b7280">If the button does not work, copy this link:<br>{escape(link)}</p>
  <p style="font-size:13px;color:#6b7280">{escape(footer)}</p>
</div>"""
    return text, html


def verification_email(first_name: str, link: str, minutes: int) -> tuple[str, str, str]:
    subject = "Verify your email address"
    text, html = _wrap(
        "Confirm your email",
        f"Hi {first_name}, thanks for signing up. Please confirm your email address (link valid for {minutes} minutes).",
        "Verify email",
        link,
        "If you did not create this account, you can ignore this email.",
    )
    return subject, text, html


def password_reset_email(first_name: str, link: str, minutes: int) -> tuple[str, str, str]:
    subject = "Reset your password"
    text, html = _wrap(
        "Reset your password",
        f"Hi {first_name}, we received a request to reset your password (link valid for {minutes} minutes, one use).",
        "Reset password",
        link,
        "If you did not ask for this, you can ignore this email; your password will not change.",
    )
    return subject, text, html
