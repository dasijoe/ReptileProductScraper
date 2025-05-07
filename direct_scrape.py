"""
Direct scraping script for Ultimate Exotics website.
Minimal implementation to start harvesting data with website banning precautions.
"""
import logging
import time
import os
import sys
from datetime import datetime

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("scrape_ultimateexotics.log"),
        logging.StreamHandler()
    ]
)

# Import necessary components
from app import app, db
from app.models import Website, Product, Category, ScrapeLog
from app.services.ai_service import AIService
from app.services.image_service import ImageService
from app.services.scraper_service import ScraperService

def create_directories():
    """Create necessary directories for storing data."""
    os.makedirs("data/images", exist_ok=True)
    os.makedirs("data/exports", exist_ok=True)

def scrape_ultimate_exotics():
    """
    Function to directly scrape the Ultimate Exotics website.
    Uses minimal implementation with safeguards against website banning.
    """
    with app.app_context():
        # 1. Find or create the website entry
        website = Website.query.filter_by(url='https://ultimateexotics.co.za/shop/').first()
        
        if not website:
            logging.info("Creating Ultimate Exotics website entry")
            website = Website(
                name='Ultimate Exotics',
                url='https://ultimateexotics.co.za/shop/',
                priority=1,
                request_delay=3.0,  # Conservative delay to avoid banning
                max_products=25  # Start with a small batch for testing
            )
            db.session.add(website)
            db.session.commit()
        
        # 2. Create a new scrape log
        logging.info(f"Starting scrape for {website.name} ({website.url})")
        scrape_log = ScrapeLog(website_id=website.id)
        db.session.add(scrape_log)
        db.session.commit()
        
        # 3. Update website status
        website.update_status('scraping')
        
        # 4. Initialize services
        ai_service = AIService()
        image_service = ImageService()
        scraper = ScraperService(ai_service, image_service)
        
        try:
            # 5. Extract product links (limited to prevent overwhelming)
            logging.info("Extracting product links...")
            start_time = time.time()
            product_links = scraper._extract_product_links(website.url, scrape_log)
            logging.info(f"Found {len(product_links)} product links in {time.time() - start_time:.2f} seconds")
            scrape_log.update_stats(products_found=len(product_links))
            
            # 6. Process only a subset of products to start with
            max_products = min(website.max_products, len(product_links))
            logging.info(f"Will scrape up to {max_products} products")
            
            # 7. Scrape products with careful throttling
            success_count = 0
            failed_count = 0
            
            for i, product_url in enumerate(product_links[:max_products]):
                try:
                    logging.info(f"Processing product {i+1}/{max_products}: {product_url}")
                    
                    # Check if product already exists
                    existing_product = Product.query.filter_by(url=product_url).first()
                    if existing_product:
                        logging.info(f"Product already exists: {product_url}")
                        continue
                    
                    # Add randomized delay to avoid detection
                    import random
                    delay = website.request_delay + random.uniform(0.5, 1.5)
                    time.sleep(delay)
                    
                    # Scrape the product
                    product_data = scraper._scrape_product(product_url, website.id)
                    
                    if product_data:
                        # Process the product
                        product = scraper._process_product(product_data, website.id)
                        if product:
                            success_count += 1
                            scrape_log.update_stats(products_scraped=success_count)
                            logging.info(f"Successfully processed: {product.name}")
                    else:
                        failed_count += 1
                        scrape_log.update_stats(products_failed=failed_count)
                        logging.warning(f"Failed to extract data from: {product_url}")
                    
                    # Commit after each product to ensure we don't lose data
                    db.session.commit()
                    
                except Exception as e:
                    failed_count += 1
                    scrape_log.update_stats(products_failed=failed_count)
                    logging.error(f"Error processing {product_url}: {str(e)}")
                    db.session.rollback()
            
            # 8. Update final statistics
            if success_count > 0:
                website.update_success_rate(success_count, success_count + failed_count)
                website.update_status('completed')
                scrape_log.complete(success=True)
                logging.info(f"Scrape completed: {success_count} products scraped, {failed_count} failed")
            else:
                website.update_status('failed')
                scrape_log.error_message = "No products were successfully scraped"
                scrape_log.complete(success=False)
                logging.error("Scrape failed: No products were successfully scraped")
            
            db.session.commit()
            return success_count, failed_count
            
        except Exception as e:
            logging.error(f"Error during scraping: {str(e)}")
            website.update_status('failed')
            scrape_log.error_message = str(e)
            scrape_log.complete(success=False)
            db.session.commit()
            return 0, 0

if __name__ == "__main__":
    create_directories()
    
    logging.info("Starting direct scrape of Ultimate Exotics")
    start_time = time.time()
    
    success, failed = scrape_ultimate_exotics()
    
    elapsed = time.time() - start_time
    logging.info(f"Scraping complete in {elapsed:.2f} seconds")
    logging.info(f"Summary: {success} successful, {failed} failed")
    
    # Exit with success code if we scraped at least one product
    sys.exit(0 if success > 0 else 1)