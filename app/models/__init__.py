"""
Initialize models package.
"""
from app.models.database import db
from app.models.product import Product
from app.models.website import Website
from app.models.category import Category
from app.models.scrape_log import ScrapeLog

# Export models
__all__ = ['db', 'Product', 'Website', 'Category', 'ScrapeLog']
