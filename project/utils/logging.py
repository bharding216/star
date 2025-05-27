import logging
import os
import traceback
from logging import LogRecord
from logging.config import dictConfig
import typing as t
from flask import session, request, current_app
from flask_login import current_user
from flask_mail import Mail, Message

from project.enums.app_mode import AppMode
from project.utils.logging_filters import (
    NoEmailLogsFilter,
    ExcludeStaticAssets,
)

# LOGGING LEVELS:
# DEBUG (10): Detailed information, typically of interest only when diagnosing problems.
# INFO (20): Confirmation that things are working as expected.
# WARNING (30): An indication that something unexpected happened, or indicative of some problem in the near future (e.g., 'disk space low'). The software is still working as expected.
# ERROR (40): Due to a more serious problem, the software has not been able to perform some function.
# CRITICAL (50): A very serious error, indicating that the program itself may be unable to continue running.

# To include the user_id in the logs, do this:
# current_app.logger.error("There was an error", extra={'user_id': '12345'})

client_name = os.getenv('CLIENT_NAME')
if client_name is None:
    raise ValueError('CLIENT_NAME is not set')

ERROR_CODES_TO_SKIP_EMAIL = [
    'Error 401',
    'Error 404',
    'Error 405',
    'Error 408',
]

class EmailOnErrorHandler(logging.Handler):
    def __init__(
        self, 
        mail: Mail, 
        config: t.Any,
        app=None
    ):
        super().__init__()
        self.mail = mail
        self.config = config
        self.app = app

        formatter = logging.Formatter('[%(asctime)s] %(levelname)s in %(module)s - %(message)s')
        self.setFormatter(formatter)

    def emit(self, record: LogRecord):
        try:
            message = record.getMessage()
            
            # Skip email for 404 and 429 errors
            if "404" in message or "429" in message:
                return

            # Skip email for specific error codes
            if any(error_string in message for error_string in ERROR_CODES_TO_SKIP_EMAIL):
                return

            # Only process errors at or above the logging.ERROR level
            if record.levelno >= logging.WARNING:
                print(f"Sending email for log level {record.levelname}")
                subject = f"Log Level {record.levelname} on STAR"
                sender = "hello@stxresources.org"
                recipients = self.config.EMAILS_TO_RECEIVE_ALERTS

                # Format the record including exception info
                formatted_message = self.format(record)  # This will use the formatter if set
                
                # If record has exception info and it's not already formatted, handle it explicitly
                if record.exc_info and not hasattr(record, 'exc_text') and self.formatter:
                    record.exc_text = self.formatter.formatException(record.exc_info)

                # Build the email message body
                message_body = self.build_email_body(record)

                # Send the email within application context
                if self.app:
                    with self.app.app_context():
                        self.send_email(subject, sender, recipients, message_body)
                else:
                    print("Warning: No Flask app instance available for sending error email")

        except Exception as e:
            print(f"Unexpected error in emit: {e}")
            self.handleError(record)

    def build_email_body(self, record: LogRecord):
        """Construct the body of the email with log details."""
        separator = "\n---\n"  # Define a separator for better readability

        # Combine all parts of the email body, separated by the separator
        message_body = self.format(record)
        message_body += separator + self.get_request_details()
        message_body += separator + self.get_file_and_function_details(record)
        message_body += separator + self.get_user_details()
        message_body += separator + self.get_session_variables()
        message_body += separator + self.get_traceback_details(record)

        return message_body

    def get_request_details(self):
        """Retrieve request-related details."""
        try:
            if request:
                details = f"Requested URL: {request.url}"
                details += f"\nClient IP: {request.remote_addr}"
                details += f"\nHTTP Method: {request.method}"
                details += f"\nUser Agent: {request.user_agent.string}"
                if request.method in ["POST", "PUT", "PATCH"]:
                    details += f"\nRequest Body: {request.get_data(as_text=True)}"
                details += f"\nRequest Headers:\n{request.headers}"
                return details
        except RuntimeError as e:
            return f"\nRequest Details: Unable to retrieve ({e})"
        return "\nRequest Details: Not available"

    def get_traceback_details(self, record: LogRecord):
        """Format and return traceback details if available."""
        if record.exc_info:
            return "Traceback:\n" + "".join(traceback.format_exception(*record.exc_info))
        elif hasattr(record, 'exc_text') and record.exc_text:
            return "Traceback:\n" + record.exc_text
        return ""

    def get_file_and_function_details(self, record: LogRecord):
        """Include file, module, function, and line number information."""
        return (
            f"File: {record.pathname}"
            f"\nModule: {record.module}"
            f"\nFunction: {record.funcName}"
            f"\nLine: {record.lineno}"
        )

    def get_user_details(self):
        """Retrieve details about the current user."""
        try:
            if current_user and hasattr(current_user, 'is_authenticated') and current_user.is_authenticated:
                return f"User ID: {current_user.id}"
            return "User ID: Not authenticated"
        except Exception as e:
            return f"User ID: Unable to retrieve ({e})"

    def get_session_variables(self):
        """Retrieve session variables if available."""
        try:
            if session:
                details = "Session Variables:\n"
                for key, value in session.items():
                    details += f"{key}: {value}\n"
                return details
        except Exception as e:
            return f"Session Variables: Unable to retrieve ({e})"
        return "Session Variables: Not available"

    def send_email(
            self, 
            subject: str, 
            sender: str, 
            recipients: tuple, 
            message_body: str
        ):
        """Send the constructed email."""
        try:
            message = Message(
                subject=subject, 
                sender=sender, 
                recipients=list(recipients)
            )
            message.body = message_body
            self.mail.send(message)
        except Exception as e:
            print(f"Error sending email: {e}")
            log_record = self.create_log_record(e)
            self.handleError(record=log_record)

    def create_log_record(self, e: Exception):
        """Create a LogRecord object for the error."""
        return logging.LogRecord(
            name=self.__class__.__name__,
            level=logging.ERROR,
            pathname=__file__,
            lineno=0,
            msg=f"Error sending email: {e}",
            args=(),
            exc_info=None
        )

