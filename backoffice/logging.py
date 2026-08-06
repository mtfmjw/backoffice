from logging import Filter
from threading import local

_thread_local = local()


def set_user_info_per_thread(request):
    """
    Set user information in thread-local storage for the current thread.

    This function extracts and stores user authentication details and IP address
    from the HTTP request into thread-local variables for use throughout the
    request processing lifecycle. This enables automatic inclusion of user context
    in log messages without explicitly passing user information to each logging call.

    Args:
        request (HttpRequest): Django HttpRequest object containing user and META information.
                              Must include user authentication data and HTTP headers.

    Thread-Local Variables Set:
        _thread_local.username (str|None): Username if user is authenticated, None otherwise
        _thread_local.ip_address (str|None): Client IP address, prioritizing X-Forwarded-For
                                           header over REMOTE_ADDR for proxy scenarios

    IP Address Resolution:
        1. First checks HTTP_X_FORWARDED_FOR header (for proxy/load balancer scenarios)
        2. If X-Forwarded-For exists, uses the first IP in the comma-separated list
        3. Falls back to REMOTE_ADDR if X-Forwarded-For is not present
        4. Returns None if no IP information is available

    Note:
        This function is typically called by middleware at the beginning of each
        request to ensure user context is available for logging throughout the
        request lifecycle.

    Example:
        ```python
        # Called by RequestMiddleware
        set_user_info_per_thread(request)
        # Now all subsequent log calls will include user context
        logger.info("User performed action")  # Includes username and IP
        ```
    """
    _thread_local.username = request.user.username if request.user.is_authenticated else None

    if request.META.get("HTTP_X_FORWARDED_FOR") is not None:
        ip_address = request.META.get("HTTP_X_FORWARDED_FOR").split(",")[0].strip()
    else:
        ip_address = request.META.get("REMOTE_ADDR") if request else None

    _thread_local.ip_address = ip_address


def clear_user_info_per_thread():
    """
    Clear user information from thread-local storage.

    Resets the thread-local user context variables to None, effectively
    removing user information from the current thread's logging context.
    This is useful for cleanup operations or when switching contexts within
    a single thread.

    Thread-Local Variables Cleared:
        _thread_local.username: Set to None
        _thread_local.ip_address: Set to None

    Note:
        This function is typically not needed in web applications as each
        request runs in its own thread context that gets cleaned up automatically.
        However, it can be useful in testing scenarios or background tasks.
    """
    _thread_local.username = None
    _thread_local.ip_address = None


class RequestLoggingFilter(Filter):
    """
    Logging filter that adds user context information to log records.

    This filter extracts user information from thread-local storage and adds
    it to log records as additional attributes. This enables automatic inclusion
    of user context (username and IP address) in log messages without requiring
    explicit formatting in each log call.

    The filter integrates with Django's logging system and the thread-local
    user information set by the RequestMiddleware to provide comprehensive
    audit trails and debugging information.

    Attributes Added to Log Records:
        username (str): The authenticated username or "anonymous" if not authenticated
        ip_address (str): The client IP address or "N/A" if not available

    Usage:
        Configure in Django settings LOGGING configuration:
        ```python
        LOGGING = {
            'filters': {
                'request_logging': {
                    '()': 'sfd.common.logging.RequestLoggingFilter',
                },
            },
            'handlers': {
                'file': {
                    'filters': ['request_logging'],
                    # ... other handler config
                },
            },
        }
        ```

    Log Format Examples:
        With this filter, log formatters can include user context:
        Format: '%(asctime)s [%(username)s@%(ip_address)s] %(levelname)s: %(message)s'
        Output: '2024-01-15 14:30:45 [john@192.168.1.100] INFO: User logged in'
    """

    def filter(self, record):
        """
        Add user context information to the log record.

        Extracts username and IP address from thread-local storage and adds
        them as attributes to the log record, making them available for
        formatting in log output.

        Args:
            record (LogRecord): The logging record to be processed. This record
                              will be modified to include user context attributes.

        Returns:
            bool: Always returns True to indicate the record should be processed.
                 (Returning False would filter out the log record entirely)

        Attributes Added:
            record.username: Username from thread-local storage or "anonymous"
            record.ip_address: IP address from thread-local storage or "N/A"
        """
        username = getattr(_thread_local, "username", None)
        record.username = username if username is not None else "anonymous"

        ip_address = getattr(_thread_local, "ip_address", None)
        record.ip_address = ip_address if ip_address is not None else "N/A"

        return True
