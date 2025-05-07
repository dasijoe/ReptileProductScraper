"""
Simple script to check if the Ultimate Exotics website is accessible.
This will verify that we can connect to the target website before starting the scraper.
"""
import requests
import random
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

def check_website():
    """Check if the Ultimate Exotics website is accessible."""
    # Use random user agent to avoid looking like a bot
    user_agents = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0'
    ]
    
    headers = {
        'User-Agent': random.choice(user_agents),
        'Accept': 'text/html,application/xhtml+xml,application/xml',
        'Accept-Language': 'en-US,en;q=0.9',
    }
    
    with app.app_context():
        # Get website from database
        website = Website.query.filter_by(url='https://ultimateexotics.co.za/shop/').first()
        
        if not website:
            logging.info("Website not found in database, creating entry...")
            website = Website(
                name='Ultimate Exotics',
                url='https://ultimateexotics.co.za/shop/',
                priority=1,
                request_delay=3.0,
                max_products=20
            )
            db.session.add(website)
            db.session.commit()
            logging.info(f"Created website entry with ID: {website.id}")
        else:
            logging.info(f"Found website: {website.name} with hash_id: {website.hash_id}")
        
        # Try to access the website
        try:
            logging.info(f"Checking website accessibility: {website.url}")
            response = requests.get(website.url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                logging.info(f"Website is accessible! Status code: {response.status_code}")
                website.status = 'pending'  # Reset status to pending
                website.updated_at = datetime.utcnow()
                db.session.commit()
                return True
            else:
                logging.warning(f"Website returned non-200 status code: {response.status_code}")
                return False
                
        except requests.RequestException as e:
            logging.error(f"Error accessing website: {str(e)}")
            return False

if __name__ == "__main__":
    check_website()