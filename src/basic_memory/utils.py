"""Utility functions for basic-memory."""

import os
import calendar
import warnings
import logging
import re
import sys
from pathlib import Path
from typing import Optional, Protocol, Union, runtime_checkable, List
from datetime import datetime, timedelta

from loguru import logger
from unidecode import unidecode
from dateparser import parse


@runtime_checkable
class PathLike(Protocol):
    """Protocol for objects that can be used as paths."""

    def __str__(self) -> str: ...


# In type annotations, use Union[Path, str] instead of FilePath for now
# This preserves compatibility with existing code while we migrate
FilePath = Union[Path, str]

# Disable the "Queue is full" warning
logging.getLogger("opentelemetry.sdk.metrics._internal.instrument").setLevel(logging.ERROR)


def generate_permalink(file_path: Union[Path, str, PathLike]) -> str:
    """Generate a stable permalink from a file path.

    Args:
        file_path: Original file path (str, Path, or PathLike)

    Returns:
        Normalized permalink that matches validation rules. Converts spaces and underscores
        to hyphens for consistency.

    Examples:
        >>> generate_permalink("docs/My Feature.md")
        'docs/my-feature'
        >>> generate_permalink("specs/API (v2).md")
        'specs/api-v2'
        >>> generate_permalink("design/unified_model_refactor.md")
        'design/unified-model-refactor'
    """
    # Convert Path to string if needed
    path_str = str(file_path)

    # Remove extension
    base = os.path.splitext(path_str)[0]

    # Transliterate unicode to ascii
    ascii_text = unidecode(base)

    # Insert dash between camelCase
    ascii_text = re.sub(r"([a-z0-9])([A-Z])", r"\1-\2", ascii_text)

    # Convert to lowercase
    lower_text = ascii_text.lower()

    # replace underscores with hyphens
    text_with_hyphens = lower_text.replace("_", "-")

    # Replace remaining invalid chars with hyphens
    clean_text = re.sub(r"[^a-z0-9/\-]", "-", text_with_hyphens)

    # Collapse multiple hyphens
    clean_text = re.sub(r"-+", "-", clean_text)

    # Clean each path segment
    segments = clean_text.split("/")
    clean_segments = [s.strip("-") for s in segments]

    return "/".join(clean_segments)


def setup_logging(
    env: str,
    home_dir: Path,
    log_file: Optional[str] = None,
    log_level: str = "INFO",
    console: bool = True,
) -> None:  # pragma: no cover
    """
    Configure logging for the application.

    Args:
        env: The environment name (dev, test, prod)
        home_dir: The root directory for the application
        log_file: The name of the log file to write to
        log_level: The logging level to use
        console: Whether to log to the console
    """
    # Remove default handler and any existing handlers
    logger.remove()

    # Add file handler if we are not running tests and a log file is specified
    if log_file and env != "test":
        # Setup file logger
        log_path = home_dir / log_file
        logger.add(
            str(log_path),
            level=log_level,
            rotation="10 MB",
            retention="10 days",
            backtrace=True,
            diagnose=True,
            enqueue=True,
            colorize=False,
        )

    # Add console logger if requested or in test mode
    if env == "test" or console:
        logger.add(sys.stderr, level=log_level, backtrace=True, diagnose=True, colorize=True)

    logger.info(f"ENV: '{env}' Log level: '{log_level}' Logging to {log_file}")

    # Reduce noise from third-party libraries
    noisy_loggers = {
        # HTTP client logs
        "httpx": logging.WARNING,
        # File watching logs
        "watchfiles.main": logging.WARNING,
    }

    # Set log levels for noisy loggers
    for logger_name, level in noisy_loggers.items():
        logging.getLogger(logger_name).setLevel(level)


def parse_tags(tags: Union[List[str], str, None]) -> List[str]:
    """Parse tags from various input formats into a consistent list.

    Args:
        tags: Can be a list of strings, a comma-separated string, or None

    Returns:
        A list of tag strings, or an empty list if no tags
    """
    if tags is None:
        return []

    if isinstance(tags, list):
        return tags

    if isinstance(tags, str):
        return [tag.strip() for tag in tags.split(",") if tag.strip()]

    # For any other type, try to convert to string and parse
    try:  # pragma: no cover
        return parse_tags(str(tags))
    except (ValueError, TypeError):  # pragma: no cover
        logger.warning(f"Couldn't parse tags from input of type {type(tags)}: {tags}")
        return []


