"""
Scraper service for extracting product data from websites.
"""
import re
import json
import time
import random
import logging
import traceback
import urllib.parse
import subprocess
import os
from datetime import datetime

from bs4 import BeautifulSoup
import requests
import trafilatura

from app import db
from app.models import Website, Product, Category, ScrapeLog
from app.utils.throttling import Throttler 
from app.config import DEFAULT_USER_AGENTS, MAX_REQUESTS_PER_MINUTE, RETRY_ATTEMPTS

class ScraperService:
    """
    Service for scraping product data from websites.
    """
    def __init__(self, ai_service, image_service):
        """
        Initialize the scraper service.
        
        Args:
            ai_service: The AI service for categorization
            image_service: The image service for downloading images
        """
        self.ai_service = ai_service
        self.image_service = image_service
        self.throttler = Throttler(MAX_REQUESTS_PER_MINUTE)
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': random.choice(DEFAULT_USER_AGENTS),
            'Accept': 'text/html,application/xhtml+xml,application/xml',
            'Accept-Language': 'en-US,en;q=0.9',
        })
    
    def scrape_website(self, website):
        """
        Scrape products from a website using an external process.
        
        Args:
            website: Website model instance
            
        Returns:
            ScrapeLog instance
        """
        # Create a new scrape log
        scrape_log = ScrapeLog(website_id=website.id)
        db.session.add(scrape_log)
        db.session.commit()
        
        # Update website status
        website.update_status('scraping')
        
        # Determine which script to run based on website URL
        script_name = None
        if 'ultimateexotics.co.za' in website.url:
            script_name = "scrape_ultimateexotics.py"
        elif 'reptile-garden-sa.myshopify.com' in website.url:
            script_name = "scrape_reptilegarden.py"
        else:
            # For other websites, use a generic approach
            try:
                return self._scrape_website_directly(website, scrape_log)
            except Exception as e:
                scrape_log.status = 'failed'
                scrape_log.error_message = str(e)
                scrape_log.end_time = datetime.utcnow()
                website.status = 'failed'
                db.session.commit()
                return scrape_log
        
        # Run the appropriate script as a background process
        try:
            # Make sure data directories exist
            os.makedirs("data/images", exist_ok=True)
            os.makedirs("data/exports", exist_ok=True)
            
            # Start the process
            process = subprocess.Popen(
                ["python", script_name],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True
            )
            
            # Write PID to file for monitoring
            website_name = website.name.lower().replace(' ', '_')
            with open(f"{website_name}_pid.txt", "w") as f:
                f.write(f"{process.pid}")
            
            # Log the start
            logging.info(f"Started scraper process for {website.name} (PID: {process.pid})")
            
            # No need to wait for process to complete as it runs in background
            return scrape_log
            
        except Exception as e:
            error_msg = f"Error starting scraper for {website.name}: {str(e)}"
            logging.error(error_msg)
            scrape_log.error_message = error_msg
            scrape_log.complete(success=False)
            website.update_status('failed')
            return scrape_log
    
    def _scrape_website_directly(self, website, scrape_log):
        """
        Directly scrape a website without using an external script.
        
        Args:
            website: Website model instance
            scrape_log: ScrapeLog instance
            
        Returns:
            ScrapeLog instance
        """
        try:
            logging.info(f"Starting direct scrape for {website.name} ({website.url})")
            
            # Extract product links
            product_links = self._extract_product_links(website.url, scrape_log)
            scrape_log.update_stats(products_found=len(product_links))
            
            # Scrape products with throttling
            success_count = 0
            for i, product_url in enumerate(product_links[:website.max_products]):
                try:
                    # Check if product already exists
                    if Product.find_by_url(product_url):
                        logging.info(f"Product already exists: {product_url}")
                        continue
                    
                    # Apply throttling
                    self.throttler.throttle()
                    time.sleep(website.request_delay)
                    
                    # Scrape product
                    product_data = self._scrape_product(product_url, website.id)
                    
                    if product_data:
                        # Process product data
                        self._process_product(product_data, website.id)
                        success_count += 1
                        scrape_log.update_stats(products_scraped=success_count)
                    
                    # Update success rate periodically
                    if i > 0 and i % 10 == 0:
                        website.update_success_rate(success_count, i + 1)
                        
                except Exception as e:
                    logging.error(f"Error scraping product {product_url}: {str(e)}")
                    scrape_log.update_stats(products_failed=scrape_log.products_failed + 1)
            
            # Update final statistics
            website.update_success_rate(success_count, len(product_links))
            website.update_status('completed')
            scrape_log.complete(success=True)
            
            logging.info(f"Scrape completed for {website.name}: {success_count} products scraped")
            return scrape_log
            
        except Exception as e:
            error_msg = f"Error scraping {website.name}: {str(e)}\n{traceback.format_exc()}"
            logging.error(error_msg)
            website.update_status('failed')
            scrape_log.error_message = error_msg
            scrape_log.complete(success=False)
            return scrape_log
    
    def _extract_product_links(self, base_url, scrape_log):
        """
        Extract product links from a website.
        
        Args:
            base_url: The website URL
            scrape_log: ScrapeLog instance for tracking
            
        Returns:
            List of product URLs
        """
        product_links = []
        pages_crawled = 0
        request_times = []
        
        try:
            # Initial page
            current_url = base_url
            visited_urls = set()
            
            # Crawl pages (limited to 5 for safety)
            while current_url and pages_crawled < 5:
                if current_url in visited_urls:
                    break
                
                visited_urls.add(current_url)
                
                # Apply throttling
                self.throttler.throttle()
                
                # Fetch page
                start_time = time.time()
                response = self._fetch_url(current_url)
                request_time = time.time() - start_time
                request_times.append(request_time)
                
                if not response:
                    break
                
                # Parse HTML
                soup = BeautifulSoup(response, 'html.parser')
                
                # Extract product links - look for common patterns
                links = self._find_product_links(soup, base_url)
                product_links.extend(links)
                
                # Find pagination link
                next_page = self._find_next_page(soup, base_url, current_url)
                current_url = next_page
                pages_crawled += 1
                
                # Update log
                scrape_log.update_stats(
                    total_request_count=pages_crawled,
                    avg_request_time=sum(request_times) / len(request_times) if request_times else 0
                )
            
            return list(set(product_links))  # Remove duplicates
            
        except Exception as e:
            logging.error(f"Error extracting product links: {str(e)}")
            return product_links
    
    def _find_product_links(self, soup, base_url):
        """
        Find product links in a page using common patterns.
        """
        product_links = []
        
        # Common product link patterns
        product_patterns = [
            # Look for product containers with links
            ('div.product', 'a', 'href'),
            ('li.product', 'a', 'href'),
            ('div.item', 'a', 'href'),
            ('div.product-item', 'a', 'href'),
            
            # Look for product grids
            ('div.product-grid', 'a', 'href'),
            
            # Look for product anchors directly
            ('a.product-link', None, 'href'),
            ('a.product-title', None, 'href'),
            
            # Generic links with product in href
            ('a[href*="product"]', None, 'href'),
            ('a[href*="item"]', None, 'href')
        ]
        
        # Try each pattern
        for container_selector, link_selector, attr in product_patterns:
            try:
                if link_selector:
                    containers = soup.select(container_selector)
                    for container in containers:
                        links = container.select(link_selector)
                        for link in links:
                            if attr in link.attrs:
                                url = link[attr]
                                full_url = urllib.parse.urljoin(base_url, url)
                                product_links.append(full_url)
                else:
                    links = soup.select(container_selector)
                    for link in links:
                        if attr in link.attrs:
                            url = link[attr]
                            full_url = urllib.parse.urljoin(base_url, url)
                            product_links.append(full_url)
            except Exception:
                continue
        
        # If no product links found, try more generic link extraction
        if not product_links:
            all_links = soup.select('a[href]')
            for link in all_links:
                url = link.get('href', '')
                
                # Filter for likely product links
                if 'product' in url or 'item' in url or '/p/' in url:
                    if not url.startswith(('http://', 'https://')):
                        url = urllib.parse.urljoin(base_url, url)
                    product_links.append(url)
        
        return product_links
    
    def _find_next_page(self, soup, base_url, current_url):
        """
        Find the next page link for pagination.
        """
        # Common pagination patterns
        pagination_patterns = [
            ('a.next', 'href'),
            ('a[rel="next"]', 'href'),
            ('a[aria-label="Next"]', 'href'),
            ('li.next a', 'href'),
            ('div.pagination a:contains("Next")', 'href')
        ]
        
        for selector, attr in pagination_patterns:
            try:
                next_link = soup.select_one(selector)
                if next_link and attr in next_link.attrs:
                    next_url = next_link[attr]
                    return urllib.parse.urljoin(base_url, next_url)
            except Exception:
                continue
        
        # Try to find page numbers
        current_page_number = None
        match = re.search(r'[?&]page=(\d+)', current_url)
        if match:
            current_page_number = int(match.group(1))
            next_page_number = current_page_number + 1
            next_url = re.sub(r'([?&]page=)(\d+)', f'\\g<1>{next_page_number}', current_url)
            return next_url
        
        return None
    
    def _scrape_product(self, product_url, website_id):
        """
        Scrape a single product page.
        
        Args:
            product_url: URL of the product page
            website_id: ID of the website
            
        Returns:
            Dictionary with product data or None if failed
        """
        try:
            # Fetch product page
            html_content = self._fetch_url(product_url)
            if not html_content:
                return None
            
            # Parse HTML
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Extract main product data
            product_data = {
                'name': self._extract_product_name(soup),
                'description': self._extract_product_description(soup),
                'price': self._extract_product_price(soup),
                'currency': 'ZAR',  # Default currency for South African sites
                'url': product_url,
                'image_url': self._extract_product_image(soup, product_url),
                'website_id': website_id
            }
            
            # Validate required fields
            if not product_data['name']:
                return None
            
            # Check if this is a reptile product
            if not self.ai_service.is_reptile_product(product_data):
                logging.info(f"Not a reptile product: {product_data['name']}")
                return None
            
            return product_data
            
        except Exception as e:
            logging.error(f"Error scraping product {product_url}: {str(e)}")
            return None
    
    def _extract_product_name(self, soup):
        """Extract product name from soup."""
        selectors = [
            'h1.product-title',
            'h1.product_title',
            'h1.title',
            'h1',
            'h2.product-name',
            'h2.product-title',
            'div.product-title h1',
            'div.product-name h1'
        ]
        
        for selector in selectors:
            try:
                element = soup.select_one(selector)
                if element and element.text.strip():
                    return element.text.strip()
            except Exception:
                continue
        
        return None
    
    def _extract_product_description(self, soup):
        """Extract product description from soup."""
        selectors = [
            'div.product-description',
            'div.description',
            'div.product-details',
            'div.product-info',
            'div#description',
            'div#product-description',
            'div.tab-content'
        ]
        
        for selector in selectors:
            try:
                element = soup.select_one(selector)
                if element and element.text.strip():
                    # Clean up the description
                    text = element.text.strip()
                    text = re.sub(r'\s+', ' ', text)
                    return text
            except Exception:
                continue
        
        # Fallback to trafilatura for content extraction
        try:
            extracted_text = trafilatura.extract(str(soup), include_comments=False, include_links=False)
            if extracted_text:
                # Keep only a portion to avoid excessive text
                return extracted_text[:1000]
        except Exception:
            pass
        
        return ""
    
    def _extract_product_price(self, soup):
        """Extract product price from soup."""
        price_patterns = [
            r'R\s?(\d+(?:[.,]\d{1,2})?)',
            r'ZAR\s?(\d+(?:[.,]\d{1,2})?)',
            r'(\d+(?:[.,]\d{1,2}))\s?ZAR',
            r'Price:\s*R\s?(\d+(?:[.,]\d{1,2})?)',
            r'(\d+(?:[.,]\d{1,2}))'
        ]
        
        selectors = [
            'span.price',
            'div.price',
            'p.price',
            'span.current-price',
            'span.product-price',
            'div.product-price',
            'span.amount'
        ]
        
        # Try to find price in dedicated elements
        for selector in selectors:
            try:
                element = soup.select_one(selector)
                if element and element.text.strip():
                    price_text = element.text.strip()
                    
                    # Try to extract the price using patterns
                    for pattern in price_patterns:
                        match = re.search(pattern, price_text)
                        if match:
                            price_str = match.group(1).replace(',', '.')
                            return float(price_str)
            except Exception:
                continue
        
        # Try to find price in the whole page text
        page_text = soup.get_text()
        for pattern in price_patterns:
            try:
                match = re.search(pattern, page_text)
                if match:
                    price_str = match.group(1).replace(',', '.')
                    return float(price_str)
            except Exception:
                continue
        
        return None
    
    def _extract_product_image(self, soup, product_url):
        """Extract product image URL from soup."""
        selectors = [
            'img.product-image',
            'img.product-img',
            'img.main-image',
            'div.product-image img',
            'div.product-img img',
            'div.woocommerce-product-gallery__image img',
            'div.product-gallery img',
            'div.image-container img'
        ]
        
        for selector in selectors:
            try:
                img = soup.select_one(selector)
                if img and ('src' in img.attrs or 'data-src' in img.attrs):
                    src = img.get('data-src') or img.get('src')
                    return urllib.parse.urljoin(product_url, src)
            except Exception:
                continue
        
        # Try to find image in JSON-LD data
        try:
            json_ld = soup.select_one('script[type="application/ld+json"]')
            if json_ld:
                data = json.loads(json_ld.string)
                if isinstance(data, dict) and 'image' in data:
                    return data['image']
        except Exception:
            pass
        
        return None
    
    def _fetch_url(self, url, retries=RETRY_ATTEMPTS):
        """
        Fetch a URL with retry logic.
        
        Args:
            url: URL to fetch
            retries: Number of retries
            
        Returns:
            HTML content or None if failed
        """
        for attempt in range(retries):
            try:
                response = self.session.get(
                    url, 
                    timeout=10,
                    headers={'User-Agent': random.choice(DEFAULT_USER_AGENTS)}
                )
                
                if response.status_code == 200:
                    return response.text
                
                # If blocked or rate limited, wait longer before retry
                if response.status_code in (403, 429):
                    wait_time = (attempt + 1) * 5  # Exponential backoff
                    logging.warning(f"Request blocked ({response.status_code}), waiting {wait_time}s before retry")
                    time.sleep(wait_time)
                else:
                    logging.warning(f"Request failed with status code: {response.status_code}")
                    
            except Exception as e:
                logging.error(f"Error fetching {url}: {str(e)}")
                
            # Wait before retry
            time.sleep(attempt + 1)
        
        return None
    
    def _process_product(self, product_data, website_id):
        """
        Process product data and save to database.
        
        Args:
            product_data: Dictionary with product data
            website_id: ID of the website
            
        Returns:
            Product instance or None if failed
        """
        try:
            # Categorize product
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
            if product_data.get('image_url'):
                image_path = self.image_service.download_image(
                    product_data['image_url'], 
                    product_data['name']
                )
            
            # Create product
            product = Product(
                name=product_data['name'],
                description=product_data.get('description', ''),
                price=product_data.get('price'),
                currency=product_data.get('currency', 'ZAR'),
                url=product_data['url'],
                image_url=product_data.get('image_url'),
                image_path=image_path,
                website_id=website_id,
                category_id=category.id if category else None,
                confidence_score=confidence_score
            )
            
            db.session.add(product)
            db.session.commit()
            
            logging.info(f"Product saved: {product.name}")
            return product
            
        except Exception as e:
            logging.error(f"Error processing product {product_data.get('name', 'Unknown')}: {str(e)}")
            db.session.rollback()
            return None