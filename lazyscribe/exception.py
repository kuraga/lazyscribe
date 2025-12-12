"""Custom exceptions for lazyscribe."""


class LazyscribeError(Exception):
    """Base exception for lazyscribe errors."""


class ReadOnlyError(LazyscribeError):
    """Raised when a project is opened in read-only mode and write operations are tried."""


class SaveError(LazyscribeError):
    """Raised when a project is unable to save objects to the filesystem."""
