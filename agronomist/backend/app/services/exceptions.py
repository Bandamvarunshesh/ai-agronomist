class DuplicateUserError(Exception):
    """Raised when signup uses an email or phone number that already exists."""


class InvalidCredentialsError(Exception):
    """Raised when login credentials are invalid."""


class InactiveUserError(Exception):
    """Raised when an inactive user attempts an authenticated action."""


class FarmNotFoundError(Exception):
    """Raised when a farm does not exist or is not owned by the current user."""


class FarmPersistenceError(Exception):
    """Raised when farm data cannot be created, read, updated, or deleted."""


class ImageValidationError(Exception):
    """Raised when an uploaded image fails validation."""


class ImageTooLargeError(ImageValidationError):
    """Raised when an uploaded image exceeds the maximum allowed size."""


class ImageStorageError(Exception):
    """Raised when an uploaded image cannot be written to local storage."""


class ImagePersistenceError(Exception):
    """Raised when image metadata cannot be created or read."""


class ImageNotFoundError(Exception):
    """Raised when an image does not exist or does not belong to the farm."""


class ImageFileNotFoundError(Exception):
    """Raised when image metadata exists but the local file is missing."""


class VisionConfigurationError(Exception):
    """Raised when the configured vision provider cannot be used."""


class VisionProviderError(Exception):
    """Raised when the vision provider request fails."""


class VisionResponseParseError(Exception):
    """Raised when the vision provider returns invalid or incomplete JSON."""


class DiagnosisPersistenceError(Exception):
    """Raised when diagnosis metadata cannot be saved."""
