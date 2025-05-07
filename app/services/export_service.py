"""
Export service for generating data exports.
"""
import os
import csv
import json
import logging
from datetime import datetime
from app.models import Product, Category
from app.config import EXPORT_PATH

class ExportService:
    """
    Service for exporting product data in various formats.
    """
    def __init__(self):
        """
        Initialize the export service.
        """
        os.makedirs(EXPORT_PATH, exist_ok=True)
    
    def export_csv(self, filters=None):
        """
        Export products to CSV format.
        
        Args:
            filters: Optional dictionary of filter parameters
            
        Returns:
            Path to the exported CSV file
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"products_export_{timestamp}.csv"
        filepath = os.path.join(EXPORT_PATH, filename)
        
        try:
            # Get products to export
            products = self._get_products(filters)
            
            # Define CSV fields
            fields = [
                'name', 'description', 'price', 'currency', 'price_zar',
                'url', 'image_url', 'category', 'website', 'confidence_score'
            ]
            
            # Write CSV file
            with open(filepath, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=fields)
                writer.writeheader()
                
                for product in products:
                    product_dict = product.to_dict()
                    # Only include specified fields
                    row = {field: product_dict.get(field, '') for field in fields}
                    writer.writerow(row)
            
            logging.info(f"Exported {len(products)} products to CSV: {filepath}")
            return filepath
            
        except Exception as e:
            logging.error(f"CSV export error: {str(e)}")
            return None
    
    def export_json(self, filters=None):
        """
        Export products to JSON format.
        
        Args:
            filters: Optional dictionary of filter parameters
            
        Returns:
            Path to the exported JSON file
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"products_export_{timestamp}.json"
        filepath = os.path.join(EXPORT_PATH, filename)
        
        try:
            # Get products to export
            products = self._get_products(filters)
            
            # Convert to dictionary list
            products_data = [product.to_dict() for product in products]
            
            # Write JSON file
            with open(filepath, 'w', encoding='utf-8') as jsonfile:
                json.dump(products_data, jsonfile, indent=2, ensure_ascii=False)
            
            logging.info(f"Exported {len(products)} products to JSON: {filepath}")
            return filepath
            
        except Exception as e:
            logging.error(f"JSON export error: {str(e)}")
            return None
    
    def export_facebook_catalog(self, filters=None):
        """
        Export products in Facebook Commerce Manager Catalog format.
        
        Args:
            filters: Optional dictionary of filter parameters
            
        Returns:
            Path to the exported CSV file
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"facebook_catalog_{timestamp}.csv"
        filepath = os.path.join(EXPORT_PATH, filename)
        
        try:
            # Get products to export
            products = self._get_products(filters)
            
            # Define Facebook catalog fields
            fields = [
                'id', 'title', 'description', 'availability', 'condition',
                'price', 'link', 'image_link', 'brand', 'product_type'
            ]
            
            # Write CSV file
            with open(filepath, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=fields)
                writer.writeheader()
                
                for product in products:
                    price_str = f"{product.price_zar:.2f} ZAR" if product.price_zar else ""
                    
                    # Map product to Facebook format
                    row = {
                        'id': product.hash_id,
                        'title': product.name,
                        'description': product.description[:5000] if product.description else "",
                        'availability': 'in stock',
                        'condition': 'new',
                        'price': price_str,
                        'link': product.url,
                        'image_link': product.image_url if product.image_url else "",
                        'brand': product.website.name if product.website else "",
                        'product_type': product.category.name if product.category else "Uncategorized"
                    }
                    writer.writerow(row)
            
            logging.info(f"Exported {len(products)} products to Facebook catalog: {filepath}")
            return filepath
            
        except Exception as e:
            logging.error(f"Facebook catalog export error: {str(e)}")
            return None
    
    def _get_products(self, filters=None):
        """
        Get products based on filters.
        
        Args:
            filters: Optional dictionary of filter parameters
            
        Returns:
            List of Product instances
        """
        # Get all products with valid name and categorized
        query = Product.query.filter(Product.name != None)
        
        # Apply category filter if specified
        if filters and 'category_id' in filters and filters['category_id']:
            query = query.filter(Product.category_id == filters['category_id'])
        
        # Apply website filter if specified
        if filters and 'website_id' in filters and filters['website_id']:
            query = query.filter(Product.website_id == filters['website_id'])
        
        # Apply confidence score filter if specified
        if filters and 'min_confidence' in filters and filters['min_confidence']:
            query = query.filter(Product.confidence_score >= float(filters['min_confidence']))
        
        # Return products ordered by name
        return query.order_by(Product.name).all()
