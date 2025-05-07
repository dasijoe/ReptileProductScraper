"""
Database configuration and initialization.
"""
from flask_sqlalchemy import SQLAlchemy
from app import db
import logging

def init_db():
    """
    Initialize database tables.
    """
    logging.info("Initializing database tables...")
    try:
        # Import models to create tables
        from app.models.product import Product
        from app.models.website import Website
        from app.models.category import Category
        from app.models.scrape_log import ScrapeLog
        
        # Create tables
        db.create_all()
        
        # Initialize categories if empty
        from app.config import PRODUCT_CATEGORIES
        if not Category.query.first():
            for category_name in PRODUCT_CATEGORIES:
                category = Category(name=category_name)
                db.session.add(category)
            
            db.session.commit()
            logging.info("Categories initialized.")
        
        # Initialize default websites if empty
        from app.config import TARGET_WEBSITES
        if not Website.query.first():
            for i, url in enumerate(TARGET_WEBSITES):
                # Extract domain name for the website name
                import re
                domain = re.search(r'https?://(?:www\.)?([^/]+)', url)
                name = domain.group(1) if domain else f"Website {i+1}"
                
                website = Website(
                    name=name,
                    url=url,
                    priority=i+1,
                    status="pending"
                )
                db.session.add(website)
            
            db.session.commit()
            logging.info("Default websites initialized.")
        
        logging.info("Database initialization completed successfully.")
    except Exception as e:
        logging.error(f"Error initializing database: {str(e)}")
        db.session.rollback()
        raise
