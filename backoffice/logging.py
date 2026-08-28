import contextvars
from logging import Filter

# Thread-safe and Async-safe Context Variables
_username_ctx = contextvars.ContextVar("logging_username", default="anonymous")
_ip_address_ctx = contextvars.ContextVar("logging_ip_address", default="N/A")


class RequestLoggingMiddleware:
    """Middleware to capture user and IP for logging context."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # 1. Extract Username
        if hasattr(request, "user") and request.user.is_authenticated:
            username = request.user.get_username()
        else:
            username = "anonymous"

        # 2. Extract IP Address
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            ip_address = x_forwarded_for.split(",")[0].strip()
        else:
            ip_address = request.META.get("REMOTE_ADDR") or "N/A"

        # 3. Set context variables and store tokens for reset
        token_user = _username_ctx.set(username)
        token_ip = _ip_address_ctx.set(ip_address)

        try:
            response = self.get_response(request)
        finally:
            # 4. Clean up after the request completes to prevent context leak
            _username_ctx.reset(token_user)
            _ip_address_ctx.reset(token_ip)

        return response


class RequestLoggingFilter(Filter):
    """Logging filter to inject context variable attributes into log records."""

    def filter(self, record):
        record.username = _username_ctx.get()
        record.ip_address = _ip_address_ctx.get()
        return True
