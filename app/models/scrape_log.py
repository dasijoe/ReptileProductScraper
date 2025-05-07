"""
ScrapeLog model for storing scraping operation logs.
"""
from datetime import datetime
from app.models.database import db
from app.utils.hash_utils import generate_hash_id

class ScrapeLog(db.Model):
    """
    ScrapeLog model to track details of scraping operations.
    """
    __tablename__ = 'scrape_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    hash_id = db.Column(db.String(64), unique=True, nullable=False)
    website_id = db.Column(db.Integer, db.ForeignKey('websites.id'), nullable=False)
    
    # Scrape details
    start_time = db.Column(db.DateTime, default=datetime.utcnow)
    end_time = db.Column(db.DateTime, nullable=True)
    status = db.Column(db.String(20), default='running')  # running, completed, failed
    products_found = db.Column(db.Integer, default=0)
    products_scraped = db.Column(db.Integer, default=0)
    products_failed = db.Column(db.Integer, default=0)
    
    # Performance metrics
    avg_request_time = db.Column(db.Float, nullable=True)
    total_request_count = db.Column(db.Integer, default=0)
    
    # Log details
    error_message = db.Column(db.Text, nullable=True)
    log_details = db.Column(db.Text, nullable=True)  # JSON string with detailed log
    
    # Relationships
    website = db.relationship('Website', back_populates='logs')
    
    def __init__(self, website_id, **kwargs):
        """
        Initialize a scrape log with required fields and generate a hash ID.
        """
        self.website_id = website_id
        self.hash_id = generate_hash_id(f"{website_id}-{datetime.utcnow().isoformat()}")
        
        # Set other attributes from kwargs
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
    
    @staticmethod
    def find_by_hash_id(hash_id):
        """Find a scrape log by hash ID."""
        return ScrapeLog.query.filter_by(hash_id=hash_id).first()
    
    @staticmethod
    def find_by_website_id(website_id, limit=10):
        """Find scrape logs for a specific website."""
        return ScrapeLog.query.filter_by(website_id=website_id)\
                           .order_by(ScrapeLog.start_time.desc())\
                           .limit(limit).all()
    
    @staticmethod
    def find_latest():
        """Find the most recent scrape logs."""
        return ScrapeLog.query.order_by(ScrapeLog.start_time.desc()).limit(10).all()
    
    def update_stats(self, **stats):
        """Update scraping statistics."""
        for key, value in stats.items():
            if hasattr(self, key):
                setattr(self, key, value)
        db.session.commit()
    
    def complete(self, success=True):
        """Mark the scraping operation as complete."""
        self.end_time = datetime.utcnow()
        self.status = 'completed' if success else 'failed'
        db.session.commit()
    
    def to_dict(self):
        """Convert scrape log to dictionary."""
        return {
            'hash_id': self.hash_id,
            'website': self.website.name if self.website else None,
            'start_time': self.start_time.isoformat() if self.start_time else None,
            'end_time': self.end_time.isoformat() if self.end_time else None,
            'status': self.status,
            'products_found': self.products_found,
            'products_scraped': self.products_scraped,
            'products_failed': self.products_failed,
            'avg_request_time': self.avg_request_time,
            'total_request_count': self.total_request_count,
            'error_message': self.error_message,
            'duration': str(self.end_time - self.start_time) if self.end_time else None
        }
