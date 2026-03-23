import sys
import asyncio
import logging
from jobspy import scrape_jobs

logger = logging.getLogger(__name__)

def scrape_jobs_sync(domain: str) -> list[dict]:
    """Blocking function to scrape jobs using jobspy."""
    # jobspy doesn't fully support naukri natively in some versions, but we add standard ones.
    sites = ["indeed", "linkedin", "glassdoor", "google"]
    
    try:
        # jobspy returns a pandas DataFrame
        jobs_df = scrape_jobs(
            site_name=sites,
            search_term=domain,
            location="India",
            results_wanted=20,
            country_indeed='India'
        )
        
        if jobs_df is None or jobs_df.empty:
            return []
            
        jobs = []
        # Convert DataFrame to list of dicts with standard keys
        for _, row in jobs_df.iterrows():
            jobs.append({
                "title": str(row.get('title', '')),
                "company": str(row.get('company', '')),
                "location": str(row.get('location', 'India')),
                "min_amount": str(row.get('min_amount', '')),
                "max_amount": str(row.get('max_amount', '')),
                "job_url": str(row.get('job_url', '')),
                "site": str(row.get('site', 'jobspy')),
                "description": str(row.get('description', '')),
                "date_posted": str(row.get('date_posted', '')),
            })
        return jobs
    except Exception as e:
        logger.error(f"Error in jobspy scraper for domain '{domain}': {e}")
        return []

async def fetch_jobs_by_domain(domain: str) -> list[dict]:
    """Async wrapper for jobspy scraper."""
    # Backoff could be implemented here, but we'll just run it in a thread
    logger.info(f"Starting JobSpy scraper for {domain}")
    loop = asyncio.get_running_loop()
    jobs = await loop.run_in_executor(None, scrape_jobs_sync, domain)
    logger.info(f"JobSpy fetched {len(jobs)} jobs for {domain}")
    return jobs
