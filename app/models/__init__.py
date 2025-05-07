"""
Initialize models package.
"""
from app import db

# Import models after db is defined to avoid circular imports
from app.models.category import Category
from app.models.website import Website
from app.models.product import Product
from app.models.scrape_log import ScrapeLog

# Export models
__all__ = ['db', 'Product', 'Website', 'Category', 'ScrapeLog']
