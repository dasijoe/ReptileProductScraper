"""
Image service for downloading and processing product images.
"""
import os
import uuid
import logging
import requests
from urllib.parse import urlparse
from app.config import IMAGES_PATH

class ImageService:
    """
    Service for downloading and processing product images.
    """
    def __init__(self):
        """
        Initialize the image service.
        """
        os.makedirs(IMAGES_PATH, exist_ok=True)
    
    def download_image(self, image_url, product_name=None):
        """
        Download an image from a URL.
        
        Args:
            image_url: URL of the image to download
            product_name: Optional product name for filename
            
        Returns:
            Local path to the saved image or None if failed
        """
        if not image_url:
            return None
        
        try:
            # Generate a filename
            url_parts = urlparse(image_url)
            
            # Extract extension from URL
            path_parts = url_parts.path.split('/')
            if path_parts and '.' in path_parts[-1]:
                extension = path_parts[-1].split('.')[-1].lower()
            else:
                extension = 'jpg'  # Default extension
            
            # Clean extension
            extension = extension.split('?')[0]
            if extension not in ['jpg', 'jpeg', 'png', 'gif', 'webp']:
                extension = 'jpg'
            
            # Generate a sanitized filename
            if product_name:
                # Sanitize product name for filename
                safe_name = ''.join(c if c.isalnum() else '_' for c in product_name)
                safe_name = safe_name[:30]  # Limit length
                filename = f"{safe_name}_{str(uuid.uuid4())[:8]}.{extension}"
            else:
                filename = f"product_{str(uuid.uuid4())}.{extension}"
            
            # Create full path
            filepath = os.path.join(IMAGES_PATH, filename)
            
            # Download the image
            response = requests.get(image_url, stream=True, timeout=10)
            
            if response.status_code == 200:
                with open(filepath, 'wb') as f:
                    for chunk in response.iter_content(1024):
                        f.write(chunk)
                
                logging.info(f"Image downloaded successfully: {filepath}")
                return filepath
            else:
                logging.warning(f"Failed to download image, status code: {response.status_code}")
                return None
                
        except Exception as e:
            logging.error(f"Error downloading image: {str(e)}")
            return None
