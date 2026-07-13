class DuplicateUserError(Exception):
    """Raised when signup uses an email or phone number that already exists."""


class UserValidationError(Exception):
    """Raised when account/profile input is invalid for the current user."""


class UserPersistenceError(Exception):
    """Raised when user account data cannot be read or saved."""


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


class ChatSessionNotFoundError(Exception):
    """Raised when a chat session does not exist or is not owned by the user."""


class ChatPersistenceError(Exception):
    """Raised when chat sessions or messages cannot be created or read."""


class ChatConfigurationError(Exception):
    """Raised when the configured chat provider cannot be used."""


class ChatProviderError(Exception):
    """Raised when the chat provider request fails."""


class WeatherLocationNotFoundError(Exception):
    """Raised when a farm location cannot be resolved for weather lookup."""


class WeatherProviderError(Exception):
    """Raised when the weather provider request fails."""


class WeatherResponseParseError(Exception):
    """Raised when the weather provider returns invalid or incomplete data."""


class StageAdvisoryPersistenceError(Exception):
    """Raised when stage advisory data cannot be read."""


class TimelinePersistenceError(Exception):
    """Raised when timeline events cannot be created or read."""


class NotificationNotFoundError(Exception):
    """Raised when a notification does not exist or is not owned by the user."""


class NotificationPersistenceError(Exception):
    """Raised when notifications or notification preferences cannot be saved or read."""


class EscalationContactNotFoundError(Exception):
    """Raised when no escalation contact can be found for a farm or filter."""


class EscalationContactPersistenceError(Exception):
    """Raised when escalation contacts cannot be created, updated, or read."""


class EscalationValidationError(Exception):
    """Raised when escalation input references invalid or mismatched records."""


class EscalationPersistenceError(Exception):
    """Raised when escalation records cannot be created or read."""


class KnowledgeValidationError(Exception):
    """Raised when a knowledge document cannot be accepted for ingestion."""


class KnowledgeParseError(Exception):
    """Raised when document text cannot be extracted."""


class KnowledgeEmbeddingError(Exception):
    """Raised when embedding generation fails."""


class KnowledgePersistenceError(Exception):
    """Raised when knowledge documents, versions, chunks, or search cannot be saved/read."""


class IntelligenceSourceError(Exception):
    """Raised when a configured intelligence source cannot be fetched or parsed."""


class IntelligencePersistenceError(Exception):
    """Raised when intelligence sources or articles cannot be saved/read."""


class RecommendationContextError(Exception):
    """Raised when recommendation context cannot be aggregated."""


class RecommendationConfigurationError(Exception):
    """Raised when the configured recommendation provider cannot be used."""


class RecommendationProviderError(Exception):
    """Raised when the recommendation provider request fails."""


class RecommendationResponseParseError(Exception):
    """Raised when the recommendation provider returns invalid JSON."""


class RecommendationPersistenceError(Exception):
    """Raised when recommendations cannot be saved or read."""
