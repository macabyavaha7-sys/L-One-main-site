from .models import CONTENT_TYPES, STATUSES, TARGETS


class ContentValidationError(ValueError):
    pass


class RevisionConflict(ContentValidationError):
    pass


class ContentNotFound(ContentValidationError):
    pass


def validate_identity(target: str, content_type: str) -> None:
    if target not in TARGETS:
        raise ContentValidationError("Invalid target")
    if content_type not in CONTENT_TYPES:
        raise ContentValidationError("Invalid content type")


def validate_status(status: str) -> None:
    if status not in STATUSES:
        raise ContentValidationError("Invalid status")


def validate_publishable(item: dict) -> None:
    if not item.get("title", "").strip():
        raise ContentValidationError("Title is required before publishing")
    if not item.get("body"):
        raise ContentValidationError("Body is required before publishing")
    if not str(item.get("cover_media_id") or "").strip():
        raise ContentValidationError("Cover is required before publishing")
