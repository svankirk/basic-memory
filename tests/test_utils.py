"""Tests for utility functions."""

import pytest
from datetime import datetime, timedelta
from basic_memory.utils import generate_permalink, parse_tags, parse_date


def test_parse_date_basic():
    """Test basic date parsing functionality."""
    # Test None handling
    assert parse_date(None) is None
    
    # Test datetime object
    now = datetime.now()
    assert parse_date(now) == now
    
    # Test explicit dates
    assert parse_date("2024-03-15").date() == datetime(2024, 3, 15).date()
    
    # Test dates without year (should use current year)
    current_year = datetime.now().year
    march_15 = parse_date("March 15")
    assert march_15 is not None
    assert march_15.year == current_year
    assert march_15.month == 3
    assert march_15.day == 15
    
    # Test relative dates
    one_week_ago = parse_date("1 week ago")
    assert one_week_ago is not None
    assert (datetime.now() - one_week_ago).days == 7
    
    yesterday = parse_date("yesterday")
    assert yesterday is not None
    assert (datetime.now() - yesterday).days == 1
    
    # Test invalid dates
    assert parse_date("not a date") is None
    assert parse_date("") is None


@pytest.mark.extended_date_parsing
class TestExtendedDateParsing:
    """Extended date parsing tests that can be optionally run."""
    
    def test_complex_relative_dates(self):
        """Test more complex relative date expressions."""
        assert parse_date("last month") is not None
        assert parse_date("next week") is not None
        assert parse_date("2 months ago") is not None
        
        # Verify relative date calculations
        two_months_ago = parse_date("2 months ago")
        assert two_months_ago is not None
        assert 55 <= (datetime.now() - two_months_ago).days <= 65  # Approximate check
    
    def test_date_formats(self):
        """Test various date format parsing."""
        # Different separators and formats
        assert parse_date("2024/03/15").date() == datetime(2024, 3, 15).date()
        assert parse_date("15-Mar-2024").date() == datetime(2024, 3, 15).date()
        
        # Natural language
        march_15 = parse_date("March 15th")
        assert march_15 is not None
        assert march_15.year == datetime.now().year
    
    def test_edge_cases(self):
        """Test edge cases in date parsing."""
        # Leap year handling
        feb_29 = parse_date("February 29")
        assert feb_29 is not None
        assert feb_29.month == 2
        assert feb_29.day in (28, 29)
        
        # End of month handling
        april_31 = parse_date("April 31")
        assert april_31 is not None
        assert april_31.month == 4
        assert april_31.day == 30  # Should adjust to valid date
    
    def test_time_components(self):
        """Test parsing dates with time components."""
        # Date with time
        dt = parse_date("2024-03-15 14:30:00")
        assert dt is not None
        assert dt.hour == 14
        assert dt.minute == 30
        
        # Timezone handling (if supported)
        dt = parse_date("2024-03-15 14:30:00 UTC")
        assert dt is not None
    
    def test_boundary_cases(self):
        """Test boundary cases and formatting variations."""
        # Whitespace handling
        assert parse_date("   2024-03-15   ").date() == datetime(2024, 3, 15).date()
        
        # Case sensitivity
        assert parse_date("MARCH 15").month == 3
        assert parse_date("march 15").month == 3
        
        # Historical and future dates
        assert parse_date("January 1, 1970") is not None
        assert parse_date("December 31, 2100") is not None
    
    def test_invalid_cases(self):
        """Test various invalid date inputs."""
        assert parse_date("not really a date at all") is None
        assert parse_date("15") is None  # Just a number
        assert parse_date("2024-13-45") is None  # Invalid month/day
    
    def test_year_handling(self):
        """Test specific year handling cases."""
        # Test explicit 1999 dates
        dt = parse_date("March 15, 1999")
        assert dt is not None
        assert dt.year == 1999  # Should preserve actual 1999 dates
        
        # Test that non-1999 years are preserved
        dt = parse_date("March 15, 2000")
        assert dt is not None
        assert dt.year == 2000 