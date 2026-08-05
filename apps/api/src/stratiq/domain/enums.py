from enum import StrEnum


class DocumentStatus(StrEnum):
    UPLOADED = "uploaded"
    PROCESSING = "processing"
    READY = "ready"
    FAILED = "failed"


class DocumentType(StrEnum):
    PDF = "pdf"
    CSV = "csv"
    XLSX = "xlsx"
    XLS = "xls"
    UNKNOWN = "unknown"


class HealthLabel(StrEnum):
    CRITICAL = "critical"
    WATCH = "watch"
    HEALTHY = "healthy"


class TrendDirection(StrEnum):
    UP = "up"
    DOWN = "down"
    FLAT = "flat"
    UNKNOWN = "unknown"


class AuditAction(StrEnum):
    USER_REGISTERED = "user.registered"
    USER_LOGIN = "user.login"
    USER_LOGOUT = "user.logout"
    DOCUMENT_UPLOADED = "document.uploaded"
    DOCUMENT_PROCESS_STARTED = "document.process_started"
    DOCUMENT_PROCESS_COMPLETED = "document.process_completed"
    DOCUMENT_PROCESS_FAILED = "document.process_failed"
    CHAT_MESSAGE = "chat.message"
    DECISIONS_GENERATED = "decisions.generated"
    REPORT_EXPORTED = "report.exported"
