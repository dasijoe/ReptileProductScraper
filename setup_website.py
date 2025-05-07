"""
Simple script to setup the Ultimate Exotics website in the database.
"""
import logging
import sys
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

# Import Flask app
from app import app, db
from app.models.website import Website
from app.models.category import Category

def setup_categories():
    """Set up basic categories if they don't exist."""
    # Common categories for reptile products
    categories = [
        'Reptiles', 
        'Reptile Food',
        'Reptile Housing',
        'Heating Equipment',
        'Lighting Equipment',
        'Substrate',
        'Decor',
        'Cleaning Supplies',
        'Healthcare',
        'Supplements',
        'Accessories'
    ]
    
    with app.app_context():
        for name in categories:
            # Check if category exists
            category = Category.query.filter_by(name=name).first()
            if not category:
                category = Category(name=name)
                db.session.add(category)
                logging.info(f"Added category: {name}")
        
        db.session.commit()
        logging.info("Categories setup complete")

def ensure_website_exists():
    """Make sure Ultimate Exotics website entry exists in the database."""
    with app.app_context():
        # Check if website exists
        website = Website.query.filter_by(url='https://ultimateexotics.co.za/shop/').first()
        
        if not website:
            # Create website
            website = Website(
                name='Ultimate Exotics',
                url='https://ultimateexotics.co.za/shop/',
                priority=1,
                request_delay=3.0,  # Conservative delay to avoid banning
                max_products=20
            )
            db.session.add(website)
            db.session.commit()
            logging.info(f"Created website with ID: {website.id}")
        else:
            logging.info(f"Website already exists: {website.name} with ID: {website.id}")

if __name__ == "__main__":
    print("==== SETTING UP DATABASE FOR ULTIMATE EXOTICS ====")
    
    with app.app_context():
        # Create categories
        setup_categories()
        
        # Create website
        ensure_website_exists()
    
    print("==== SETUP COMPLETE ====")
    print("Website and categories have been set up in the database.")