def configure_logging(app, mail):
    # Import Config here to avoid circular imports
    if client_name == 'star':
        from project.config.star import Config
    elif client_name == 'se_legacy':
        from project.config.se_legacy import Config
    else:
        raise ValueError(f"Unknown client_name: {client_name}")

    email_on_error_handler = None
    app_mode = os.getenv('APP_MODE', AppMode.PROD.value)

    # Create email handler regardless of mode for testing
    email_on_error_handler = EmailOnErrorHandler(mail, Config, app=app)
    email_on_error_handler.setLevel(logging.ERROR)  # Only send emails for ERROR level and above

    log_level = (
        logging.INFO
        if app_mode == AppMode.DEV
        else getattr(logging, Config.PROD_LOGGING_LEVEL, logging.ERROR)  # Changed default to ERROR
    )

    dictConfig(
        {
            'version': 1,
            'formatters': {
                'default': {
                    'format': '[%(asctime)s] %(levelname)s in %(module)s - %(message)s',
                    'exc_info': True,
                }
            },
            'handlers': {
                'wsgi': {
                    'class': 'logging.StreamHandler',
                    'stream': 'ext://flask.logging.wsgi_errors_stream',
                    'formatter': 'default',
                },
            },
            'root': {
                'level': log_level, 
                'handlers': ['wsgi']
            },
        }
    )

    stream_handler = logging.StreamHandler()
    stream_handler.addFilter(NoEmailLogsFilter())

    for logger_name in ('werkzeug', 'flask.app'):
        logger = logging.getLogger(logger_name)
        logger.addFilter(ExcludeStaticAssets())
        logger.addFilter(NoEmailLogsFilter())
        logger.setLevel(log_level)

        if email_on_error_handler:
            if not any(
                isinstance(h, EmailOnErrorHandler) for h in logger.handlers
            ):
                logger.addHandler(email_on_error_handler)

    root_logger = logging.getLogger()
    root_logger.addFilter(ExcludeStaticAssets())

    if not any(
        isinstance(h, logging.StreamHandler) 
        for h in root_logger.handlers
    ):
        root_logger.addHandler(stream_handler)

    if email_on_error_handler and not any(
        isinstance(h, EmailOnErrorHandler) 
        for h in root_logger.handlers
    ):
        root_logger.addHandler(email_on_error_handler)
