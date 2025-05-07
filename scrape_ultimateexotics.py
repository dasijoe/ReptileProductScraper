"""
Script to scrape Ultimate Exotics website for reptile products.
This script implements the minimal functionality needed to start collecting data
with safeguards against website banning.
"""
import os
import sys
import logging
import time
import traceback
from datetime import datetime

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Initialize Flask app context
from app import app, db
from app.models import Website, Product, Category, ScrapeLog
from app.services.ai_service import AIService
from app.services.image_service import ImageService
from app.services.scraper_service import ScraperService
from app.utils.throttling import Throttler

def ensure_folders_exist():
    """Ensure necessary folders exist for storing images and exports."""
    os.makedirs("data/images", exist_ok=True)
    os.makedirs("data/exports", exist_ok=True)

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

def scrape_ultimateexotics():
    """Main function to scrape Ultimate Exotics website."""
    with app.app_context():
        try:
            # Setup
            ensure_folders_exist()
            setup_categories()
            website = ensure_website_exists()
            
            # Initialize services
            ai_service = AIService()
            image_service = ImageService()
            scraper_service = ScraperService(ai_service, image_service)
            
            # Start scraping
            logging.info(f"Starting scrape for Ultimate Exotics ({website.url})")
            
            # Update website status
            website.update_status('scraping')
            website.last_scraped = datetime.utcnow()
            db.session.commit()
            
            # Create scrape log
            scrape_log = ScrapeLog(website_id=website.id)
            db.session.add(scrape_log)
            db.session.commit()
            
            # Extract product links with a more conservative approach
            product_links = scraper_service._extract_product_links(website.url, scrape_log)
            product_count = len(product_links)
            logging.info(f"Found {product_count} product links")
            
            # Update scrape log
            scrape_log.update_stats(products_found=product_count)
            
            # Set a reasonable batch size to avoid overwhelming the site
            batch_size = min(20, website.max_products)
            
            # Scrape products with careful throttling
            success_count = 0
            failed_count = 0
            
            logging.info(f"Starting to scrape first {batch_size} products")
            
            for i, product_url in enumerate(product_links[:batch_size]):
                try:
                    # Check if product already exists
                    existing_product = Product.query.filter_by(url=product_url).first()
                    if existing_product:
                        logging.info(f"Product already exists: {product_url}")
                        continue
                    
                    # Log progress
                    logging.info(f"Scraping product {i+1}/{batch_size}: {product_url}")
                    
                    # Apply extra throttling for safety
                    time.sleep(website.request_delay)
                    
                    # Scrape product
                    product_data = scraper_service._scrape_product(product_url, website.id)
                    
                    if product_data:
                        # Process product data (commit happens inside)
                        product = scraper_service._process_product(product_data, website.id)
                        if product:
                            success_count += 1
                            scrape_log.update_stats(products_scraped=success_count)
                            logging.info(f"Successfully processed product: {product.name}")
                    else:
                        failed_count += 1
                        scrape_log.update_stats(products_failed=failed_count)
                        logging.warning(f"Failed to extract product data from: {product_url}")
                    
                    # Commit transaction for each product to ensure we don't lose data
                    db.session.commit()
                    
                    # Sleep between products to be extra cautious
                    time.sleep(1)
                    
                except Exception as e:
                    failed_count += 1
                    scrape_log.update_stats(products_failed=failed_count)
                    logging.error(f"Error scraping product {product_url}: {str(e)}")
                    logging.error(traceback.format_exc())
                    # Don't break the whole process for one failure
                    db.session.rollback()
                    continue
            
            # Complete the scrape log
            if success_count > 0:
                website.update_status('completed')
                scrape_log.complete(success=True)
                logging.info(f"Scrape completed: {success_count} products scraped, {failed_count} failed")
            else:
                website.update_status('failed')
                scrape_log.error_message = "No products were successfully scraped"
                scrape_log.complete(success=False)
                logging.error("Scrape failed: No products were successfully scraped")
            
            db.session.commit()
            
            return success_count, failed_count, product_count
        
        except Exception as e:
            logging.error(f"Error during scraping: {str(e)}")
            logging.error(traceback.format_exc())
            return 0, 0, 0

if __name__ == "__main__":
    success, failed, total = scrape_ultimateexotics()
    logging.info(f"Scraping summary - Success: {success}, Failed: {failed}, Total found: {total}")
    sys.exit(0 if success > 0 else 1)