"""Domain exceptions – raised by application use-cases and mapped to HTTP errors in the interface layer."""


class StratIQError(Exception):
    """Base exception for all StratIQ errors."""


class NotFoundError(StratIQError):
    """Resource does not exist."""

    def __init__(self, resource: str, identifier: object) -> None:
        super().__init__(f"{resource} not found: {identifier}")
        self.resource = resource
        self.identifier = identifier


class AuthenticationError(StratIQError):
    """Invalid credentials or token."""


class AuthorizationError(StratIQError):
    """Caller lacks permission for the requested action."""


class ConflictError(StratIQError):
    """Resource already exists or state conflict."""

    def __init__(self, message: str) -> None:
        super().__init__(message)


class ValidationError(StratIQError):
    """Domain-level validation failure."""

    def __init__(self, message: str) -> None:
        super().__init__(message)


class ProcessingError(StratIQError):
    """Document processing pipeline failure."""

    def __init__(self, message: str) -> None:
        super().__init__(message)


class StorageError(StratIQError):
    """Object storage operation failure."""

    def __init__(self, message: str) -> None:
        super().__init__(message)


class EvidenceRequiredError(StratIQError):
    """KPI must have at least one evidence chunk."""

    def __init__(self, kpi_name: str) -> None:
        super().__init__(f"KPI '{kpi_name}' has no evidence_chunk_ids – extraction rejected.")
        self.kpi_name = kpi_name
