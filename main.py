"""
Main entry point for the Reptile Products Scraper application.
"""
from app import app

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
