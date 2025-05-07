"""
API routes for the Reptile Products Scraper application.
These endpoints allow direct control of the application via HTTP API.
"""
import os
import json
import logging
from flask import Blueprint, request, jsonify, current_app
from datetime import datetime

from app import db
from app.models.website import Website
from app.models.product import Product
from app.models.category import Category
from app.models.scrape_log import ScrapeLog
from app.services.ai_service import AIService
from app.services.image_service import ImageService
from app.services.direct_scraper import DirectScraper

# Create blueprint
api_bp = Blueprint('api', __name__, url_prefix='/api')

# Initialize services
ai_service = AIService()
image_service = ImageService()
direct_scraper = DirectScraper(ai_service, image_service)

@api_bp.route('/websites', methods=['GET'])
def get_websites():
    """Get all websites."""
    websites = Website.query.all()
    return jsonify({
        'success': True,
        'websites': [w.to_dict() for w in websites]
    })

@api_bp.route('/websiteStatusSummary', methods=['GET'])
def get_website_status_summary():
    """Get status summary of all websites."""
    # Count websites by status
    status_counts = {
        'pending': 0,
        'completed': 0,
        'failed': 0,
        'scraping': 0
    }
    
    # Get all website statuses
    websites = Website.query.all()
    for website in websites:
        if website.status in status_counts:
            status_counts[website.status] += 1
    
    # Count products
    product_count = Product.query.count()
    
    # Count categories with products
    categories = Category.query.all()
    categories_with_products = 0
    categories_data = []
    
    for category in categories:
        product_count_in_category = Product.query.filter_by(category_id=category.id).count()
        categories_data.append({
            'name': category.name,
            'product_count': product_count_in_category
        })
        if product_count_in_category > 0:
            categories_with_products += 1
    
    # Sort categories by product count (descending)
    categories_data.sort(key=lambda x: x['product_count'], reverse=True)
    
    return jsonify({
        'success': True,
        'websites': {
            'total': len(websites),
            'by_status': status_counts
        },
        'products': {
            'total': product_count
        },
        'categories': {
            'total': len(categories),
            'with_products': categories_with_products,
            'data': categories_data
        }
    })

@api_bp.route('/setupWebsites', methods=['POST'])
def setup_websites():
    """Setup target websites in the database."""
    from app.config import TARGET_WEBSITES, PRODUCT_CATEGORIES
    
    # Create categories
    categories_created = 0
    for name in PRODUCT_CATEGORIES:
        category = Category.query.filter_by(name=name).first()
        if not category:
            category = Category(name=name)
            db.session.add(category)
            categories_created += 1
    
    # Create websites
    websites_created = 0
    for url in TARGET_WEBSITES:
        website = Website.query.filter_by(url=url).first()
        if not website:
            # Extract domain name for the website name
            import urllib.parse
            domain = urllib.parse.urlparse(url).netloc
            # Clean up domain name
            if domain.startswith('www.'):
                domain = domain[4:]
            # Convert domain to title case
            name = ' '.join(w.capitalize() for w in domain.split('.')[0].split('-'))
            
            website = Website(
                name=name,
                url=url,
                priority=websites_created + 1
            )
            db.session.add(website)
            websites_created += 1
    
    db.session.commit()
    
    return jsonify({
        'success': True,
        'categories_created': categories_created,
        'websites_created': websites_created,
        'message': f'Setup complete: {categories_created} categories and {websites_created} websites created'
    })

@api_bp.route('/scrapeWebsite', methods=['POST'])
def scrape_website():
    """Trigger website scraping."""
    data = request.json
    
    if not data or 'url' not in data:
        return jsonify({
            'success': False,
            'error': 'Missing required parameter: url'
        }), 400
    
    website_url = data['url']
    max_products = data.get('max_products', 10)
    
    # Verify the URL exists in our database
    website = Website.query.filter_by(url=website_url).first()
    if not website:
        return jsonify({
            'success': False,
            'error': f'Website not found in database: {website_url}'
        }), 404
    
    # Check if website is already being scraped
    if website.status == 'scraping':
        return jsonify({
            'success': False,
            'error': f'Website is already being scraped: {website.name}'
        }), 409
    
    # Start scraping
    try:
        result = direct_scraper.scrape_website(website_url, max_products)
        return jsonify(result)
    except Exception as e:
        logging.error(f"Error scraping website: {str(e)}")
        import traceback
        logging.error(traceback.format_exc())
        
        return jsonify({
            'success': False,
            'error': str(e),
            'website': website.name,
            'website_url': website.url
        }), 500

@api_bp.route('/products', methods=['GET'])
def get_products():
    """Get products with optional filtering."""
    # Temporarily removed auth check for debugging
    """Get products with optional filtering."""
    # Get query parameters
    category_id = request.args.get('category_id')
    website_id = request.args.get('website_id')
    limit = int(request.args.get('limit', 20))
    offset = int(request.args.get('offset', 0))
    
    # Build query
    query = Product.query
    
    if category_id:
        query = query.filter_by(category_id=category_id)
    
    if website_id:
        query = query.filter_by(website_id=website_id)
    
    # Get total count for pagination
    total_count = query.count()
    
    # Apply pagination
    products = query.order_by(Product.created_at.desc()).limit(limit).offset(offset).all()
    
    return jsonify({
        'success': True,
        'products': [p.to_dict() for p in products],
        'pagination': {
            'total': total_count,
            'limit': limit,
            'offset': offset,
            'has_more': (offset + limit) < total_count
        }
    })

@api_bp.route('/categories', methods=['GET'])
def get_categories():
    """Get all categories."""
    categories = Category.query.all()
    return jsonify({
        'success': True,
        'categories': [c.to_dict() for c in categories]
    })

def register_api_routes(app):
    """Register API routes with Flask app."""
    app.register_blueprint(api_bp)
    logging.info("API routes registered")