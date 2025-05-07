"""
Script to setup all target websites in the database.
This ensures the websites and categories exist before any scraping starts.
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
        'Reptiles',  # Live animals
        'Reptile Food',  # Rodents, insects, etc.
        'Reptile Housing',  # Terrariums, vivariums, etc.
        'Heating Equipment',  # Heat mats, lamps, thermostats
        'Lighting Equipment',  # UVB lights, fixtures
        'Substrate',  # Bedding, soil, etc.
        'Decor',  # Hides, branches, plants
        'Cleaning Supplies',  # Disinfectants, cleaning tools
        'Healthcare',  # Medicines, supplements
        'Supplements',  # Vitamins, calcium
        'Accessories',  # Tools, feeding equipment
        'Amphibians',  # Frogs, salamanders, etc.
        'Invertebrates',  # Spiders, scorpions, etc.
        'Books & Resources',  # Care guides, etc.
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

def setup_ultimate_exotics():
    """Set up Ultimate Exotics website in the database."""
    with app.app_context():
        # Check if website exists
        website = Website.query.filter_by(url='https://ultimateexotics.co.za/shop/').first()
        
        if not website:
            # Create website
            website = Website(
                name='Ultimate Exotics',
                url='https://ultimateexotics.co.za/shop/',
                priority=1,  # Highest priority
                request_delay=3.0,  # Conservative delay to avoid banning
                max_products=20
            )
            db.session.add(website)
            db.session.commit()
            logging.info(f"Created Ultimate Exotics website with ID: {website.id}")
        else:
            logging.info(f"Ultimate Exotics website already exists with ID: {website.id}")

def setup_reptile_garden():
    """Set up Reptile Garden website in the database."""
    with app.app_context():
        # Check if website exists
        website = Website.query.filter_by(url='https://reptile-garden-sa.myshopify.com/').first()
        
        if not website:
            # Create website
            website = Website(
                name='Reptile Garden',
                url='https://reptile-garden-sa.myshopify.com/',
                priority=2,  # Secondary priority
                request_delay=3.0,  # Conservative delay to avoid banning
                max_products=15
            )
            db.session.add(website)
            db.session.commit()
            logging.info(f"Created Reptile Garden website with ID: {website.id}")
        else:
            logging.info(f"Reptile Garden website already exists with ID: {website.id}")

def setup_all_websites():
    """Set up all websites."""
    # Create categories first
    setup_categories()
    
    # Set up each website
    setup_ultimate_exotics()
    setup_reptile_garden()
    
    logging.info("All websites setup complete")

if __name__ == "__main__":
    print("==== SETTING UP ALL TARGET WEBSITES ====")
    
    setup_all_websites()
    
    print("==== SETUP COMPLETE ====")
    print("Websites and categories have been set up in the database.")