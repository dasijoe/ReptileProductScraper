"""
Website model for storing target websites.
"""
from datetime import datetime
from app.models.database import db
from app.utils.hash_utils import generate_hash_id

class Website(db.Model):
    """
    Website model to store information about target websites for scraping.
    """
    __tablename__ = 'websites'
    
    id = db.Column(db.Integer, primary_key=True)
    hash_id = db.Column(db.String(64), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    url = db.Column(db.String(512), nullable=False, unique=True)
    priority = db.Column(db.Integer, default=10)  # Lower number = higher priority
    status = db.Column(db.String(20), default='pending')  # pending, scraping, completed, failed
    
    # Scraping settings
    request_delay = db.Column(db.Float, default=2.0)  # Seconds between requests
    max_products = db.Column(db.Integer, default=100)  # Maximum products to scrape
    
    # Metadata
    last_scraped = db.Column(db.DateTime, nullable=True)
    scrape_success_rate = db.Column(db.Float, default=0.0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    products = db.relationship('Product', back_populates='website', cascade='all, delete-orphan')
    logs = db.relationship('ScrapeLog', back_populates='website', cascade='all, delete-orphan')
    
    def __init__(self, name, url, **kwargs):
        """
        Initialize a website with required fields and generate a hash ID.
        """
        self.name = name
        self.url = url
        self.hash_id = generate_hash_id(url)
        
        # Set other attributes from kwargs
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
    
    @staticmethod
    def find_by_hash_id(hash_id):
        """Find a website by hash ID."""
        return Website.query.filter_by(hash_id=hash_id).first()
    
    @staticmethod
    def find_by_url(url):
        """Find a website by URL."""
        return Website.query.filter_by(url=url).first()
    
    @staticmethod
    def find_all():
        """Get all websites ordered by priority."""
        return Website.query.order_by(Website.priority, Website.name).all()
    
    def update_status(self, status):
        """Update website status and last_scraped if completed."""
        self.status = status
        if status == 'completed':
            self.last_scraped = datetime.utcnow()
        db.session.commit()
    
    def update_success_rate(self, success_count, total_count):
        """Update the scraping success rate."""
        if total_count > 0:
            self.scrape_success_rate = (success_count / total_count) * 100
            db.session.commit()
    
    def to_dict(self):
        """Convert website to dictionary."""
        return {
            'hash_id': self.hash_id,
            'name': self.name,
            'url': self.url,
            'priority': self.priority,
            'status': self.status,
            'request_delay': self.request_delay,
            'max_products': self.max_products,
            'last_scraped': self.last_scraped.isoformat() if self.last_scraped else None,
            'scrape_success_rate': self.scrape_success_rate,
            'product_count': len(self.products) if self.products else 0,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
