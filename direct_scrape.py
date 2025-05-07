"""
Direct scraping script for Ultimate Exotics website.
Minimal implementation to start harvesting data with website banning precautions.
"""
import os
import sys
import time
import random
import logging
import requests
from datetime import datetime
from bs4 import BeautifulSoup
import urllib.parse

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("ultimateexotics_scrape.log"),
        logging.StreamHandler(sys.stdout)
    ]
)

# Create directories for storing data
def create_directories():
    """Create necessary directories for storing data."""
    os.makedirs("data/images", exist_ok=True)
    os.makedirs("data/exports", exist_ok=True)
    logging.info("Created necessary directories")

# Import the Flask app and models after directory creation
from app import app, db
from app.models.website import Website
from app.models.product import Product
from app.models.category import Category
from app.models.scrape_log import ScrapeLog
from app.services.ai_service import AIService
from app.services.image_service import ImageService

def scrape_ultimate_exotics():
    """
    Function to directly scrape the Ultimate Exotics website.
    Uses minimal implementation with safeguards against website banning.
    """
    logging.info("Starting Ultimate Exotics scraper")
    create_directories()
    
    # Initialize services
    ai_service = AIService()
    image_service = ImageService()
    
    with app.app_context():
        # Get or create website
        website = Website.query.filter_by(url='https://ultimateexotics.co.za/shop/').first()
        if not website:
            logging.info("Creating Ultimate Exotics website entry")
            website = Website(
                name='Ultimate Exotics',
                url='https://ultimateexotics.co.za/shop/',
                priority=1,
                request_delay=3.0,  # Conservative delay to avoid banning
                max_products=10  # Start with a small batch for testing
            )
            db.session.add(website)
            db.session.commit()
        
        # Create scrape log
        scrape_log = ScrapeLog(website_id=website.id)
        db.session.add(scrape_log)
        
        # Update website status
        website.status = 'scraping'
        website.last_scraped = datetime.utcnow()
        db.session.commit()
        
        logging.info(f"Starting scrape for website: {website.name} (ID: {website.id})")
        
        # Initialize session with random user agent to avoid detection
        session = requests.Session()
        user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0'
        ]
        session.headers.update({
            'User-Agent': random.choice(user_agents),
            'Accept': 'text/html,application/xhtml+xml,application/xml',
            'Accept-Language': 'en-US,en;q=0.9',
        })
        
        try:
            # Step 1: Get the main page and extract product links
            logging.info(f"Fetching main page: {website.url}")
            response = session.get(website.url, timeout=10)
            if response.status_code != 200:
                raise Exception(f"Failed to fetch main page: {response.status_code}")
            
            # Parse HTML
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Find product links - Ultimate Exotics uses WooCommerce
            logging.info("Extracting product links")
            product_links = []
            
            # Try different selectors for product links
            product_containers = soup.select('li.product') or soup.select('div.product') or soup.select('div.product-item')
            
            for container in product_containers:
                link_tag = container.select_one('a.woocommerce-LoopProduct-link') or container.select_one('a')
                if link_tag and 'href' in link_tag.attrs:
                    product_url = link_tag['href']
                    # Make sure it's an absolute URL
                    if not product_url.startswith(('http://', 'https://')):
                        product_url = urllib.parse.urljoin(website.url, product_url)
                    product_links.append(product_url)
            
            # If no product links found with specific selectors, try generic approach
            if not product_links:
                all_links = soup.select('a[href]')
                for link in all_links:
                    url = link.get('href', '')
                    # Filter for likely product links
                    if 'product' in url and url.startswith(('http://', 'https://')):
                        product_links.append(url)
            
            # Update scrape log
            num_products = len(product_links)
            scrape_log.products_found = num_products
            db.session.commit()
            
            if num_products == 0:
                logging.warning("No product links found!")
                scrape_log.status = 'failed'
                scrape_log.error_message = 'No product links found'
                scrape_log.end_time = datetime.utcnow()
                website.status = 'failed'
                db.session.commit()
                return 0
            
            logging.info(f"Found {num_products} product links")
            
            # Limit to max_products for initial testing
            product_links = product_links[:website.max_products]
            
            # Step 2: Process each product link
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
                    
                    # Add delay to avoid detection (3-5 seconds)
                    delay = website.request_delay + random.uniform(0, 2)
                    logging.info(f"Waiting {delay:.2f} seconds...")
                    time.sleep(delay)
                    
                    # Fetch product page
                    response = session.get(product_url, timeout=10)
                    if response.status_code != 200:
                        logging.warning(f"Failed to fetch product: {response.status_code}")
                        failed_count += 1
                        continue
                    
                    # Parse product page
                    soup = BeautifulSoup(response.text, 'html.parser')
                    
                    # Extract product data using various selectors for robustness
                    
                    # Product name
                    name_tag = (
                        soup.select_one('h1.product_title') or 
                        soup.select_one('h1.entry-title') or
                        soup.select_one('h1')
                    )
                    if not name_tag:
                        logging.warning("Could not find product name")
                        failed_count += 1
                        continue
                    
                    product_name = name_tag.text.strip()
                    
                    # Product description
                    description_tag = (
                        soup.select_one('div.woocommerce-product-details__short-description') or
                        soup.select_one('div#tab-description') or
                        soup.select_one('div.product-description')
                    )
                    product_description = description_tag.text.strip() if description_tag else ""
                    
                    # Product price - Ultimate Exotics uses WooCommerce price format (R XXX.XX)
                    price_tag = (
                        soup.select_one('p.price') or
                        soup.select_one('span.price') or
                        soup.select_one('span.woocommerce-Price-amount')
                    )
                    
                    product_price = None
                    if price_tag:
                        price_text = price_tag.text.strip()
                        # Extract price using regex for South African Rand
                        import re
                        price_match = re.search(r'R\s?(\d+(?:[.,]\d{1,2})?)', price_text)
                        if price_match:
                            price_str = price_match.group(1).replace(',', '.')
                            try:
                                product_price = float(price_str)
                            except ValueError:
                                pass
                    
                    # Product image
                    image_tag = (
                        soup.select_one('img.wp-post-image') or
                        soup.select_one('div.woocommerce-product-gallery__image img') or
                        soup.select_one('div.images img')
                    )
                    
                    product_image_url = None
                    if image_tag and ('src' in image_tag.attrs or 'data-src' in image_tag.attrs):
                        img_src = image_tag.get('data-src') or image_tag.get('src')
                        product_image_url = urllib.parse.urljoin(product_url, img_src)
                    
                    # Check if this appears to be a reptile product
                    # Use AI service to verify it's a reptile product
                    product_data = {
                        'name': product_name,
                        'description': product_description,
                        'price': product_price,
                        'url': product_url,
                        'image_url': product_image_url
                    }
                    
                    is_reptile_product = ai_service.is_reptile_product(product_data)
                    
                    if not is_reptile_product:
                        logging.info(f"Not a reptile product: {product_name}")
                        continue
                    
                    # Categorize the product
                    category_result = ai_service.categorize_product(product_data)
                    category_name = category_result.get('category_name', 'Uncategorized')
                    confidence_score = category_result.get('confidence_score', 0.0)
                    
                    # Get or create category
                    category = Category.query.filter_by(name=category_name).first()
                    if not category:
                        category = Category(name=category_name)
                        db.session.add(category)
                        db.session.flush()
                    
                    # Download image if available
                    image_path = None
                    if product_image_url:
                        image_path = image_service.download_image(product_image_url, product_name)
                    
                    # Create product
                    new_product = Product(
                        name=product_name,
                        description=product_description,
                        price=product_price,
                        currency='ZAR',
                        url=product_url,
                        image_url=product_image_url,
                        image_path=image_path,
                        website_id=website.id,
                        category_id=category.id if category else None,
                        confidence_score=confidence_score
                    )
                    
                    db.session.add(new_product)
                    db.session.commit()
                    
                    logging.info(f"Successfully scraped product: {product_name}")
                    success_count += 1
                    scrape_log.products_scraped = success_count
                    db.session.commit()
                    
                except Exception as e:
                    logging.error(f"Error processing product {product_url}: {str(e)}")
                    import traceback
                    logging.error(traceback.format_exc())
                    failed_count += 1
                    scrape_log.products_failed = failed_count
                    db.session.commit()
            
            # Finalize scrape
            scrape_log.end_time = datetime.utcnow()
            
            if success_count > 0:
                scrape_log.status = 'completed'
                website.status = 'completed'
                website.scrape_success_rate = success_count / len(product_links) if product_links else 0
            else:
                scrape_log.status = 'failed'
                website.status = 'failed'
                scrape_log.error_message = "No products were successfully scraped"
            
            db.session.commit()
            
            logging.info(f"Scraping completed: {success_count} products scraped, {failed_count} failed")
            return success_count
            
        except Exception as e:
            logging.error(f"Error during scraping: {str(e)}")
            import traceback
            logging.error(traceback.format_exc())
            
            # Update scrape log with error
            scrape_log.status = 'failed'
            scrape_log.error_message = str(e)
            scrape_log.end_time = datetime.utcnow()
            website.status = 'failed'
            db.session.commit()
            
            return 0

if __name__ == "__main__":
    print("==== STARTING ULTIMATE EXOTICS DIRECT SCRAPER ====")
    print("This script will scrape products from Ultimate Exotics with anti-ban protections")
    print("Scraping a small number of products for testing")
    
    start_time = time.time()
    success_count = scrape_ultimate_exotics()
    elapsed = time.time() - start_time
    
    print(f"==== SCRAPING COMPLETE: {success_count} products scraped ====")
    print(f"Total time: {elapsed:.2f} seconds")
    print("Check ultimateexotics_scrape.log for detailed log information")