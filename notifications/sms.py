import base64
import logging
import re
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from django.conf import settings
from django.utils.module_loading import import_string

logger = logging.getLogger(__name__)


def normalize_phone(raw):
    """Turn what a customer typed ("98765 43210", "09876543210") into +919876543210."""
    cleaned = re.sub(r"[^\d+]", "", raw or "")
    if cleaned.startswith("+"):
        return cleaned

    digits = cleaned.lstrip("0")
    if not digits:
        return ""

    country = settings.SMS_DEFAULT_COUNTRY_CODE
    if digits.startswith(country.lstrip("+")) and len(digits) > 10:
        return "+" + digits  # the country code was already typed
    return country + digits


class ConsoleSMSBackend:
    """Writes the message to the log instead of sending it (development and demos)."""

    def send(self, to, body):
        logger.info("SMS to %s: %s", to, body)
        return True


class TwilioSMSBackend:
    """
    Sends through Twilio's REST API using only the standard library.
    Needs TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN and TWILIO_FROM_NUMBER in the settings.
    Sending to India also needs DLT registration, so this is not tested against a live account.
    """

    def send(self, to, body):
        sid = settings.TWILIO_ACCOUNT_SID
        token = settings.TWILIO_AUTH_TOKEN
        data = urlencode({"To": to, "From": settings.TWILIO_FROM_NUMBER, "Body": body}).encode()

        request = Request(
            f"https://api.twilio.com/2010-04-01/Accounts/{sid}/Messages.json", data=data
        )
        credentials = base64.b64encode(f"{sid}:{token}".encode()).decode()
        request.add_header("Authorization", f"Basic {credentials}")

        with urlopen(request, timeout=10) as response:
            return 200 <= response.status < 300


def send_sms(to, body):
    """Send one SMS through the backend named in settings.SMS_BACKEND."""
    number = normalize_phone(to)
    if not number:
        logger.warning("No usable phone number; SMS skipped")
        return False
    backend = import_string(settings.SMS_BACKEND)()
    return backend.send(number, body)