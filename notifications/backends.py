from django.core.mail.backends.console import EmailBackend as ConsoleEmailBackend


class ReadableConsoleEmailBackend(ConsoleEmailBackend):
    """
    Like Django's console email backend, but the body is printed as plain text.
    The standard one wraps long lines (a trailing "="), which breaks links when copied.
    """

    def write_message(self, message):
        self.stream.write(
            "\n"
            f"----- EMAIL to {', '.join(message.to)} -----\n"
            f"Subject: {message.subject}\n\n"
            f"{message.body}\n"
            "----- end of email -----\n"
        )