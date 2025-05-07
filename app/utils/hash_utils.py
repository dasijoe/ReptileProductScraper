"""
Utility for generating hash IDs.
"""
import hashlib
import uuid

def generate_hash_id(source_string):
    """
    Generate a hash ID from a source string.
    
    Args:
        source_string: Source string to hash
        
    Returns:
        Hash ID as a hexadecimal string
    """
    # If source string is not provided, use a random UUID
    if not source_string:
        source_string = str(uuid.uuid4())
    
    # Convert to string if not already
    if not isinstance(source_string, str):
        source_string = str(source_string)
    
    # Add a salt to make hash more unique
    salt = "reptile_scraper_salt"
    salted_string = salt + source_string
    
    # Generate SHA-256 hash
    hash_object = hashlib.sha256(salted_string.encode())
    hash_id = hash_object.hexdigest()
    
    return hash_id
