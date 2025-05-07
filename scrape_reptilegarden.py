"""
Script to scrape Reptile Garden website for reptile products.
This script implements minimal functionality with safeguards against website banning.
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
        logging.FileHandler("reptile_garden_scrape.log"),
        logging.StreamHandler(sys.stdout)
    ]
)

# Create directory structure
def ensure_folders_exist():
    """Ensure necessary folders exist for storing images and exports."""
    os.makedirs("data/images", exist_ok=True)
    os.makedirs("data/exports", exist_ok=True)
    logging.info("Data directories created")

# Import app and models (after directory creation)
from app import app, db
from app.models.website import Website
from app.models.product import Product  
from app.models.category import Category
from app.models.scrape_log import ScrapeLog
from app.services.ai_service import AIService
from app.services.image_service import ImageService

def scrape_reptilegarden():
    """Main function to scrape Reptile Garden website."""
    # Initialize required directories
    ensure_folders_exist()
    
    # Initialize services
    ai_service = AIService()
    image_service = ImageService()
    
    with app.app_context():
        # Get or create website
        website = Website.query.filter_by(url='https://reptile-garden-sa.myshopify.com/').first()
        
        if not website:
            logging.info("Creating Reptile Garden website entry")
            website = Website(
                name='Reptile Garden',
                url='https://reptile-garden-sa.myshopify.com/',
                priority=2,  # Secondary priority after Ultimate Exotics
                request_delay=3.0,  # Conservative delay to avoid banning
                max_products=15  # Limited number for testing
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
        
        # Initialize session with random user agent
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
            # Step 1: Fetch main products page - Shopify usually has a /collections/all page
            products_url = 'https://reptile-garden-sa.myshopify.com/collections/all'
            
            logging.info(f"Fetching products page: {products_url}")
            response = session.get(products_url, timeout=10)
            if response.status_code != 200:
                # Try alternate URL if the main one fails
                products_url = website.url
                response = session.get(products_url, timeout=10)
                if response.status_code != 200:
                    raise Exception(f"Failed to fetch products page: {response.status_code}")
            
            # Parse HTML
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Find product links - Shopify sites typically use specific product grid patterns
            logging.info("Extracting product links")
            product_links = []
            
            # Try multiple selectors for Shopify product links
            product_selectors = [
                '.product-card a',
                '.product-item a',
                '.grid-product__link',
                '.product-grid-item a',
                '.grid__item a[href*="/products/"]'
            ]
            
            for selector in product_selectors:
                product_elements = soup.select(selector)
                for element in product_elements:
                    href = element.get('href')
                    if href:
                        # Shopify often uses relative URLs starting with /products/
                        if href.startswith('/'):
                            absolute_url = urllib.parse.urljoin(website.url, href)
                            product_links.append(absolute_url)
                        else:
                            product_links.append(href)
            
            # Remove duplicates
            product_links = list(set(product_links))
            
            # Filter out non-product links
            product_links = [url for url in product_links if '/products/' in url]
            
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
            
            # Limit number of products to process
            product_links = product_links[:website.max_products]
            logging.info(f"Found {num_products} product links, processing {len(product_links)}")
            
            # Step 2: Process each product
            success_count = 0
            failed_count = 0
            
            for i, product_url in enumerate(product_links):
                try:
                    # Log progress
                    logging.info(f"Processing product {i+1}/{len(product_links)}: {product_url}")
                    
                    # Check for existing product
                    existing_product = Product.query.filter_by(url=product_url).first()
                    if existing_product:
                        logging.info(f"Product already exists: {product_url}")
                        continue
                    
                    # Add delay to avoid detection
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
                    
                    # Extract product data - Shopify sites have fairly consistent selectors
                    
                    # Product name
                    name_tag = (
                        soup.select_one('.product-single__title') or
                        soup.select_one('.product__title') or
                        soup.select_one('h1.title') or
                        soup.select_one('h1')
                    )
                    if not name_tag:
                        logging.warning("Could not find product name")
                        failed_count += 1
                        continue
                    
                    product_name = name_tag.text.strip()
                    
                    # Product description
                    description_tag = (
                        soup.select_one('.product-single__description') or
                        soup.select_one('.product__description') or
                        soup.select_one('.description') or
                        soup.select_one('#product-description')
                    )
                    product_description = description_tag.text.strip() if description_tag else ""
                    
                    # Product price - Shopify usually formats as $XX.XX or R XX.XX
                    price_tag = (
                        soup.select_one('.product__price') or
                        soup.select_one('.product-single__price') or
                        soup.select_one('.price') or
                        soup.select_one('[data-product-price]')
                    )
                    
                    product_price = None
                    if price_tag:
                        price_text = price_tag.text.strip()
                        # Extract price using regex for South African Rand
                        import re
                        # Try to match Rand format (R XXX.XX)
                        price_match = re.search(r'R\s?(\d+(?:[.,]\d{1,2})?)', price_text)
                        if not price_match:
                            # Try to match regular number format
                            price_match = re.search(r'(\d+(?:[.,]\d{1,2})?)', price_text)
                        
                        if price_match:
                            price_str = price_match.group(1).replace(',', '.')
                            try:
                                product_price = float(price_str)
                            except ValueError:
                                pass
                    
                    # Product image - Shopify sites often use img tags with specific classes
                    image_tag = (
                        soup.select_one('.product-featured-img') or
                        soup.select_one('.product-single__photo img') or
                        soup.select_one('.product__photo img') or
                        soup.select_one('[data-product-featured-image] img')
                    )
                    
                    product_image_url = None
                    if image_tag:
                        # Shopify often uses data-src or srcset for images
                        img_src = (
                            image_tag.get('data-srcset') or
                            image_tag.get('data-src') or
                            image_tag.get('srcset') or
                            image_tag.get('src')
                        )
                        
                        if img_src:
                            # Handle srcset format (multiple sizes)
                            if ' ' in img_src and ',' in img_src:
                                # Take the first URL from srcset
                                img_src = img_src.split(',')[0].split(' ')[0]
                            
                            product_image_url = urllib.parse.urljoin(product_url, img_src)
                    
                    # If no image found, try looking for JSON-LD data which often contains image info
                    if not product_image_url:
                        json_ld = soup.select_one('script[type="application/ld+json"]')
                        if json_ld:
                            import json
                            try:
                                data = json.loads(json_ld.string)
                                if isinstance(data, dict) and 'image' in data:
                                    product_image_url = data['image']
                            except:
                                pass
                    
                    # Prepare product data
                    product_data = {
                        'name': product_name,
                        'description': product_description,
                        'price': product_price,
                        'url': product_url,
                        'image_url': product_image_url
                    }
                    
                    # Verify it's a reptile product
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
            
            # Finalize scrape log
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
            
            # Update logs
            scrape_log.status = 'failed'
            scrape_log.error_message = str(e)
            scrape_log.end_time = datetime.utcnow()
            website.status = 'failed'
            db.session.commit()
            
            return 0

if __name__ == "__main__":
    logging.info("==== STARTING REPTILE GARDEN SCRAPER ====")
    
    start_time = time.time()
    success_count = scrape_reptilegarden()
    elapsed = time.time() - start_time
    
    logging.info(f"==== SCRAPING COMPLETE: {success_count} products scraped ====")
    logging.info(f"Total time: {elapsed:.2f} seconds")
    
    # Write PID file to indicate completion
    with open("reptilegarden_pid.txt", "w") as f:
        f.write(f"completed:{datetime.now().isoformat()}")
    
    sys.exit(0 if success_count > 0 else 1)