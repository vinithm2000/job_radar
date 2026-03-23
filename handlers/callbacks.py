import logging
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes, CallbackQueryHandler
from database.db import get_db
from engine.ai_engine import generate_interview_prep

logger = logging.getLogger(__name__)

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    user_id = update.effective_user.id
    
    if data.startswith("save_job_"):
        job_id = data.replace("save_job_", "")
        async with get_db() as db:
            # Fetch job details
            async with db.execute("SELECT title, company, url FROM jobs WHERE id = ?", (job_id,)) as cursor:
                job = await cursor.fetchone()
            if job:
                await db.execute(
                    "INSERT INTO saved_jobs (user_id, job_url, job_title, company) VALUES (?, ?, ?, ?)", 
                    (user_id, job['url'], job['title'], job['company'])
                )
                await db.commit()
                await query.edit_message_reply_markup(reply_markup=None)
                await query.message.reply_text(f"✅ Saved **{job['title']}** to your list!", parse_mode="Markdown")
                
    elif data.startswith("apply_job_"):
        # Assuming the inline button goes to URL directly, this callback triggers if they hit a custom Apply callback button instead
        job_id = data.replace("apply_job_", "")
        logger.info(f"User {user_id} clicked apply for job {job_id}")
        
    elif data.startswith("interview_"):
        job_id = data.replace("interview_", "")
        prep = await generate_interview_prep(job_id)
        await query.message.reply_text(prep, parse_mode="Markdown")
        
    elif data.startswith("remove_saved_"):
        saved_id = data.replace("remove_saved_", "")
        async with get_db() as db:
            await db.execute("DELETE FROM saved_jobs WHERE id = ?", (saved_id,))
            await db.commit()
        await query.edit_message_text("✅ Job removed from saved list.")
        
    elif data.startswith("share_job_"):
        job_id = data.replace("share_job_", "")
        bot_username = context.bot.username
        await query.message.reply_text(f"Share this job link: https://t.me/{bot_username}?start=job_{job_id}")

    # Helper menu callbacks
    elif data == "menu_search":
        await query.message.reply_text("Send /search [your job title] to find jobs directly! (Example: /search Python Developer)")
    elif data == "menu_prefs":
        await query.message.reply_text("Use /preferences to update your settings.")
    elif data == "menu_saved":
        await query.message.reply_text("Use /saved to view your jobs.")
    elif data == "menu_salary":
        await query.message.reply_text("Use /salary [role] [location] for insights.")
    elif data == "menu_resume":
        await query.message.reply_text("Use /resume and upload your PDF.")
    elif data == "menu_follow":
        await query.message.reply_text("Use /follow [company] to track a company.")
    elif data == "menu_help":
        await query.message.reply_text("Use /help for all commands.")

def get_callback_handlers():
    return CallbackQueryHandler(handle_callback, pattern="^(save_job_|apply_job_|interview_|remove_saved_|share_job_|menu_)")
