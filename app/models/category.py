"""
Category model for organizing products.
"""
from app.models.database import db
from app.utils.hash_utils import generate_hash_id

class Category(db.Model):
    """
    Category model to organize products into groups.
    """
    __tablename__ = 'categories'
    
    id = db.Column(db.Integer, primary_key=True)
    hash_id = db.Column(db.String(64), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False, unique=True)
    description = db.Column(db.Text, nullable=True)
    parent_id = db.Column(db.Integer, db.ForeignKey('categories.id'), nullable=True)
    
    # Relationships
    products = db.relationship('Product', back_populates='category')
    subcategories = db.relationship('Category', 
                                   backref=db.backref('parent', remote_side=[id]),
                                   cascade='all, delete-orphan')
    
    def __init__(self, name, **kwargs):
        """
        Initialize a category with required fields and generate a hash ID.
        """
        self.name = name
        self.hash_id = generate_hash_id(name)
        
        # Set other attributes from kwargs
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
    
    @staticmethod
    def find_by_hash_id(hash_id):
        """Find a category by hash ID."""
        return Category.query.filter_by(hash_id=hash_id).first()
    
    @staticmethod
    def find_by_name(name):
        """Find a category by name."""
        return Category.query.filter_by(name=name).first()
    
    @staticmethod
    def find_all():
        """Get all categories."""
        return Category.query.all()
    
    def has_subcategories(self):
        """Check if category has subcategories."""
        return len(self.subcategories) > 0
    
    def to_dict(self):
        """Convert category to dictionary."""
        return {
            'hash_id': self.hash_id,
            'name': self.name,
            'description': self.description,
            'parent_id': self.parent_id,
            'product_count': len(self.products) if self.products else 0,
            'subcategories': [subcategory.to_dict() for subcategory in self.subcategories] if self.has_subcategories() else []
        }
