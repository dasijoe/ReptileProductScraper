"""
Script to run scrapers for multiple reptile product websites.
This implements minimal functionality with anti-ban protections to start harvesting data.
"""
import logging
import time
import os
import sys
import random
import subprocess
import threading
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("scrape_process.log"),
        logging.StreamHandler(sys.stdout)
    ]
)

# Ensure directories exist
def create_directories():
    """Create necessary directories for storing data and logs."""
    os.makedirs("data/images", exist_ok=True)
    os.makedirs("data/exports", exist_ok=True)
    logging.info("Created necessary directories")
    
def run_scraper(script_name, website_name):
    """Run a scraper script as a subprocess and monitor its output."""
    logging.info(f"Starting scraper for {website_name} using {script_name}")
    
    # Use a unique log file for each scraper
    log_file = f"{website_name.lower().replace(' ', '_')}_scrape.log"
    
    try:
        # Start the process
        process = subprocess.Popen(
            ["python", script_name],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            bufsize=1
        )
        
        # Write PID to file for monitoring
        with open(f"{website_name.lower().replace(' ', '_')}_pid.txt", "w") as f:
            f.write(f"{process.pid}")
        
        # Monitor and log output
        with open(log_file, "a") as log:
            log.write(f"\n\n==== NEW SCRAPE RUN STARTED AT {datetime.now()} ====\n\n")
            
            for line in process.stdout:
                # Write to both the specific log file and the main log
                log.write(line)
                log.flush()
                logging.info(f"[{website_name}] {line.strip()}")
        
        # Wait for process to complete
        return_code = process.wait()
        logging.info(f"Scraper for {website_name} completed with return code {return_code}")
        
        # Remove PID file
        if os.path.exists(f"{website_name.lower().replace(' ', '_')}_pid.txt"):
            os.remove(f"{website_name.lower().replace(' ', '_')}_pid.txt")
            
        return return_code == 0
        
    except Exception as e:
        logging.error(f"Error running scraper for {website_name}: {str(e)}")
        return False

def setup_and_run():
    """Setup database and run scrapers for all websites."""
    # Initialize directories
    create_directories()
    
    # First add websites to database
    logging.info("Setting up websites in database")
    from setup_websites import setup_all_websites
    setup_all_websites()
    
    # Run scraper for Ultimate Exotics
    ue_success = run_scraper("scrape_ultimateexotics.py", "Ultimate Exotics")
    
    # Run scraper for Reptile Garden
    rg_success = run_scraper("scrape_reptilegarden.py", "Reptile Garden")
    
    # Log final results
    logging.info("===== SCRAPING SUMMARY =====")
    logging.info(f"Ultimate Exotics: {'SUCCESS' if ue_success else 'FAILED'}")
    logging.info(f"Reptile Garden: {'SUCCESS' if rg_success else 'FAILED'}")
    
    return ue_success or rg_success

if __name__ == "__main__":
    print("===== STARTING REPTILE PRODUCT SCRAPERS =====")
    print("This script will scrape multiple websites for reptile products with anti-ban protections.")
    
    # Run setup and scrapers
    start_time = time.time()
    success = setup_and_run()
    elapsed = time.time() - start_time
    
    print(f"\nTotal execution time: {elapsed:.2f} seconds")
    print("Check scrape_process.log for detailed information")
    
    sys.exit(0 if success else 1)