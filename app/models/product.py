"""
Product model for storing product data.
"""
from datetime import datetime
from app.models.database import db
from app.utils.hash_utils import generate_hash_id

class Product(db.Model):
    """
    Product model to store product information scraped from websites.
    """
    __tablename__ = 'products'
    
    id = db.Column(db.Integer, primary_key=True)
    hash_id = db.Column(db.String(64), unique=True, nullable=False)
    name = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=True)
    price = db.Column(db.Float, nullable=True)
    currency = db.Column(db.String(3), nullable=True, default='ZAR')
    price_zar = db.Column(db.Float, nullable=True)
    url = db.Column(db.String(512), nullable=True)
    image_url = db.Column(db.String(512), nullable=True)
    image_path = db.Column(db.String(512), nullable=True)
    
    # Foreign keys
    website_id = db.Column(db.Integer, db.ForeignKey('websites.id'), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id'), nullable=True)
    
    # Metadata
    confidence_score = db.Column(db.Float, default=0.0)  # AI confidence in categorization
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    website = db.relationship('Website', back_populates='products')
    category = db.relationship('Category', back_populates='products')
    
    def __init__(self, name, website_id, **kwargs):
        """
        Initialize a product with required fields and generate a hash ID.
        """
        self.name = name
        self.website_id = website_id
        self.hash_id = generate_hash_id(f"{name}-{website_id}")
        
        # Set other attributes from kwargs
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
    
    @staticmethod
    def find_by_hash_id(hash_id):
        """Find a product by hash ID."""
        return Product.query.filter_by(hash_id=hash_id).first()
    
    @staticmethod
    def find_by_url(url):
        """Find a product by URL to prevent duplicates."""
        return Product.query.filter_by(url=url).first()
    
    @staticmethod
    def find_all(limit=100, offset=0, **filters):
        """Find products with optional filters."""
        query = Product.query
        
        # Apply filters
        for key, value in filters.items():
            if hasattr(Product, key) and value is not None:
                query = query.filter(getattr(Product, key) == value)
        
        # Apply pagination
        return query.order_by(Product.created_at.desc()).limit(limit).offset(offset).all()
    
    def to_dict(self):
        """Convert product to dictionary for export."""
        return {
            'hash_id': self.hash_id,
            'name': self.name,
            'description': self.description,
            'price': self.price,
            'currency': self.currency,
            'price_zar': self.price_zar,
            'url': self.url,
            'image_url': self.image_url,
            'image_path': self.image_path,
            'category': self.category.name if self.category else 'Uncategorized',
            'website': self.website.name,
            'confidence_score': self.confidence_score,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
