import logging
from telegram import Update
from telegram.ext import Application, ContextTypes
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from config import BOT_TOKEN, logger
from database.db import init_db

# Handlers Imports
from handlers.onboarding import get_onboarding_handler
from handlers.commands import get_command_handlers
from handlers.callbacks import get_callback_handlers
from handlers.admin import get_admin_handlers

# Example background job function
async def fetch_jobs_task(context: ContextTypes.DEFAULT_TYPE):
    """
    This task will run every 2 hours to scrape new jobs and notify users.
    """
    logger.info("Executing scheduled job scraping task...")
    from engine.fetcher import fetch_all_jobs
    jobs = await fetch_all_jobs()
    logger.info(f"Background task complete. Fetched {len(jobs)} total jobs.")

async def post_init(application: Application):
    """Actions to perform after the application connects, before it begins polling."""
    await init_db()
    
    # Register the "Menu" button commands in the Telegram UI
    from telegram import BotCommand
    commands = [
        BotCommand("start", "Start or setup profile"),
        BotCommand("menu", "Interactive dashboard"),
        BotCommand("search", "Live job search (e.g. /search python)"),
        BotCommand("saved", "View your saved jobs"),
        BotCommand("applied", "Application tracker"),
        BotCommand("follow", "Watch a company (e.g. /follow Apple)"),
        BotCommand("unfollow", "Manage watched companies"),
        BotCommand("salary", "AI insights (e.g. /salary dev)"),
        BotCommand("resume", "Resume matcher"),
        BotCommand("preferences", "Set or update your job alerts"),
        BotCommand("myprofile", "View your current profile"),
        BotCommand("stats", "View public JobRadar stats"),
        BotCommand("stop", "Pause all job alerts"),
        BotCommand("help", "View full command reference")
    ]
    await application.bot.set_my_commands(commands)
    
    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        fetch_jobs_task,
        "interval",
        hours=2,
        kwargs={'context': None},
        id="job_scraper_interval",
        replace_existing=True
    )
    scheduler.start()
    application.bot_data["scheduler"] = scheduler
    logger.info("Scheduler started. Jobs will be fetched every 2 hours.")

def main():
    """Start the bot."""
    if not BOT_TOKEN or BOT_TOKEN == 'your_telegram_bot_token_here':
        logger.error("BOT_TOKEN is not configured! Exiting...")
        return
        
    application = Application.builder().token(BOT_TOKEN).post_init(post_init).build()
    
    # Core command handlers (start, menu, etc.)
    application.add_handlers(get_command_handlers())
    # Universal inline button callbacks
    application.add_handler(get_callback_handlers())
    # Admin locked commands
    application.add_handlers(get_admin_handlers())
    # Conversation interactive flow
    application.add_handler(get_onboarding_handler())

    # Run the bot until the user presses Ctrl-C
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
