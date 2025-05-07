
"""
Functional test script for scraper service.
"""
import logging
import sys
from app import app, db
from app.models import Website, Product
from app.services.direct_scraper import DirectScraper
from app.services.ai_service import AIService
from app.services.image_service import ImageService

logging.basicConfig(level=logging.INFO)

def test_scraper():
    """Run functional tests for scrapers."""
    with app.app_context():
        ai_service = AIService()
        image_service = ImageService()
        scraper = DirectScraper(ai_service, image_service)
        
        websites = [
            "https://ultimateexotics.co.za/shop/",
            "https://reptile-garden-sa.myshopify.com/"
        ]
        
        results = []
        for url in websites:
            try:
                website = Website.query.filter_by(url=url).first()
                if not website:
                    continue
                
                logging.info(f"Testing scraper for {website.name}")
                result = scraper.scrape_website(url, max_products=3, test_mode=True)
                
                # Validate results
                products = Product.query.filter_by(website_id=website.id).all()
                logging.info(f"Found {len(products)} products")
                
                # Basic validation
                for product in products:
                    assert product.name, "Product name is required"
                    assert product.url, "Product URL is required"
                    
                results.append({
                    "website": website.name,
                    "success": result.get("success", False),
                    "products": len(products)
                })
                
            except Exception as e:
                logging.error(f"Test failed for {url}: {str(e)}")
                results.append({
                    "website": url,
                    "success": False,
                    "error": str(e)
                })
        
        return results

if __name__ == "__main__":
    results = test_scraper()
    success = all(r.get("success", False) for r in results)
    sys.exit(0 if success else 1)
