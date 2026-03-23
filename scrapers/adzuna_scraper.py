import os
import requests
import asyncio
import logging

logger = logging.getLogger(__name__)

ADZUNA_APP_ID = os.getenv("ADZUNA_APP_ID")
ADZUNA_APP_KEY = os.getenv("ADZUNA_APP_KEY")

def fetch_adzuna_sync(domain: str) -> list[dict]:
    """Fetch jobs from Adzuna APIs synchronously."""
    if not ADZUNA_APP_ID or not ADZUNA_APP_KEY:
        logger.warning("Adzuna credentials not set. Skipping Adzuna scraper.")
        return []
        
    url = f"https://api.adzuna.com/v1/api/jobs/in/search/1"
    params = {
        "app_id": ADZUNA_APP_ID,
        "app_key": ADZUNA_APP_KEY,
        "what": domain,
        "where": "India",
        "results_per_page": 20
    }
    
    try:
        response = requests.get(url, params=params, timeout=15)
        response.raise_for_status()
        data = response.json()
        
        jobs = []
        for result in data.get('results', []):
            jobs.append({
                "title": result.get('title', ''),
                "company": result.get('company', {}).get('display_name', ''),
                "location": result.get('location', {}).get('display_name', 'India'),
                "min_amount": str(result.get('salary_min', '')),
                "max_amount": str(result.get('salary_max', '')),
                "job_url": result.get('redirect_url', ''),
                "site": "adzuna",
                "description": result.get('description', ''),
                "date_posted": result.get('created', '')
            })
        return jobs
    except Exception as e:
        logger.error(f"Adzuna scraping failed for domain '{domain}': {e}")
        return []

async def fetch_jobs_by_domain(domain: str) -> list[dict]:
    """Async wrapper for Adzuna scraper."""
    logger.info(f"Starting Adzuna scraper for {domain}")
    loop = asyncio.get_running_loop()
    jobs = await loop.run_in_executor(None, fetch_adzuna_sync, domain)
    logger.info(f"Adzuna fetched {len(jobs)} jobs for {domain}")
    return jobs
