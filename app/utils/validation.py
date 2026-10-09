import re
from datetime import datetime


def validate_name(name: str) -> str:
    """Validate that name is a non-empty string with meaningful characters."""
    cleaned = name.strip() if name else ""
    if not cleaned:
        raise ValueError("Recipient name cannot be empty or blank")
    if len(cleaned) > 200:
        raise ValueError("Recipient name must not exceed 200 characters")
    return cleaned


def validate_course(course: str) -> str:
    """Validate that course name is non-empty."""
    cleaned = course.strip() if course else ""
    if not cleaned:
        raise ValueError("Course/event name cannot be empty or blank")
    if len(cleaned) > 200:
        raise ValueError("Course name must not exceed 200 characters")
    return cleaned


def validate_date_string(date_str: str) -> str:
    """Validate date format is YYYY-MM-DD and represents a valid calendar date."""
    cleaned = date_str.strip() if date_str else ""
    if not cleaned:
        raise ValueError("Completion date cannot be empty")
    try:
        parsed = datetime.strptime(cleaned, "%Y-%m-%d").date()
        return parsed.isoformat()
    except ValueError:
        raise ValueError("Completion date must be a valid date in YYYY-MM-DD format")


def sanitize_filename(filename: str) -> str:
    """Strip dangerous characters to avoid directory traversal or OS filename issues."""
    return re.sub(r"[^a-zA-Z0-9_\-\.]", "_", filename)
