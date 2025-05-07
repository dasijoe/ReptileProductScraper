"""
Utility for validating input data.
"""
import re
from urllib.parse import urlparse

def validate_url(url):
    """
    Validate a URL.
    
    Args:
        url: URL to validate
        
    Returns:
        Boolean indicating if the URL is valid
    """
    if not url:
        return False
    
    # Basic validation
    try:
        result = urlparse(url)
        return all([result.scheme in ['http', 'https'], result.netloc])
    except:
        return False

def validate_product_name(name):
    """
    Validate a product name.
    
    Args:
        name: Product name to validate
        
    Returns:
        Boolean indicating if the name is valid
    """
    if not name:
        return False
    
    # Name should be a string with at least 3 characters
    return isinstance(name, str) and len(name.strip()) >= 3

def validate_price(price):
    """
    Validate a price.
    
    Args:
        price: Price to validate
        
    Returns:
        Float price or None if invalid
    """
    if price is None:
        return None
    
    # Try to convert to float
    try:
        price_float = float(price)
        # Price should be positive
        return price_float if price_float >= 0 else None
    except:
        return None

def validate_email(email):
    """
    Validate an email address.
    
    Args:
        email: Email to validate
        
    Returns:
        Boolean indicating if the email is valid
    """
    if not email:
        return False
    
    # Basic email validation pattern
    pattern = r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$'
    return bool(re.match(pattern, email))
