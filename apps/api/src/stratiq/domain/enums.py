"""Domain enumerations."""

from enum import Enum


class DocumentStatus(str, Enum):
    uploaded = "uploaded"
    processing = "processing"
    ready = "ready"
    failed = "failed"


class KPIDomain(str, Enum):
    financial = "financial"
    operational = "operational"
    strategic = "strategic"
    risk = "risk"
    hr = "hr"
    marketing = "marketing"
    technology = "technology"
    other = "other"


class HealthLabel(str, Enum):
    critical = "critical"
    watch = "watch"
    healthy = "healthy"


class TrendDirection(str, Enum):
    up = "up"
    down = "down"
    flat = "flat"
    unknown = "unknown"


class EvidenceMode(str, Enum):
    evidence = "evidence"
    inference = "inference"
    insufficient = "insufficient"


class AuditEventType(str, Enum):
    user_registered = "user_registered"
    user_login = "user_login"
    user_logout = "user_logout"
    token_refreshed = "token_refreshed"
    document_uploaded = "document_uploaded"
    document_processed = "document_processed"
    document_failed = "document_failed"
    chat_message_sent = "chat_message_sent"
    chat_session_created = "chat_session_created"
    decisions_generated = "decisions_generated"
    report_exported = "report_exported"
