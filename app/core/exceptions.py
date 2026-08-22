class AppError(Exception):
    """Base class for all application-raised errors."""

    status_code: int = 500

    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


class InvalidCoordinatesError(AppError):
    status_code = 400


class InvalidQueryParamsError(AppError):
    status_code = 400


class UpstreamServiceError(AppError):
    """Raised when the DataSF API is unreachable or returns a bad response."""

    status_code = 502
