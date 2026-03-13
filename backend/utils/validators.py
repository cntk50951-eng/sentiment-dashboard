"""
Validators

Input validation utilities.
"""

import re
from datetime import datetime, timedelta
from typing import Optional, Tuple


def validate_ticker(ticker: str) -> Tuple[bool, Optional[str]]:
    """
    Validate stock ticker symbol.
    
    Args:
        ticker: Stock ticker symbol
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not ticker:
        return False, "Ticker cannot be empty"
    
    # Remove $ prefix if present
    ticker = ticker.lstrip('$').upper()
    
    # Check length (1-5 characters for most exchanges)
    if len(ticker) < 1 or len(ticker) > 5:
        return False, "Ticker must be 1-5 characters"
    
    # Check format (letters only)
    if not re.match(r'^[A-Z]+$', ticker):
        return False, "Ticker must contain only letters"
    
    return True, None


def validate_date_range(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    max_range_days: int = 365
) -> Tuple[bool, Optional[str]]:
    """
    Validate date range.
    
    Args:
        start_date: Start date string (ISO format)
        end_date: End date string (ISO format)
        max_range_days: Maximum allowed range in days
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    try:
        if start_date:
            start = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
        else:
            start = datetime.now() - timedelta(days=30)
        
        if end_date:
            end = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
        else:
            end = datetime.now()
        
        # Check if end is after start
        if end < start:
            return False, "End date must be after start date"
        
        # Check range
        if (end - start).days > max_range_days:
            return False, f"Date range cannot exceed {max_range_days} days"
        
        # Check if dates are in the future
        if start > datetime.now():
            return False, "Start date cannot be in the future"
        
        return True, None
        
    except ValueError as e:
        return False, f"Invalid date format: {e}"


def sanitize_input(text: str, max_length: int = 1000) -> str:
    """
    Sanitize user input.
    
    Args:
        text: Input text
        max_length: Maximum allowed length
        
    Returns:
        Sanitized text
    """
    if not text:
        return ""
    
    # Remove control characters
    text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', text)
    
    # Trim whitespace
    text = text.strip()
    
    # Limit length
    if len(text) > max_length:
        text = text[:max_length]
    
    return text


def validate_category(category: str, allowed_categories: list) -> Tuple[bool, Optional[str]]:
    """
    Validate category against allowed list.
    
    Args:
        category: Category to validate
        allowed_categories: List of allowed categories
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not category:
        return True, None  # Empty is valid (means all categories)
    
    category_lower = category.lower()
    allowed_lower = [c.lower() for c in allowed_categories]
    
    if category_lower not in allowed_lower:
        return False, f"Invalid category. Allowed: {', '.join(allowed_categories)}"
    
    return True, None


def validate_limit(limit: int, min_val: int = 1, max_val: int = 100) -> Tuple[bool, Optional[str]]:
    """
    Validate limit parameter.
    
    Args:
        limit: Limit value
        min_val: Minimum allowed value
        max_val: Maximum allowed value
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not isinstance(limit, int):
        return False, f"Limit must be an integer"
    
    if limit < min_val:
        return False, f"Limit must be at least {min_val}"
    
    if limit > max_val:
        return False, f"Limit cannot exceed {max_val}"
    
    return True, None
