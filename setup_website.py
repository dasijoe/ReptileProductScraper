"""
Simple script to setup the Ultimate Exotics website in the database.
"""
import os
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)

# Initialize Flask app context
from app import app, db
from app.models import Website, Category

def setup_categories():
    """Set up basic categories if they don't exist."""
    from app.config import PRODUCT_CATEGORIES
    
    # Check if categories already exist
    if Category.query.count() > 0:
        logging.info("Categories already exist in the database")
        return
    
    # Create categories
    logging.info("Creating categories...")
    for category_name in PRODUCT_CATEGORIES:
        category = Category(name=category_name)
        db.session.add(category)
    
    db.session.commit()
    logging.info(f"Created {len(PRODUCT_CATEGORIES)} categories")

def ensure_website_exists():
    """Make sure Ultimate Exotics website entry exists in the database."""
    website = Website.query.filter_by(url='https://ultimateexotics.co.za/shop/').first()
    
    if not website:
        logging.info("Creating Ultimate Exotics website entry")
        website = Website(
            name='Ultimate Exotics',
            url='https://ultimateexotics.co.za/shop/',
            priority=1,  # Highest priority
            request_delay=3.0,  # Conservative delay to avoid banning
            max_products=50  # Start with a small batch for testing
        )
        db.session.add(website)
        db.session.commit()
        logging.info(f"Website created with ID: {website.id} and hash_id: {website.hash_id}")
    else:
        logging.info(f"Ultimate Exotics website found with ID: {website.id} and hash_id: {website.hash_id}")
    
    return website

with app.app_context():
    # Create directories
    os.makedirs("data/images", exist_ok=True)
    os.makedirs("data/exports", exist_ok=True)
    
    # Setup categories
    setup_categories()
    
    # Ensure website exists
    website = ensure_website_exists()
    
    print(f"Ultimate Exotics website has been set up with hash_id: {website.hash_id}")
    print("You can now go to the website management page and start the scraping process.")