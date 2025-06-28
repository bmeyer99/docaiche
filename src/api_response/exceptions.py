"""Custom exceptions for the API Response Pipeline."""


class APIResponseError(Exception):
    """
    Base exception for API response pipeline errors.
    """

    def __init__(self, message: str):
        """
        Initialize APIResponseError.

        Args:
            message: Error message.
        """
        super().__init__(message)
        self.message = message


class FormattingError(APIResponseError):
    """
    Raised when response formatting fails.
    """

    def __init__(self, message: str = "Formatting error occurred."):
        """
        Initialize FormattingError.

        Args:
            message: Error message.
        """
        super().__init__(message)


class CacheError(APIResponseError):
    """
    Raised when cache operations fail.
    """

    def __init__(self, message: str = "Cache operation error occurred."):
        """
        Initialize CacheError.

        Args:
            message: Error message.
        """
        super().__init__(message)
