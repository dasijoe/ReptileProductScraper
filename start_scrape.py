"""
Script to scrape Ultimate Exotics with steps to monitor progress.
Implementing minimal scraping functionality with anti-ban protections.
"""
import logging
import time
import os
import sys
import random
from datetime import datetime

# Set up logging to both file and console
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("ultimateexotics_scrape.log"),
        logging.StreamHandler()
    ]
)

# We need to make sure the script exits at appropriate points
def exit_script(message, exit_code=0):
    """Exit the script with a message and code."""
    print(f"\n{message}")
    sys.exit(exit_code)

# Create directories for storing data
def create_directories():
    """Create necessary directories for storing data."""
    os.makedirs("data/images", exist_ok=True)
    os.makedirs("data/exports", exist_ok=True)
    logging.info("Created necessary directories")

# Import application modules
from app import app, db
from app.models import Website, Product, Category, ScrapeLog
from app.services.ai_service import AIService
from app.services.image_service import ImageService
from app.services.scraper_service import ScraperService

def run_scrape():
    """Main function to control the scraping process."""
    with app.app_context():
        try:
            # Step 1: Setup and preparation
            logging.info("==== STEP 1: SETUP AND PREPARATION ====")
            create_directories()
            
            # Get or create website
            website = Website.query.filter_by(url='https://ultimateexotics.co.za/shop/').first()
            if not website:
                logging.info("Creating Ultimate Exotics website entry")
                website = Website(
                    name='Ultimate Exotics',
                    url='https://ultimateexotics.co.za/shop/',
                    priority=1,
                    request_delay=3.0,  # Conservative delay to avoid banning
                    max_products=20  # Start with a small batch for testing
                )
                db.session.add(website)
                db.session.commit()
                logging.info(f"Created website with ID: {website.id}")
            else:
                logging.info(f"Found website: {website.name} (ID: {website.id})")
            
            # Initialize services
            ai_service = AIService()
            image_service = ImageService()
            scraper = ScraperService(ai_service, image_service)
            
            input("Press Enter to continue to Step 2: Create Scrape Log...")
            
            # Step 2: Create Scrape Log
            logging.info("==== STEP 2: CREATE SCRAPE LOG ====")
            scrape_log = ScrapeLog(website_id=website.id)
            scrape_log.status = 'running'
            db.session.add(scrape_log)
            db.session.commit()
            logging.info(f"Created ScrapeLog with ID: {scrape_log.id}")
            
            # Update website status
            website.status = 'scraping'
            website.last_scraped = datetime.utcnow()
            db.session.commit()
            logging.info(f"Updated website status to: {website.status}")
            
            input("Press Enter to continue to Step 3: Extract Product Links...")
            
            # Step 3: Extract Product Links
            logging.info("==== STEP 3: EXTRACT PRODUCT LINKS ====")
            start_time = time.time()
            logging.info(f"Starting link extraction from: {website.url}")
            
            # This can take some time
            product_links = scraper._extract_product_links(website.url, scrape_log)
            
            elapsed = time.time() - start_time
            num_links = len(product_links)
            logging.info(f"Found {num_links} product links in {elapsed:.2f} seconds")
            
            # Update scrape log with link count
            scrape_log.products_found = num_links
            db.session.commit()
            
            # Display some of the found links
            if num_links > 0:
                logging.info("Sample of product links found:")
                for i, link in enumerate(product_links[:5]):
                    logging.info(f"  {i+1}. {link}")
                if num_links > 5:
                    logging.info(f"  ... and {num_links - 5} more")
            else:
                exit_script("No product links found. Exiting.", 1)
            
            input("Press Enter to continue to Step 4: Scrape Products...")
            
            # Step 4: Scrape Products
            logging.info("==== STEP 4: SCRAPE PRODUCTS ====")
            
            # Limit the number of products for initial test
            max_products = min(website.max_products, num_links)
            logging.info(f"Will scrape up to {max_products} products")
            
            # Initialize counters
            success_count = 0
            failed_count = 0
            
            # Process each product with careful throttling
            for i, product_url in enumerate(product_links[:max_products]):
                logging.info(f"Processing product {i+1}/{max_products}: {product_url}")
                
                try:
                    # Check if product already exists
                    existing_product = Product.query.filter_by(url=product_url).first()
                    if existing_product:
                        logging.info(f"Product already exists: {product_url}")
                        continue
                    
                    # Add randomized delay to avoid detection patterns
                    delay = website.request_delay + random.uniform(0.5, 1.5)
                    logging.info(f"Waiting {delay:.2f} seconds before next request...")
                    time.sleep(delay)
                    
                    # Scrape the product
                    logging.info(f"Scraping product data from: {product_url}")
                    product_data = scraper._scrape_product(product_url, website.id)
                    
                    if product_data:
                        logging.info(f"Successfully extracted data for: {product_data.get('name', 'Unnamed product')}")
                        
                        # Process the product
                        product = scraper._process_product(product_data, website.id)
                        if product:
                            success_count += 1
                            scrape_log.products_scraped = success_count
                            logging.info(f"Successfully processed product: {product.name}")
                        else:
                            failed_count += 1
                            scrape_log.products_failed = failed_count
                            logging.warning(f"Failed to process product data")
                    else:
                        failed_count += 1
                        scrape_log.products_failed = failed_count
                        logging.warning(f"Failed to extract data from: {product_url}")
                    
                    # Update scrape log and commit transaction
                    db.session.commit()
                    
                    # After every 5 products, confirm continuation
                    if (i + 1) % 5 == 0 and i < max_products - 1:
                        input(f"Processed {i+1}/{max_products} products. Press Enter to continue...")
                    
                except Exception as e:
                    failed_count += 1
                    scrape_log.products_failed = failed_count
                    logging.error(f"Error processing {product_url}: {str(e)}")
                    db.session.rollback()
            
            input("Press Enter to continue to Step 5: Finalize Scrape...")
            
            # Step 5: Finalize Scrape
            logging.info("==== STEP 5: FINALIZE SCRAPE ====")
            
            # Update final statistics
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
            
            logging.info("==== SCRAPING PROCESS COMPLETE ====")
            return success_count, failed_count, num_links
            
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
    print("\n===== ULTIMATE EXOTICS SCRAPER =====")
    print("This script will scrape products from Ultimate Exotics with anti-ban protections.")
    print("The process will stop at each major step for monitoring.")
    print("Press Ctrl+C at any time to exit\n")
    
    # Confirm start
    input("Press Enter to begin scraping...")
    
    start_time = time.time()
    success, failed, total = run_scrape()
    elapsed = time.time() - start_time
    
    print("\n===== SCRAPING SUMMARY =====")
    print(f"Total time: {elapsed:.2f} seconds")
    print(f"Products found: {total}")
    print(f"Successfully scraped: {success}")
    print(f"Failed: {failed}")
    print(f"Success rate: {(success / total * 100) if total > 0 else 0:.2f}%")
    print("\nCheck ultimateexotics_scrape.log for detailed log information.")