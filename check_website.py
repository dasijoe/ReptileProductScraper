from app import app
from app.models import Website

with app.app_context():
    website = Website.query.filter_by(url='https://ultimateexotics.co.za/shop/').first()
    if website:
        print(f'Found website: {website.name} with hash_id: {website.hash_id}')
    else:
        print('Website not found in database')