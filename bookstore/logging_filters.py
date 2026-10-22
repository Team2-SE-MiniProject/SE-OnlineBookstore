import logging
import re

# Order matters: the Bearer rule must run before the key=value rule.
PATTERNS = [
    (re.compile(r"(?i)\bBearer\s+[\w.~+/=-]+"), "Bearer [REDACTED]"),
    (
        re.compile(
            r"(?i)\b(password|passwd|token|secret|api[_-]?key|authorization)"
            r"([\"']?\s*[:=]\s*[\"']?)([^\s,;&'\"}]+)"
        ),
        r"\1\2[REDACTED]",
    ),
    (re.compile(r"\b(?:\d[ -]?){13,19}\b"), "[REDACTED CARD]"),
]


def redact(text):
    for pattern, replacement in PATTERNS:
        text = pattern.sub(replacement, text)
    return text


class SensitiveDataFilter(logging.Filter):
    """Removes passwords, tokens and card numbers from log output (SAD 4.4)."""

    def filter(self, record):
        record.msg = redact(record.getMessage())
        record.args = ()
        if record.exc_info and record.exc_info[0]:
            record.exc_text = redact(logging.Formatter().formatException(record.exc_info))
        return True