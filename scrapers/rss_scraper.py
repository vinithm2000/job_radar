import feedparser
import asyncio
import logging

logger = logging.getLogger(__name__)

RSS_FEEDS = [
    "https://remoteok.com/remote-jobs.rss",
    "https://weworkremotely.com/remote-jobs.rss"
]

def fetch_rss_sync() -> list[dict]:
    jobs = []
    
    for feed_url in RSS_FEEDS:
        try:
            feed = feedparser.parse(feed_url)
            for entry in feed.entries[:20]: # limit to 20 for matching limits
                jobs.append({
                    "title": entry.get('title', ''),
                    "company": "", # RSS feeds sometimes bundle company in title
                    "location": "Remote",
                    "min_amount": "",
                    "max_amount": "",
                    "job_url": entry.get('link', ''),
                    "site": "rss_feed",
                    "description": entry.get('description', ''),
                    "date_posted": entry.get('published', '')
                })
        except Exception as e:
            logger.error(f"Failed to parse RSS feed {feed_url}: {e}")
            
    return jobs

async def fetch_rss_jobs() -> list[dict]:
    logger.info(f"Starting RSS scraper for remote jobs")
    loop = asyncio.get_running_loop()
    jobs = await loop.run_in_executor(None, fetch_rss_sync)
    logger.info(f"RSS fetched {len(jobs)} jobs")
    return jobs
