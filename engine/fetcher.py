import asyncio
import logging
import uuid
from datetime import datetime
from scrapers.jobspy_scraper import fetch_jobs_by_domain as fetch_jobspy
from scrapers.adzuna_scraper import fetch_jobs_by_domain as fetch_adzuna
from scrapers.rss_scraper import fetch_rss_jobs
from database.db import get_db
from config import JOB_DOMAINS

logger = logging.getLogger(__name__)

async def filter_new_jobs(jobs: list[dict]) -> list[dict]:
    """Filters out jobs whose URL is already in the posted_jobs table."""
    if not jobs:
        return []
        
    urls = [job['job_url'] for job in jobs if job.get('job_url')]
    if not urls:
        return []
        
    async with get_db() as db:
        # We can do this in batches or one query. For SQLite with small list, one query is fine.
        placeholders = ','.join(['?'] * len(urls))
        async with db.execute(f"SELECT url FROM posted_jobs WHERE url IN ({placeholders})", urls) as cursor:
            rows = await cursor.fetchall()
            existing_urls = {row['url'] for row in rows}
            
    # Filter the jobs
    new_jobs = [job for job in jobs if job.get('job_url') and job['job_url'] not in existing_urls]
    return new_jobs
    
async def mark_jobs_as_posted(jobs: list[dict]):
    """Insert newly fetched and verified jobs into posted_jobs and jobs table."""
    # (Optional based on design: you might wait to mark them until actually sent to users.
    # But for a general deduplication, marking them as we fetch/store them makes sense)
    async with get_db() as db:
        for job in jobs:
            url = job['job_url']
            # Inserting into deduplication table
            await db.execute("INSERT OR IGNORE INTO posted_jobs (url, posted_at) VALUES (?, CURRENT_TIMESTAMP)", (url,))
            
            # Inserting into main jobs table
            job_id = str(uuid.uuid4())
            await db.execute('''
                INSERT OR IGNORE INTO jobs (id, title, company, location, salary, work_type, experience, url, source_portal, domain, score, posted_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                job_id, job['title'], job['company'], job['location'], 
                f"{job['min_amount']} - {job['max_amount']}", "Any", "Any", 
                url, job['site'], job.get('domain', 'general'), 0, job['date_posted'] or datetime.utcnow().isoformat()
            ))
            
            # Note: We assign a random UUID since the jobs table schema expects an `id` TEXT PRIMARY KEY.
            # We also attach the domain below in `fetch_all_jobs` before calling this.
            
        await db.commit()

async def fetch_all_jobs() -> list[dict]:
    """Orchestrates fetching from all scrapers concurrently and deduplicating."""
    logger.info("Starting engine.fetch_all_jobs...")
    all_jobs = []
    
    # Create a Semaphore to limit concurrent requests to 4 at a time
    # This prevents 429 Too Many Requests and Telegram Event Loop Starvation
    semaphore = asyncio.Semaphore(4)
    
    async def bounded_fetch(func, *args):
        async with semaphore:
            # Stagger requests slightly to avoid sharp spikes
            await asyncio.sleep(0.5)
            try:
                return await func(*args)
            except Exception as e:
                logger.error(f"Error executing {func.__name__} with {args}: {e}")
                return []

    tasks = []
    for domain in JOB_DOMAINS:
        tasks.append(bounded_fetch(fetch_jobspy, domain))
        tasks.append(bounded_fetch(fetch_adzuna, domain))
        
    # RSS doesn't take domain args
    tasks.append(bounded_fetch(fetch_rss_jobs))
    
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Process results
    jobspy_count = 0
    adzuna_count = 0
    rss_count = 0
    
    idx = 0
    for domain in JOB_DOMAINS:
        # JobSpy Result
        res_jobspy = results[idx]
        idx += 1
        if isinstance(res_jobspy, list):
            for job in res_jobspy:
                job['domain'] = domain
            all_jobs.extend(res_jobspy)
            jobspy_count += len(res_jobspy)
            
        # Adzuna Result
        res_adzuna = results[idx]
        idx += 1
        if isinstance(res_adzuna, list):
            for job in res_adzuna:
                job['domain'] = domain
            all_jobs.extend(res_adzuna)
            adzuna_count += len(res_adzuna)
            
    # RSS Result
    res_rss = results[idx]
    if isinstance(res_rss, list):
        for job in res_rss:
            job['domain'] = 'remote'
        all_jobs.extend(res_rss)
        rss_count += len(res_rss)
        
    logger.info(f"Scraping complete. JobSpy: {jobspy_count}, Adzuna: {adzuna_count}, RSS: {rss_count}")
    
    # Deduplicate within the fetched list itself by URL
    unique_jobs = {}
    for job in all_jobs:
        url = job.get('job_url')
        if url and url not in unique_jobs:
            unique_jobs[url] = job
            
    # Filter against DB
    new_jobs = await filter_new_jobs(list(unique_jobs.values()))
    logger.info(f"Total Unique New Jobs found: {len(new_jobs)}")
    
    # Mark in DB so we don't fetch them again next time
    await mark_jobs_as_posted(new_jobs)
    
    return new_jobs
