"""
Automatic scraping script for Ultimate Exotics with anti-ban protections.
This script runs automatically without user interaction.
"""
import logging
import time
import os
import sys
import random
from datetime import datetime

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("auto_scrape.log"),
        logging.StreamHandler()
    ]
)

# Import application modules
from app import app, db
from app.models import Website, Product, Category, ScrapeLog
from app.services.ai_service import AIService
from app.services.image_service import ImageService
from app.services.scraper_service import ScraperService

def scrape_ultimateexotics():
    """Automatic function to scrape Ultimate Exotics."""
    with app.app_context():
        try:
            # Create directories
            os.makedirs("data/images", exist_ok=True)
            os.makedirs("data/exports", exist_ok=True)
            
            # Get website
            website = Website.query.filter_by(url='https://ultimateexotics.co.za/shop/').first()
            logging.info(f"Starting scrape for {website.name} ({website.url})")
            
            # Create scrape log
            scrape_log = ScrapeLog(website_id=website.id)
            db.session.add(scrape_log)
            db.session.commit()
            logging.info(f"Created scrape log with ID: {scrape_log.id}")
            
            # Update website status
            website.status = 'scraping'
            website.last_scraped = datetime.utcnow()
            db.session.commit()
            
            # Initialize services
            ai_service = AIService()
            image_service = ImageService()
            scraper = ScraperService(ai_service, image_service)
            
            # Extract first 10 product links only (to be safe)
            logging.info("Extracting product links...")
            all_product_links = scraper._extract_product_links(website.url, scrape_log)
            
            # Take only 10 links for safety
            safe_limit = 10
            product_links = all_product_links[:safe_limit]
            logging.info(f"Found {len(all_product_links)} product links, will process first {len(product_links)}")
            
            # Update scrape log
            scrape_log.products_found = len(all_product_links)
            db.session.commit()
            
            # Process products
            success_count = 0
            failed_count = 0
            
            for i, product_url in enumerate(product_links):
                try:
                    logging.info(f"Processing product {i+1}/{len(product_links)}: {product_url}")
                    
                    # Check if product already exists
                    existing_product = Product.query.filter_by(url=product_url).first()
                    if existing_product:
                        logging.info(f"Product already exists: {product_url}")
                        continue
                    
                    # Add delay to avoid detection (3-5 seconds between requests)
                    delay = 3 + random.uniform(0, 2)
                    logging.info(f"Waiting {delay:.2f} seconds...")
                    time.sleep(delay)
                    
                    # Scrape product
                    product_data = scraper._scrape_product(product_url, website.id)
                    
                    if product_data:
                        # Process product
                        product = scraper._process_product(product_data, website.id)
                        if product:
                            success_count += 1
                            scrape_log.products_scraped = success_count
                            logging.info(f"Successfully processed: {product.name}")
                        else:
                            failed_count += 1
                            scrape_log.products_failed = failed_count
                            logging.warning(f"Failed to process product data")
                    else:
                        failed_count += 1
                        scrape_log.products_failed = failed_count
                        logging.warning(f"Failed to extract data from: {product_url}")
                    
                    # Commit after each product
                    db.session.commit()
                    
                except Exception as e:
                    failed_count += 1
                    scrape_log.products_failed = failed_count
                    logging.error(f"Error processing {product_url}: {str(e)}")
                    db.session.rollback()
            
            # Finalize scrape
            if success_count > 0:
                website.scrape_success_rate = success_count / (success_count + failed_count) if (success_count + failed_count) > 0 else 0
                website.status = 'completed'
                scrape_log.status = 'completed'
                scrape_log.end_time = datetime.utcnow()
                logging.info(f"Scrape completed: {success_count} products scraped, {failed_count} failed")
            else:
                website.status = 'failed'
                scrape_log.status = 'failed'
                scrape_log.error_message = "No products were successfully scraped"
                scrape_log.end_time = datetime.utcnow()
                logging.error("Scrape failed: No products were successfully scraped")
            
            db.session.commit()
            return success_count, failed_count, len(all_product_links)
            
        except Exception as e:
            logging.error(f"Error during scraping: {str(e)}")
            import traceback
            logging.error(traceback.format_exc())
            
            try:
                # Try to update website and log status
                website.status = 'failed'
                scrape_log.status = 'failed'
                scrape_log.error_message = str(e)
                scrape_log.end_time = datetime.utcnow()
                db.session.commit()
            except:
                pass
            
            return 0, 0, 0

if __name__ == "__main__":
    logging.info("===== STARTING ULTIMATE EXOTICS AUTO-SCRAPER =====")
    
    start_time = time.time()
    success, failed, total = scrape_ultimateexotics()
    elapsed = time.time() - start_time
    
    logging.info("===== SCRAPING COMPLETE =====")
    logging.info(f"Total time: {elapsed:.2f} seconds")
    logging.info(f"Products found: {total}")
    logging.info(f"Successfully scraped: {success}")
    logging.info(f"Failed: {failed}")
    
    sys.exit(0 if success > 0 else 1)