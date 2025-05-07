"""
Routes for the Reptile Products Scraper application.
"""
import os
import json
import logging
from datetime import datetime
from flask import (
    render_template, redirect, url_for, request, flash, 
    session, jsonify, send_from_directory, Blueprint
)
from functools import wraps
from app import db
from app.config import ADMIN_USERNAME, ADMIN_PASSWORD, EXPORT_PATH
from app.models import Website, Product, Category, ScrapeLog
from app.services.ai_service import AIService
from app.services.scraper_service import ScraperService
from app.services.export_service import ExportService
from app.services.image_service import ImageService
from app.utils.validation import validate_url

# Import API routes
from app.api import register_api_routes

# Initialize services
ai_service = AIService()
image_service = ImageService()
scraper_service = ScraperService(ai_service, image_service)
export_service = ExportService()

# Authentication decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'authenticated' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def register_routes(app):
    """
    Register all routes with the Flask app.
    
    Args:
        app: Flask application instance
    """
    # Register API routes
    register_api_routes(app)
    
    @app.route('/login', methods=['GET', 'POST'])
    def login():
        """Handle login form and authentication."""
        # For debugging, log the username and password from config
        logging.debug(f"Expected credentials from config: {ADMIN_USERNAME} / {ADMIN_PASSWORD}")
        
        if request.method == 'POST':
            username = request.form.get('username')
            password = request.form.get('password')
            
            logging.debug(f"Login attempt: username={username}, password={'*' * len(password) if password else 'None'}")
            
            if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
                session['authenticated'] = True
                session.permanent = True
                flash('Login successful!', 'success')
                return redirect(url_for('dashboard'))
            else:
                flash(f'Invalid credentials. Please try with username: {ADMIN_USERNAME} and password from config.', 'danger')
        
        return render_template('login.html')
    
    @app.route('/logout')
    def logout():
        """Handle user logout."""
        session.pop('authenticated', None)
        flash('You have been logged out.', 'info')
        return redirect(url_for('login'))
    
    @app.route('/')
    @login_required
    def dashboard():
        """Main dashboard view."""
        # Get statistics
        websites_count = Website.query.count()
        products_count = Product.query.count()
        
        # Get recent scrape logs
        recent_logs = ScrapeLog.find_latest()
        
        # Get top websites by product count
        websites = Website.query.all()
        websites_data = [
            {'name': website.name, 'products': len(website.products)} 
            for website in websites
        ]
        websites_data.sort(key=lambda x: x['products'], reverse=True)
        top_websites = websites_data[:5]
        
        # Get category distribution
        categories = Category.query.all()
        category_data = [
            {'name': category.name, 'products': len(category.products)}
            for category in categories
        ]
        category_data.sort(key=lambda x: x['products'], reverse=True)
        
        return render_template(
            'dashboard.html',
            websites_count=websites_count,
            products_count=products_count,
            recent_logs=recent_logs,
            top_websites=top_websites,
            category_data=category_data
        )
    
    @app.route('/websites')
    @login_required
    def websites():
        """Website management view."""
        all_websites = Website.find_all()
        return render_template('websites.html', websites=all_websites)
    
    @app.route('/websites/add', methods=['POST'])
    @login_required
    def add_website():
        """Add a new website."""
        name = request.form.get('name')
        url = request.form.get('url')
        priority = request.form.get('priority', 10)
        
        if not name or not url:
            flash('Name and URL are required.', 'danger')
            return redirect(url_for('websites'))
        
        if not validate_url(url):
            flash('Invalid URL format.', 'danger')
            return redirect(url_for('websites'))
        
        # Check if URL already exists
        existing = Website.find_by_url(url)
        if existing:
            flash('This website URL already exists.', 'warning')
            return redirect(url_for('websites'))
        
        try:
            # Create new website
            website = Website(
                name=name,
                url=url,
                priority=int(priority)
            )
            db.session.add(website)
            db.session.commit()
            
            flash('Website added successfully.', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'Error adding website: {str(e)}', 'danger')
        
        return redirect(url_for('websites'))
    
    @app.route('/websites/edit/<hash_id>', methods=['POST'])
    @login_required
    def edit_website(hash_id):
        """Edit an existing website."""
        website = Website.find_by_hash_id(hash_id)
        if not website:
            flash('Website not found.', 'danger')
            return redirect(url_for('websites'))
        
        name = request.form.get('name')
        url = request.form.get('url')
        priority = request.form.get('priority')
        
        if not name or not url:
            flash('Name and URL are required.', 'danger')
            return redirect(url_for('websites'))
        
        if not validate_url(url):
            flash('Invalid URL format.', 'danger')
            return redirect(url_for('websites'))
        
        try:
            # Update website
            website.name = name
            website.url = url
            website.priority = int(priority)
            
            # Optional fields
            if 'request_delay' in request.form:
                website.request_delay = float(request.form.get('request_delay'))
            
            if 'max_products' in request.form:
                website.max_products = int(request.form.get('max_products'))
            
            db.session.commit()
            flash('Website updated successfully.', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating website: {str(e)}', 'danger')
        
        return redirect(url_for('websites'))
    
    @app.route('/websites/delete/<hash_id>', methods=['POST'])
    @login_required
    def delete_website(hash_id):
        """Delete a website."""
        website = Website.find_by_hash_id(hash_id)
        if not website:
            flash('Website not found.', 'danger')
            return redirect(url_for('websites'))
        
        try:
            db.session.delete(website)
            db.session.commit()
            flash('Website deleted successfully.', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'Error deleting website: {str(e)}', 'danger')
        
        return redirect(url_for('websites'))
    
    @app.route('/scrape/<hash_id>', methods=['POST'])
    @login_required
    def scrape_website(hash_id):
        """Start scraping a website."""
        website = Website.find_by_hash_id(hash_id)
        if not website:
            flash('Website not found.', 'danger')
            return redirect(url_for('websites'))
        
        # Check if already scraping
        if website.status == 'scraping':
            flash('This website is already being scraped.', 'warning')
            return redirect(url_for('websites'))
        
        try:
            # Start scraping in a background thread (would use Celery in production)
            import threading
            thread = threading.Thread(
                target=scraper_service.scrape_website,
                args=(website,)
            )
            thread.daemon = True
            thread.start()
            
            flash(f'Scraping started for {website.name}.', 'success')
        except Exception as e:
            flash(f'Error starting scraper: {str(e)}', 'danger')
        
        return redirect(url_for('websites'))
    
    @app.route('/products')
    @login_required
    def products():
        """Products view with filtering."""
        # Get filter parameters
        category_id = request.args.get('category_id')
        website_id = request.args.get('website_id')
        search_query = request.args.get('q')
        page = int(request.args.get('page', 1))
        
        # Build query
        query = Product.query
        
        if category_id:
            query = query.filter(Product.category_id == category_id)
        
        if website_id:
            query = query.filter(Product.website_id == website_id)
        
        if search_query:
            query = query.filter(Product.name.ilike(f'%{search_query}%'))
        
        # Pagination
        per_page = 20
        products = query.order_by(Product.created_at.desc())\
                       .paginate(page=page, per_page=per_page, error_out=False)
        
        # Get categories and websites for filters
        categories = Category.find_all()
        websites = Website.find_all()
        
        return render_template(
            'products.html',
            products=products,
            categories=categories,
            websites=websites,
            current_category=category_id,
            current_website=website_id,
            search_query=search_query
        )
    
    @app.route('/products/delete/<hash_id>', methods=['POST'])
    @login_required
    def delete_product(hash_id):
        """Delete a product."""
        product = Product.find_by_hash_id(hash_id)
        if not product:
            flash('Product not found.', 'danger')
            return redirect(url_for('products'))
        
        try:
            db.session.delete(product)
            db.session.commit()
            flash('Product deleted successfully.', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'Error deleting product: {str(e)}', 'danger')
        
        return redirect(url_for('products'))
    
    @app.route('/products/category/<hash_id>', methods=['POST'])
    @login_required
    def update_product_category(hash_id):
        """Update a product's category."""
        product = Product.find_by_hash_id(hash_id)
        if not product:
            flash('Product not found.', 'danger')
            return redirect(url_for('products'))
        
        category_id = request.form.get('category_id')
        
        try:
            product.category_id = category_id if category_id else None
            db.session.commit()
            flash('Product category updated.', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating category: {str(e)}', 'danger')
        
        return redirect(url_for('products'))
    
    @app.route('/export', methods=['GET', 'POST'])
    @login_required
    def export():
        """Export view and handling."""
        if request.method == 'POST':
            export_format = request.form.get('format')
            category_id = request.form.get('category_id')
            website_id = request.form.get('website_id')
            min_confidence = request.form.get('min_confidence')
            
            # Build filters
            filters = {}
            if category_id:
                filters['category_id'] = category_id
            
            if website_id:
                filters['website_id'] = website_id
            
            if min_confidence:
                filters['min_confidence'] = min_confidence
            
            # Generate export
            export_path = None
            if export_format == 'csv':
                export_path = export_service.export_csv(filters)
            elif export_format == 'json':
                export_path = export_service.export_json(filters)
            elif export_format == 'facebook':
                export_path = export_service.export_facebook_catalog(filters)
            
            if export_path:
                # Extract filename from path
                filename = os.path.basename(export_path)
                flash(f'Export completed successfully: {filename}', 'success')
                # Return the file for download
                return send_from_directory(
                    directory=EXPORT_PATH,
                    path=filename,
                    as_attachment=True
                )
            else:
                flash('Export failed. Please check logs.', 'danger')
        
        # Get categories and websites for filters
        categories = Category.find_all()
        websites = Website.find_all()
        
        # Get list of existing exports
        try:
            exports = []
            for filename in os.listdir(EXPORT_PATH):
                file_path = os.path.join(EXPORT_PATH, filename)
                if os.path.isfile(file_path):
                    file_stats = os.stat(file_path)
                    file_size = file_stats.st_size / 1024  # Convert to KB
                    file_date = datetime.fromtimestamp(file_stats.st_mtime)
                    
                    exports.append({
                        'filename': filename,
                        'size': f"{file_size:.1f} KB",
                        'date': file_date.strftime("%Y-%m-%d %H:%M")
                    })
            
            # Sort by date (newest first)
            exports.sort(key=lambda x: x['date'], reverse=True)
        except Exception as e:
            logging.error(f"Error listing exports: {str(e)}")
            exports = []
        
        return render_template(
            'export.html',
            categories=categories,
            websites=websites,
            exports=exports
        )
    
    @app.route('/download/<filename>')
    @login_required
    def download_export(filename):
        """Download an export file."""
        return send_from_directory(
            directory=EXPORT_PATH,
            path=filename,
            as_attachment=True
        )
    
    @app.route('/scrape-logs')
    @login_required
    def scrape_logs():
        """View scrape logs."""
        website_id = request.args.get('website_id')
        
        if website_id:
            logs = ScrapeLog.find_by_website_id(website_id)
            current_website = Website.query.get(website_id)
        else:
            logs = ScrapeLog.find_latest()
            current_website = None
        
        websites = Website.find_all()
        
        return render_template(
            'scrape_logs.html',
            logs=logs,
            websites=websites,
            current_website=current_website
        )
    
    @app.route('/api/website-status')
    @login_required
    def website_status():
        """API endpoint for website scraping status."""
        websites = Website.query.all()
        data = [
            {
                'id': website.hash_id,
                'name': website.name,
                'status': website.status,
                'last_scraped': website.last_scraped.isoformat() if website.last_scraped else None,
                'product_count': len(website.products)
            }
            for website in websites
        ]
        return jsonify(data)
