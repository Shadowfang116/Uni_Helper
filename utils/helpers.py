"""
Utility helper functions
"""

from datetime import datetime
from typing import Optional


def format_datetime(dt: datetime, format_string: Optional[str] = None) -> str:
    """
    Format datetime object to string

    Args:
        dt: Datetime object
        format_string: Optional format string (default: "%B %d, %Y at %I:%M %p")

    Returns:
        Formatted datetime string
    """
    if format_string:
        return dt.strftime(format_string)
    return dt.strftime("%B %d, %Y at %I:%M %p")


def parse_datetime_flexible(date_string: str) -> Optional[datetime]:
    """
    Try to parse datetime from various formats

    Args:
        date_string: Date string to parse

    Returns:
        Datetime object or None if parsing fails
    """
    formats = [
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M",
        "%Y-%m-%d",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%dT%H:%M",
        "%B %d, %Y at %I:%M %p",
        "%B %d at %I:%M %p",
        "%b %d, %Y %I:%M %p",
    ]

    for fmt in formats:
        try:
            return datetime.strptime(date_string, fmt)
        except:
            continue

    return None


def truncate_text(text: str, max_length: int = 100, suffix: str = "...") -> str:
    """
    Truncate text to max length

    Args:
        text: Text to truncate
        max_length: Maximum length
        suffix: Suffix to add if truncated

    Returns:
        Truncated text
    """
    if len(text) <= max_length:
        return text
    return text[:max_length - len(suffix)] + suffix


def validate_email(email: str) -> bool:
    """
    Basic email validation

    Args:
        email: Email address to validate

    Returns:
        True if valid format, False otherwise
    """
    import re
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))


def safe_get(dictionary: dict, *keys, default=None):
    """
    Safely get nested dictionary value

    Args:
        dictionary: Dictionary to search
        *keys: Keys to traverse
        default: Default value if not found

    Returns:
        Value at nested key or default

    Example:
        safe_get(data, 'user', 'profile', 'name', default='Unknown')
    """
    for key in keys:
        if isinstance(dictionary, dict):
            dictionary = dictionary.get(key)
            if dictionary is None:
                return default
        else:
            return default
    return dictionary


if __name__ == "__main__":
    # Test helper functions
    print("Testing helper functions...")

    # Test datetime formatting
    now = datetime.now()
    formatted = format_datetime(now)
    print(f"Formatted datetime: {formatted}")

    # Test text truncation
    long_text = "This is a very long text that needs to be truncated for display purposes."
    truncated = truncate_text(long_text, 30)
    print(f"Truncated: {truncated}")

    # Test email validation
    print(f"Valid email: {validate_email('test@example.com')}")
    print(f"Invalid email: {validate_email('notanemail')}")

    print("\n✓ Helper tests complete!")
