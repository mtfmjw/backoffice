# settings.py

import logging
import os
from pathlib import Path


class MillisecondFormatter(logging.Formatter):
    """Custom formatter to include milliseconds in log timestamps."""

    def formatTime(self, record, datefmt=None):
        """Format time with milliseconds."""
        import datetime

        ct = datetime.datetime.fromtimestamp(record.created)
        if datefmt:
            # Replace %f with milliseconds
            if "%f" in datefmt:
                datefmt = datefmt.replace("%f", f"{int(record.msecs):06d}")
            s = ct.strftime(datefmt)
        else:
            t = ct.strftime("%Y-%m-%d %H:%M:%S")
            s = f"{t}.{int(record.msecs):03d}"
        return s


LOG_DIR = os.path.join(Path(__file__).resolve().parent.parent, "logs")

# Ensure log directory exists
os.makedirs(LOG_DIR, exist_ok=True)

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "()": "backoffice.settings_log.MillisecondFormatter",
            "format": "[{asctime}][{process:d}][{thread:d}][{ip_address}][{username}][{levelname}][{name}][{filename}:{lineno}][{funcName}]: {message}",  # noqa
            "datefmt": "%Y/%m/%d %H:%M:%S.%f",
            "style": "{",
        },
        "simple": {
            "()": "backoffice.settings_log.MillisecondFormatter",
            "format": "[{asctime}][{levelname}][{username}][{module}:{filename}:{funcName}]: {message}",
            "datefmt": "%Y/%m/%d %H:%M:%S.%f",
            "style": "{",
        },
    },
    "filters": {
        "require_debug_true": {
            "()": "django.utils.log.RequireDebugTrue",
        },
        "require_debug_false": {
            "()": "django.utils.log.RequireDebugFalse",
        },
        "extra_attributes": {
            "()": "backoffice.logging.RequestLoggingFilter",
        },
    },
    "handlers": {
        "sql_log": {
            "level": "DEBUG",
            "filters": ["extra_attributes"],
            "class": "concurrent_log_handler.ConcurrentRotatingFileHandler",
            "maxBytes": 1024 * 1024 * 2,  # 10 MB file size limit
            "backupCount": 10,
            "formatter": "verbose",
            "filename": os.path.join(LOG_DIR, "django_sql.log"),
            "encoding": "utf8",
        },
        "root_log": {
            "level": "WARN",
            "filters": ["require_debug_false", "extra_attributes"],
            "class": "logging.FileHandler",
            "formatter": "verbose",
            "filename": os.path.join(LOG_DIR, "django_root.log"),
            "encoding": "utf8",
        },
        "app_log": {
            "level": "DEBUG",
            "filters": ["extra_attributes"],
            "class": "concurrent_log_handler.ConcurrentRotatingFileHandler",
            "maxBytes": 1024 * 1024 * 2,  # 10 MB file size limit
            "backupCount": 10,  # Keep up to 10 backup files
            "formatter": "verbose",
            "filename": os.path.join(LOG_DIR, "app.log"),
            "encoding": "utf8",
        },
        "console": {
            "level": "DEBUG",
            "filters": ["extra_attributes"],
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        },
    },
    "root": {
        "handlers": ["console", "root_log"],
        "level": "INFO",
    },
    "loggers": {
        "django": {
            "handlers": ["console", "app_log"],
            "level": "DEBUG",
            "propagate": False,
        },
        "django.server": {
            "handlers": ["console", "app_log"],
            "level": "INFO",
            "propagate": False,
        },
        "django.template": {
            "handlers": ["console", "app_log"],
            "level": "WARN",
            "propagate": False,
        },
        "django.utils.autoreload": {
            "handlers": ["app_log"],
            "level": "CRITICAL",  # Set to CRITICAL to suppress most logs
            "propagate": False,
        },
        "django.db.backends": {
            "handlers": ["sql_log"],
            "level": "DEBUG",
            "propagate": False,
        },
        "urllib3": {
            "handlers": ["console", "app_log"],
            "level": "DEBUG",
            "propagate": False,
        },
    },
}
