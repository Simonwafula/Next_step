import logging
import os
import sqlite3
import urllib3
import requests
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urljoin
import time
from ratelimit import limits, sleep_and_retry
from datetime import datetime, timedelta

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Database setup
try:
    conn = sqlite3.connect('db/jobs.sqlite3')
    cursor = conn.cursor()
    logging.info("Database connection established successfully.")
except sqlite3.Error as e:
    logging.error(f"Database connection error: {e}")
    raise

# Create tables
cursor.execute('''
CREATE TABLE IF NOT EXISTS jobs_data (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    full_link TEXT UNIQUE,
    title TEXT,
    content TEXT
)
''')

# Function to insert company data
def insert_data(extracted_data):
    title = extracted_data.get('title', 'N/A')
    full_link = extracted_data.get('full_link')
    content = extracted_data.get('content', 'N/A')
    
    # Ensure the required fields are present
    if not title or not full_link:
        logging.warning(f"Missing required fields for job: {extracted_data}")
        return  # Skip this insertion if critical data is missing

    try:
        with sqlite3.connect('db/jobs.sqlite3') as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR IGNORE INTO jobs_data (title, full_link, content) 
                VALUES (?, ?, ?)
            ''', (title, full_link, content))
            conn.commit()
            logging.info(f"Successfully added job: {title}")

    except sqlite3.Error as e:
        logging.error(f"Error inserting title {title}: {e}")
        conn.rollback()
        return None

# Scraper class to handle the job scraping process
class Scraper:
    def fetch_job_page(self, page_number):
        try:
            url = f"https://www.brightermonday.co.ke/jobs?page={page_number}"
            response = requests.get(url)
            response.raise_for_status()
            logging.info(f"Successfully fetched page {page_number}")
            return response.text
        except requests.RequestException as e:
            logging.error(f"Error fetching page {page_number}: {e}")
            return None

    def scrape(self):
        with ThreadPoolExecutor(max_workers=5) as executor:
            page_numbers = range(1, 131)  # 167 Consider making this dynamic
            results = list(executor.map(self.fetch_job_page, page_numbers))

        for result in results:
            if result:
                soup = BeautifulSoup(result, 'html.parser')
                jobs = soup.find_all('a', class_='relative mb-3 text-lg font-medium break-words focus:outline-none metrics-apply-now text-link-500 text-loading-animate')

                for job in jobs:
                    title = job.get('title', '').strip()
                    link = job.get('href', '')
                    full_link = urljoin('https://www.brightermonday.co.ke', link)

                    try:
                        job_response = requests.get(full_link)
                        job_response.raise_for_status()
                        job_soup = BeautifulSoup(job_response.text, 'html.parser')
                        job_description_html = job_soup.find('article', class_='job__details')
                        if job_description_html:
                            job_description = job_description_html.text.strip()
                            print(job_description)
                            
                            # After extracting job details, insert into the database
                            extracted_data = {
                                'title': title,
                                'full_link': full_link,
                                'content': job_description
                            }
                            insert_data(extracted_data)  # Insert the data into the database
                            
                        else:
                            logging.warning(f"No job description found for {title}")
                            continue

                    except requests.RequestException as e:
                        logging.error(f"Error fetching job details for {title}: {e}")
                    except Exception as e:
                        logging.error(f"Unexpected error processing job {title}: {e}")

        logging.info("Job scraping and insertion complete!")

if __name__ == '__main__':
    try:
        scraper = Scraper()
        scraper.scrape()
    except Exception as e:
        logging.error(f"An unexpected error occurred: {e}")
    finally:
        conn.close()
        logging.info("Database connection closed.")