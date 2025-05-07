#!/usr/bin/env python3
"""
Simple test script to demonstrate the API functionality.
This script allows testing the scraping capabilities via API endpoints.
"""
import os
import json
import logging
import requests
import argparse
import time
from urllib.parse import urljoin

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Base URL for API
BASE_URL = "http://localhost:5000/api/"

def setup_websites():
    """Setup target websites in the database."""
    url = urljoin(BASE_URL, "setupWebsites")
    try:
        response = requests.post(url)
        data = response.json()
        
        if data.get('success'):
            logger.info(f"Setup successful: {data.get('message')}")
        else:
            logger.error(f"Setup failed: {data.get('error')}")
        
        return data
    except Exception as e:
        logger.error(f"Error setting up websites: {str(e)}")
        return {"success": False, "error": str(e)}

def get_websites():
    """Get all websites from the API."""
    url = urljoin(BASE_URL, "websites")
    try:
        response = requests.get(url)
        data = response.json()
        
        if data.get('success'):
            websites = data.get('websites', [])
            logger.info(f"Retrieved {len(websites)} websites")
            
            # Print website details
            for i, website in enumerate(websites[:5], 1):  # Show first 5 for brevity
                logger.info(f"{i}. {website['name']} - {website['status']} - {website['url']}")
            
            if len(websites) > 5:
                logger.info(f"...and {len(websites) - 5} more")
        else:
            logger.error(f"Failed to retrieve websites: {data.get('error')}")
        
        return data
    except Exception as e:
        logger.error(f"Error retrieving websites: {str(e)}")
        return {"success": False, "error": str(e)}

def get_website_status_summary():
    """Get summary of website statuses."""
    url = urljoin(BASE_URL, "websiteStatusSummary")
    try:
        response = requests.get(url)
        data = response.json()
        
        if data.get('success'):
            websites = data.get('websites', {})
            products = data.get('products', {})
            categories = data.get('categories', {})
            
            logger.info("Website Status Summary:")
            logger.info(f"Total websites: {websites.get('total', 0)}")
            logger.info(f"Status counts: {websites.get('by_status', {})}")
            logger.info(f"Total products: {products.get('total', 0)}")
            logger.info(f"Categories with products: {categories.get('with_products', 0)} of {categories.get('total', 0)}")
            
            # Show top categories
            top_categories = categories.get('data', [])[:5]
            for cat in top_categories:
                logger.info(f"Category: {cat['name']} - {cat['product_count']} products")
        else:
            logger.error(f"Failed to retrieve status summary: {data.get('error')}")
        
        return data
    except Exception as e:
        logger.error(f"Error retrieving status summary: {str(e)}")
        return {"success": False, "error": str(e)}

def scrape_website(url, max_products=10):
    """Trigger scraping for a specific website."""
    api_url = urljoin(BASE_URL, "scrapeWebsite")
    payload = {
        "url": url,
        "max_products": max_products
    }
    
    try:
        logger.info(f"Starting scrape for {url} with max {max_products} products")
        response = requests.post(api_url, json=payload)
        data = response.json()
        
        if data.get('success'):
            logger.info(f"Scraping initiated successfully")
            logger.info(f"Results: {json.dumps(data, indent=2)}")
        else:
            logger.error(f"Scraping failed: {data.get('error')}")
        
        return data
    except Exception as e:
        logger.error(f"Error triggering scrape: {str(e)}")
        return {"success": False, "error": str(e)}

def get_products(limit=10, offset=0, category_id=None, website_id=None):
    """Get products with optional filtering."""
    url = urljoin(BASE_URL, "products")
    params = {
        "limit": limit,
        "offset": offset
    }
    
    if category_id:
        params["category_id"] = category_id
    
    if website_id:
        params["website_id"] = website_id
    
    try:
        response = requests.get(url, params=params)
        data = response.json()
        
        if data.get('success'):
            products = data.get('products', [])
            pagination = data.get('pagination', {})
            
            logger.info(f"Retrieved {len(products)} products (total: {pagination.get('total', 0)})")
            
            # Print product details
            for i, product in enumerate(products, 1):
                logger.info(f"{i}. {product['name']} - {product.get('price_zar', 'N/A')} ZAR")
                logger.info(f"   Category: {product.get('category_name', 'Uncategorized')}")
                logger.info(f"   URL: {product.get('url', 'N/A')}")
                logger.info(f"   Image: {product.get('image_url', 'N/A')}")
                logger.info("---")
        else:
            logger.error(f"Failed to retrieve products: {data.get('error')}")
        
        return data
    except Exception as e:
        logger.error(f"Error retrieving products: {str(e)}")
        return {"success": False, "error": str(e)}

def main():
    """Main function to run API tests."""
    parser = argparse.ArgumentParser(description='Test API endpoints for Reptile Products Scraper')
    parser.add_argument('--action', choices=['setup', 'websites', 'summary', 'scrape', 'products'], 
                        default='summary', help='Action to perform')
    parser.add_argument('--url', help='Website URL to scrape (required for scrape action)')
    parser.add_argument('--max', type=int, default=10, help='Maximum products to scrape')
    parser.add_argument('--limit', type=int, default=10, help='Limit for product retrieval')
    parser.add_argument('--offset', type=int, default=0, help='Offset for product retrieval')
    parser.add_argument('--category', help='Category ID for filtering products')
    parser.add_argument('--website', help='Website ID for filtering products')
    
    args = parser.parse_args()
    
    if args.action == 'setup':
        setup_websites()
    elif args.action == 'websites':
        get_websites()
    elif args.action == 'summary':
        get_website_status_summary()
    elif args.action == 'scrape':
        if not args.url:
            logger.error("URL parameter is required for scrape action")
            return
        scrape_website(args.url, args.max)
    elif args.action == 'products':
        get_products(args.limit, args.offset, args.category, args.website)

if __name__ == "__main__":
    main()