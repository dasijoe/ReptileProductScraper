"""
Scraper implementation that can be called directly from the web interface.
This allows scraping to start without long-running initialization processes.
"""
import os
import json
import time
import random
import logging
import requests
from datetime import datetime
from bs4 import BeautifulSoup
import urllib.parse

# Import Flask app
from app import db
from app.models.website import Website
from app.models.product import Product  
from app.models.category import Category
from app.models.scrape_log import ScrapeLog
from app.services.ai_service import AIService
from app.services.image_service import ImageService
from app.config import DEFAULT_USER_AGENTS

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("direct_scraper.log"),
        logging.StreamHandler()
    ]
)

class DirectScraper:
    """Direct implementation of scraper for use within web application."""
    
    def __init__(self, ai_service, image_service):
        """Initialize the scraper service."""
        self.ai_service = ai_service
        self.image_service = image_service
        self.session = requests.Session()
        
    def setup_directories(self):
        """Create necessary directories."""
        os.makedirs("data/images", exist_ok=True)
        os.makedirs("data/exports", exist_ok=True)
        
    def scrape_website(self, website_url, max_products=10):
        """
        Scrape a website directly.
        
        Args:
            website_url: URL of the website to scrape
            max_products: Maximum number of products to scrape
            
        Returns:
            Dictionary with scraping results
        """
        self.setup_directories()
        
        # Get website from database
        website = Website.query.filter_by(url=website_url).first()
        
        if not website:
            logging.error(f"Website not found: {website_url}")
            return {"success": False, "error": "Website not found in database"}
        
        # Create scrape log
        scrape_log = ScrapeLog(website_id=website.id)
        db.session.add(scrape_log)
        
        # Update website status
        website.status = 'scraping'
        website.last_scraped = datetime.utcnow()
        db.session.commit()
        
        # Initialize session with random user agent
        user_agent = random.choice(DEFAULT_USER_AGENTS)
        self.session.headers.update({
            'User-Agent': user_agent,
            'Accept': 'text/html,application/xhtml+xml,application/xml',
            'Accept-Language': 'en-US,en;q=0.9',
        })
        
        logging.info(f"Starting scrape for {website.name} with user agent: {user_agent}")
        
        try:
            # Determine which scraper to use based on URL
            if 'ultimateexotics.co.za' in website.url:
                return self._scrape_ultimateexotics(website, scrape_log, max_products)
            elif 'reptile-garden-sa.myshopify.com' in website.url:
                return self._scrape_reptile_garden(website, scrape_log, max_products)
            else:
                # Generic scraper for other websites
                return self._scrape_generic(website, scrape_log, max_products)
                
        except Exception as e:
            logging.error(f"Error scraping {website.name}: {str(e)}")
            import traceback
            logging.error(traceback.format_exc())
            
            # Update logs
            scrape_log.status = 'failed'
            scrape_log.error_message = str(e)
            scrape_log.end_time = datetime.utcnow()
            website.status = 'failed'
            db.session.commit()
            
            return {
                "success": False, 
                "error": str(e),
                "website": website.name,
                "url": website.url
            }
    
    def _scrape_ultimateexotics(self, website, scrape_log, max_products=10):
        """
        Scrape Ultimate Exotics website.
        
        Args:
            website: Website model instance
            scrape_log: ScrapeLog model instance
            max_products: Maximum number of products to scrape
            
        Returns:
            Dictionary with scraping results
        """
        try:
            # Fetch main page
            logging.info(f"Fetching main page: {website.url}")
            response = self.session.get(website.url, timeout=10)
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
            
            # Fallback to more generic approach if needed
            if not product_links:
                all_links = soup.select('a[href]')
                for link in all_links:
                    url = link.get('href', '')
                    # Filter for likely product links
                    if isinstance(url, str) and 'product' in url:
                        if not url.startswith(('http://', 'https://')):
                            url = urllib.parse.urljoin(website.url, url)
                        product_links.append(url)
            
            # Remove duplicates
            product_links = list(set(product_links))
            
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
                return {"success": False, "error": "No product links found"}
            
            # Limit number of products to process
            product_links = product_links[:max_products]
            logging.info(f"Found {num_products} product links, processing {len(product_links)}")
            
            # Process products
            success_count = 0
            failed_count = 0
            products_data = []
            
            for i, product_url in enumerate(product_links):
                try:
                    # Log progress
                    logging.info(f"Processing product {i+1}/{len(product_links)}: {product_url}")
                    
                    # Check for existing product
                    existing_product = Product.query.filter_by(url=product_url).first()
                    if existing_product:
                        logging.info(f"Product already exists: {product_url}")
                        products_data.append({
                            "name": existing_product.name,
                            "url": existing_product.url,
                            "status": "already_exists"
                        })
                        continue
                    
                    # Add delay to avoid detection
                    delay = website.request_delay + random.uniform(0, 2)
                    logging.info(f"Waiting {delay:.2f} seconds...")
                    time.sleep(delay)
                    
                    # Fetch product page
                    response = self.session.get(product_url, timeout=10)
                    if response.status_code != 200:
                        logging.warning(f"Failed to fetch product: {response.status_code}")
                        failed_count += 1
                        continue
                    
                    # Parse product page
                    soup = BeautifulSoup(response.text, 'html.parser')
                    
                    # Extract product data
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
                    
                    # Product price
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
                        if img_src:
                            if isinstance(img_src, str):
                                product_image_url = urllib.parse.urljoin(product_url, img_src)
                    
                    # Prepare product data
                    product_data = {
                        'name': product_name,
                        'description': product_description,
                        'price': product_price,
                        'url': product_url,
                        'image_url': product_image_url
                    }
                    
                    # Verify it's a reptile product
                    is_reptile_product = self.ai_service.is_reptile_product(product_data)
                    
                    if not is_reptile_product:
                        logging.info(f"Not a reptile product: {product_name}")
                        products_data.append({
                            "name": product_name,
                            "url": product_url,
                            "status": "not_reptile_product"
                        })
                        continue
                    
                    # Categorize the product
                    category_result = self.ai_service.categorize_product(product_data)
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
                        image_path = self.image_service.download_image(product_image_url, product_name)
                    
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
                    
                    products_data.append({
                        "name": product_name,
                        "url": product_url,
                        "price": product_price,
                        "category": category_name,
                        "confidence": confidence_score,
                        "status": "scraped_successfully"
                    })
                    
                except Exception as e:
                    logging.error(f"Error processing product {product_url}: {str(e)}")
                    import traceback
                    logging.error(traceback.format_exc())
                    failed_count += 1
                    scrape_log.products_failed = failed_count
                    db.session.commit()
                    
                    products_data.append({
                        "url": product_url,
                        "status": "failed",
                        "error": str(e)
                    })
            
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
            
            return {
                "success": True,
                "website": website.name,
                "website_url": website.url,
                "products_found": num_products,
                "products_processed": len(product_links),
                "products_scraped": success_count,
                "products_failed": failed_count,
                "products": products_data
            }
            
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
            
            return {
                "success": False,
                "error": str(e),
                "website": website.name,
                "website_url": website.url
            }
    
    def _scrape_reptile_garden(self, website, scrape_log, max_products=10):
        """
        Scrape Reptile Garden website.
        
        Args:
            website: Website model instance
            scrape_log: ScrapeLog model instance
            max_products: Maximum number of products to scrape
            
        Returns:
            Dictionary with scraping results
        """
        try:
            # Fetch main products page - Shopify usually has a /collections/all page
            products_url = 'https://reptile-garden-sa.myshopify.com/collections/all'
            
            logging.info(f"Fetching products page: {products_url}")
            response = self.session.get(products_url, timeout=10)
            if response.status_code != 200:
                # Try alternate URL if the main one fails
                products_url = website.url
                response = self.session.get(products_url, timeout=10)
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
                        if isinstance(href, str) and href.startswith('/'):
                            absolute_url = urllib.parse.urljoin(website.url, href)
                            product_links.append(absolute_url)
                        else:
                            product_links.append(href)
            
            # Remove duplicates
            product_links = list(set(product_links))
            
            # Filter out non-product links
            product_links = [url for url in product_links if isinstance(url, str) and '/products/' in url]
            
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
                return {"success": False, "error": "No product links found"}
            
            # Limit number of products to process
            product_links = product_links[:max_products]
            logging.info(f"Found {num_products} product links, processing {len(product_links)}")
            
            # Process products
            success_count = 0
            failed_count = 0
            products_data = []
            
            for i, product_url in enumerate(product_links):
                try:
                    # Log progress
                    logging.info(f"Processing product {i+1}/{len(product_links)}: {product_url}")
                    
                    # Check for existing product
                    existing_product = Product.query.filter_by(url=product_url).first()
                    if existing_product:
                        logging.info(f"Product already exists: {product_url}")
                        products_data.append({
                            "name": existing_product.name,
                            "url": existing_product.url,
                            "status": "already_exists"
                        })
                        continue
                    
                    # Add delay to avoid detection
                    delay = website.request_delay + random.uniform(0, 2)
                    logging.info(f"Waiting {delay:.2f} seconds...")
                    time.sleep(delay)
                    
                    # Fetch product page
                    response = self.session.get(product_url, timeout=10)
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
                        
                        if img_src and isinstance(img_src, str):
                            # Handle srcset format (multiple sizes)
                            if ' ' in img_src and ',' in img_src:
                                # Take the first URL from srcset
                                img_src = img_src.split(',')[0].split(' ')[0]
                            
                            product_image_url = urllib.parse.urljoin(product_url, img_src)
                    
                    # If no image found, try looking for JSON-LD data which often contains image info
                    if not product_image_url:
                        json_ld = soup.select_one('script[type="application/ld+json"]')
                        if json_ld and json_ld.string:
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
                    is_reptile_product = self.ai_service.is_reptile_product(product_data)
                    
                    if not is_reptile_product:
                        logging.info(f"Not a reptile product: {product_name}")
                        products_data.append({
                            "name": product_name,
                            "url": product_url,
                            "status": "not_reptile_product"
                        })
                        continue
                    
                    # Categorize the product
                    category_result = self.ai_service.categorize_product(product_data)
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
                        image_path = self.image_service.download_image(product_image_url, product_name)
                    
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
                    
                    products_data.append({
                        "name": product_name,
                        "url": product_url,
                        "price": product_price,
                        "category": category_name,
                        "confidence": confidence_score,
                        "status": "scraped_successfully"
                    })
                    
                except Exception as e:
                    logging.error(f"Error processing product {product_url}: {str(e)}")
                    import traceback
                    logging.error(traceback.format_exc())
                    failed_count += 1
                    scrape_log.products_failed = failed_count
                    db.session.commit()
                    
                    products_data.append({
                        "url": product_url,
                        "status": "failed",
                        "error": str(e)
                    })
            
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
            
            return {
                "success": True,
                "website": website.name,
                "website_url": website.url,
                "products_found": num_products,
                "products_processed": len(product_links),
                "products_scraped": success_count,
                "products_failed": failed_count,
                "products": products_data
            }
            
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
            
            return {
                "success": False,
                "error": str(e),
                "website": website.name,
                "website_url": website.url
            }
    
    def _scrape_generic(self, website, scrape_log, max_products=10):
        """
        Generic scraper for other websites.
        
        Args:
            website: Website model instance
            scrape_log: ScrapeLog model instance
            max_products: Maximum number of products to scrape
            
        Returns:
            Dictionary with scraping results
        """
        # Implementation is similar to the specific scrapers but with more
        # generic selectors and patterns to handle various website formats
        
        # For brevity, this function is not fully implemented here but would follow the 
        # same pattern as the other scraper methods with more generic selectors
        
        logging.info(f"Generic scraper not fully implemented for {website.name}")
        
        return {
            "success": False,
            "error": "Generic scraper not fully implemented",
            "website": website.name,
            "website_url": website.url
        }