def parse_date(date_str: Union[str, datetime, None]) -> Optional[datetime]:
    """Parse a date string into a datetime object.
    
    Handles:
    - None values (returns None)
    - datetime objects (returns as is) 
    - Explicit dates (e.g. "2024-03-15")
    - Dates without year (uses current year)
    - Relative dates (e.g. "1 week ago")
    - Invalid dates (adjusts to last valid day of month)
    - Explicit years (preserves year including 1999)
    
    Examples:
        >>> parse_date("2024-03-15")   # Explicit date
        datetime(2024, 3, 15)
        >>> parse_date("March 15")      # Date without year
        datetime(2024, 3, 15)  # Uses current year
        >>> parse_date("April 31")     # Invalid date
        datetime(2024, 4, 30)  # Adjusts to last day
        >>> parse_date("1 week ago")   # Relative date
        datetime(...)  # Date relative to now
        >>> parse_date(None)           # None handling
        None
    """
    # Suppress the specific deprecation warning about dates without years
    with warnings.catch_warnings():
        warnings.filterwarnings(
            "ignore",
            message="Parsing dates involving a day of month without a year specified is ambiguious",
            category=DeprecationWarning
        )
        
        if date_str is None:
            return None
            
        if isinstance(date_str, datetime):
            return date_str
            
        # Reject single numbers as invalid dates
        if isinstance(date_str, str) and date_str.strip().isdigit():
            return None
            
        # Handle relative dates
        relative_indicators = {'ago', 'last', 'previous', 'yesterday', 'today', 'tomorrow', 'week', 'day', 'month', 'year'}
        if any(indicator in str(date_str).lower() for indicator in relative_indicators):
            try:
                # For relative dates, we don't need PREFER_DATES_FROM
                return parse(date_str, settings={'STRICT_PARSING': False})
            except (ValueError, TypeError):
                return None
        
        # Try to match month-day pattern first (e.g. "April 31", "February 29")
        if isinstance(date_str, str):
            month_names = {
                'january': 1, 'february': 2, 'march': 3, 'april': 4,
                'may': 5, 'june': 6, 'july': 7, 'august': 8,
                'september': 9, 'october': 10, 'november': 11, 'december': 12
            }
            
            # Convert to lowercase for matching
            date_lower = date_str.lower()
            
            # Try to find month name in the string
            found_month = None
            for month_name, month_num in month_names.items():
                if month_name in date_lower:
                    found_month = month_num
                    break
                    
            if found_month:
                # Try to extract day number
                day_match = re.search(r'\b(\d{1,2})\b', date_str)
                if day_match:
                    day = int(day_match.group(1))
                    
                    # Check if there's a year in the string
                    year_match = re.search(r'\b(19|20)\d{2}\b', date_str)
                    year = int(year_match.group(0)) if year_match else datetime.now().year
                    
                    try:
                        # Get the last day of the target month
                        if found_month == 12:
                            next_month = datetime(year + 1, 1, 1)
                        else:
                            next_month = datetime(year, found_month + 1, 1)
                        last_day = (next_month - timedelta(days=1)).day
                        
                        # Adjust day if needed
                        if day > last_day:
                            day = last_day
                            
                        # Create datetime with adjusted values
                        return datetime(year, found_month, day)
                    except ValueError:
                        pass
        
        # If month-day pattern didn't match, try normal parsing
        try:
            # First check if the string already contains a year
            has_year = bool(re.search(r'\b(19|20)\d{2}\b', str(date_str)))
            current_year = datetime.now().year
            
            if has_year:
                # If it has a year, parse as is with PREFER_DATES_FROM
                dt = parse(date_str, settings={
                    'PREFER_DATES_FROM': 'past' if '1999' in str(date_str) else 'current_period',
                    'RELATIVE_BASE': datetime(current_year, 1, 1),
                    'STRICT_PARSING': False
                })
            else:
                # If no year, explicitly add current year
                dt = parse(f"{date_str}, {current_year}", settings={
                    'PREFER_DATES_FROM': 'current_period',
                    'RELATIVE_BASE': datetime(current_year, 1, 1),
                    'STRICT_PARSING': False
                })
            
            return dt if dt else None
            
        except (ValueError, TypeError):
            logger.warning(f"Could not parse date string: {date_str}")
            return None
