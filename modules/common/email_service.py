# modules/common/email_service.py
import smtplib, ssl, logging
from email.message import EmailMessage
from typing import Iterable, Optional

logger = logging.getLogger(__name__)

class EmailService:
    def __init__(self, settings):
        self.s = settings

    def _as_msg(self, subject: str, to: Iterable[str], html: str, text: Optional[str] = None) -> EmailMessage:
        msg = EmailMessage()
        frm = f"{self.s.EMAIL_FROM_NAME} <{self.s.EMAIL_FROM or 'noreply@localhost'}>"
        msg["From"] = frm
        msg["To"] = ", ".join(to)
        msg["Subject"] = subject
        # both plain + html
        msg.set_content(text or " ")
        if html:
            msg.add_alternative(html, subtype="html")
        return msg

    def _send_smtp(self, msg: EmailMessage) -> bool:
        context = ssl.create_default_context()
        try:
            if self.s.EMAIL_USE_SSL:
                # Port 465 (SSL) — Tencent Exmail
                with smtplib.SMTP_SSL(self.s.EMAIL_HOST, self.s.EMAIL_PORT, context=context, timeout=20) as server:
                    if self.s.EMAIL_USERNAME:
                        server.login(self.s.EMAIL_USERNAME, self.s.EMAIL_PASSWORD)
                    server.send_message(msg)
            else:
                # Port 587 (STARTTLS)
                with smtplib.SMTP(self.s.EMAIL_HOST, self.s.EMAIL_PORT, timeout=20) as server:
                    if self.s.EMAIL_USE_TLS:
                        server.starttls(context=context)
                    if self.s.EMAIL_USERNAME:
                        server.login(self.s.EMAIL_USERNAME, self.s.EMAIL_PASSWORD)
                    server.send_message(msg)
            logger.info("[Email] Sent via SMTP: %s -> %s", msg["Subject"], msg["To"])
            return True
        except smtplib.SMTPException as e:
            # จับ error เคสยอดฮิตของ Exmail เช่น 530/550
            logger.exception("SMTP failed (%s): %s", e.__class__.__name__, e)
            return False
        except Exception as e:
            logger.exception("Unexpected email error: %s", e)
            return False

    def send(self, subject: str, to: Iterable[str], html: str, text: Optional[str] = None) -> bool:
        """Fail-safe: ไม่โยน exception ออกไปภายนอก"""
        if not self.s.EMAIL_ENABLED:
            logger.info("[Email] Suppressed (EMAIL_ENABLED=False): %s -> %s", subject, list(to))
            return False

        if (self.s.EMAIL_BACKEND or "").lower() == "console":
            logger.info("[Email console] SUBJECT: %s", subject)
            logger.info("[Email console] TO: %s", ", ".join(to))
            logger.info("[Email console] HTML:\n%s", html)
            if text:
                logger.info("[Email console] TEXT:\n%s", text)
            return True

        if not self.s.EMAIL_HOST or not self.s.EMAIL_PORT:
            logger.error("EMAIL_HOST/EMAIL_PORT not configured")
            return False

        if not self.s.EMAIL_FROM:
            logger.warning("EMAIL_FROM is empty, using noreply@localhost")

        # Exmail ควรให้ FROM ตรงกับ USERNAME
        if self.s.EMAIL_USERNAME and self.s.EMAIL_FROM and (self.s.EMAIL_USERNAME.lower() != self.s.EMAIL_FROM.lower()):
            logger.warning("EMAIL_FROM (%s) != EMAIL_USERNAME (%s). Tencent Exmail อาจปฏิเสธการส่ง",
                           self.s.EMAIL_FROM, self.s.EMAIL_USERNAME)

        msg = self._as_msg(subject, to, html, text)
        return self._send_smtp(msg)
