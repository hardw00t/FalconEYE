"""Domain exceptions for FalconEYE."""


class FalconEyeDomainError(Exception):
    """Base exception for domain errors."""
    pass


class InvalidCodebaseError(FalconEyeDomainError):
    """Raised when codebase is invalid or inaccessible."""
    pass


class UnsupportedLanguageError(FalconEyeDomainError):
    """Raised when language is not supported."""
    pass


class InvalidChunkError(FalconEyeDomainError):
    """Raised when code chunk is invalid."""
    pass


class AnalysisError(FalconEyeDomainError):
    """Raised when AI analysis fails."""
    pass


class InvalidSecurityFindingError(FalconEyeDomainError):
    """Raised when security finding is malformed."""
    pass


class LanguageDetectionError(FalconEyeDomainError):
    """Raised when automatic language detection fails."""
    pass