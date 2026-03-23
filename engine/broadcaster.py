import asyncio
import logging
import os
from telegram import Bot
from database.db import get_db
from utils.formatter import format_job_card, format_morning_digest

logger = logging.getLogger(__name__)

CHANNEL_ID = os.getenv("CHANNEL_ID", "")

async def get_matching_users(job: dict) -> list[dict]:
    """Find users whose preferences match the job."""
    # This queries job_preferences table for domains matching the job's domain.
    # In a real heavy-load scenario, reverse index or caching is used.
    # We'll do a basic fetch and filter in python for simplicity.
    matched = []
    
    async with get_db() as db:
        async with db.execute("SELECT u.user_id, p.domains, p.work_type, p.experience_years, p.preferred_location FROM users u JOIN job_preferences p ON u.user_id = p.user_id WHERE u.is_active = 1") as cursor:
            users = await cursor.fetchall()
            
    job_domain = str(job.get('domain', '')).lower()
    job_loc = str(job.get('location', '')).lower()
    job_wt = str(job.get('work_type', '')).lower()
    
    for u in users:
        # Check domain
        if job_domain and u['domains']:
            if job_domain not in str(u['domains']).lower():
                continue
                
        # Match location (Supports multiple comma-separated locations)
        user_pref_loc = str(u['preferred_location']).lower()
        if user_pref_loc and user_pref_loc != 'any':
            pref_locs = [l.strip() for l in user_pref_loc.split(',') if l.strip()]
            
            # Check if ANY of the user's preferred locations exist in the job location
            if not any(loc_part in job_loc for loc_part in pref_locs):
                continue
            
        matched.append(u)
        
    return matched

async def broadcast_jobs(bot: Bot, new_jobs: list[dict]):
    """Broadcasts jobs to matched users and channels."""
    logger.info(f"Broadcasting {len(new_jobs)} new jobs.")
    
    for job in new_jobs:
        users = await get_matching_users(job)
        if not users:
            continue
            
        text, markup = format_job_card(job)
        sent_count = 0
        
        for u in users:
            try:
                await bot.send_message(
                    chat_id=u['user_id'], 
                    text=text, 
                    reply_markup=markup, 
                    parse_mode='HTML',
                    disable_web_page_preview=True
                )
                sent_count += 1
                await asyncio.sleep(0.05) # Rate limiting delay
            except Exception as e:
                logger.error(f"Failed to send to user {u['user_id']}: {e}")
                # Optional: deactivate user if bot blocked
                
        logger.info(f"Sent {job.get('title')} to {sent_count} users")
        
        # Post to channel if score >= 8 (AI score stub)
        # Note: AI features in future as per requirements
        score = job.get('score', 0)
        if score >= 8 and CHANNEL_ID:
            try:
                await bot.send_message(
                    chat_id=CHANNEL_ID,
                    text=text,
                    reply_markup=markup,
                    parse_mode='HTML',
                    disable_web_page_preview=True
                )
            except Exception as e:
                logger.error(f"Failed to post to channel: {e}")

async def send_morning_digest(bot: Bot):
    """Sends top 10 jobs from the last 24hrs to all active users."""
    logger.info("Generating Morning Digest...")
    
    async with get_db() as db:
        # Fetch top 10 jobs ordered by score
        async with db.execute("SELECT * FROM jobs WHERE datetime(posted_at) >= datetime('now', '-1 day') ORDER BY score DESC LIMIT 10") as cursor:
            top_jobs = await cursor.fetchall()
            
        async with db.execute("SELECT user_id FROM users WHERE is_active = 1") as cursor:
            users = await cursor.fetchall()
            
    if not top_jobs:
        logger.info("No jobs to generate digest. Skipping.")
        return
        
    # Standard DB row objects must be converted to dict for formatter
    jobs_list = [dict(row) for row in top_jobs]
    digest_text = format_morning_digest(jobs_list)
    
    sent_count = 0
    for u in users:
        try:
            await bot.send_message(
                chat_id=u['user_id'],
                text=digest_text,
                parse_mode='HTML',
                disable_web_page_preview=True
            )
            sent_count += 1
            await asyncio.sleep(0.05)
        except Exception as e:
            pass
            
    logger.info(f"Morning digest sent to {sent_count} active users.")
    
    # Also post to channel  
    if CHANNEL_ID:
        try:
            await bot.send_message(chat_id=CHANNEL_ID, text=digest_text, parse_mode='HTML', disable_web_page_preview=True)
        except Exception:
            pass
