import os
import logging
from telegram import Update
from telegram.ext import ContextTypes, CommandHandler
from database.db import get_db
from engine.fetcher import fetch_all_jobs

logger = logging.getLogger(__name__)

# Default ID if not set. Change via env.
ADMIN_CHAT_ID = int(os.getenv("ADMIN_CHAT_ID", "0"))

def is_admin(user_id: int) -> bool:
    return user_id == ADMIN_CHAT_ID

async def adminstats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id): return
    
    async with await get_db() as db:
        async with db.execute("SELECT COUNT(*), SUM(is_active) FROM users") as c:
            row = await c.fetchone()
            total_users, active_users = row[0], row[1]
            
        async with db.execute("SELECT COUNT(*) FROM jobs WHERE date(posted_at) = date('now')") as c: 
            jobs_today = (await c.fetchone())[0]
            
        # Get DB size
        db_size_mb = os.path.getsize(os.getenv("DB_PATH", "jobradar.db")) / (1024 * 1024) if os.path.exists(os.getenv("DB_PATH", "jobradar.db")) else 0
        
    await update.message.reply_text(
        f"👑 **Admin Stats**\n"
        f"Users: {total_users} (Active: {active_users})\n"
        f"Jobs Today: {jobs_today}\n"
        f"DB Size: {db_size_mb:.2f} MB\n"
        f"Top Domains (query pending)",
        parse_mode="Markdown"
    )

async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id): return
    msg = " ".join(context.args)
    if not msg:
        await update.message.reply_text("Usage: /broadcast [msg]")
        return
        
    async with await get_db() as db:
        async with db.execute("SELECT user_id FROM users WHERE is_active = 1") as cursor:
            users = await cursor.fetchall()
            
    sent_count = 0
    for u in users:
        try:
            await context.bot.send_message(chat_id=u['user_id'], text=f"📢 Announcement:\n\n{msg}")
            sent_count += 1
        except Exception:
            pass
            
    await update.message.reply_text(f"Broadcast sent to {sent_count} users.")

async def forcefetch(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id): return
    await update.message.reply_text("Forcing immediate job fetch cycle...")
    new_jobs = await fetch_all_jobs()
    await update.message.reply_text(f"Fetch complete! Found {len(new_jobs)} new jobs.")

async def addomain(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id): return
    domain = " ".join(context.args)
    if not domain:
        await update.message.reply_text("Usage: /addomain [domain]")
        return
    # Appending to config list dynamically is tough since it resets on restart,
    # but we can simulate it or add to a DB table instead.
    from config import JOB_DOMAINS
    JOB_DOMAINS.append(domain)
    await update.message.reply_text(f"Added domain: {domain}")

async def logs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id): return
    await update.message.reply_text("This requires file-based logging setup to read the latest lines. Not fully implemented.")

def get_admin_handlers():
    return [
        CommandHandler("adminstats", adminstats),
        CommandHandler("broadcast", broadcast),
        CommandHandler("forcefetch", forcefetch),
        CommandHandler("addomain", addomain),
        CommandHandler("logs", logs)
    ]
