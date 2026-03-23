import logging
import uuid
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes, CommandHandler
from database.db import get_db, add_or_update_user, get_user
from engine.ai_engine import generate_salary_insights, analyze_resume_match
from handlers.onboarding import start_preferences, my_profile

logger = logging.getLogger(__name__)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    db_user = await get_user(user.id)
    await add_or_update_user(user.id, user.username, user.full_name)
    
    if not db_user:
        await start_preferences(update, context)
    else:
        await menu(update, context)

async def menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🔍 Search Jobs", switch_inline_query_current_chat=""),
         InlineKeyboardButton("📋 My Preferences", callback_data="menu_prefs")],
        [InlineKeyboardButton("💾 Saved Jobs", callback_data="menu_saved"),
         InlineKeyboardButton("📊 Salary Insights", callback_data="menu_salary")],
        [InlineKeyboardButton("🏢 Follow Company", callback_data="menu_follow"),
         InlineKeyboardButton("📄 Resume Match", callback_data="menu_resume")],
        [InlineKeyboardButton("ℹ️ Help", callback_data="menu_help")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("JobRadar Dashboard:", reply_markup=reply_markup)

async def search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = " ".join(context.args) if context.args else ""
    if not query:
        await update.message.reply_text("Usage: /search [query]")
        return
        
    async with await get_db() as db:
        async with db.execute("SELECT * FROM jobs WHERE title LIKE ? OR company LIKE ? LIMIT 5", (f"%{query}%", f"%{query}%")) as cursor:
            jobs = await cursor.fetchall()
            
    if not jobs:
        await update.message.reply_text(f"No jobs found for '{query}'.")
        return
        
    for job in jobs:
        kb = [[
            InlineKeyboardButton("Apply", url=job['url']),
            InlineKeyboardButton("Save", callback_data=f"save_job_{job['id']}"),
            InlineKeyboardButton("Interview Prep", callback_data=f"interview_{job['id']}")
        ]]
        await update.message.reply_text(
            f"**{job['title']}** at {job['company']}\n📍 {job['location']} | 💰 {job['salary']}",
            reply_markup=InlineKeyboardMarkup(kb),
            parse_mode="Markdown"
        )

async def saved(update: Update, context: ContextTypes.DEFAULT_TYPE):
    async with await get_db() as db:
        async with db.execute("SELECT * FROM saved_jobs WHERE user_id = ?", (update.effective_user.id,)) as cursor:
            jobs = await cursor.fetchall()
            
    if not jobs:
        await update.message.reply_text("You have no saved jobs.")
        return
        
    for job in jobs:
        kb = [[InlineKeyboardButton("Remove", callback_data=f"remove_saved_{job['id']}")]]
        await update.message.reply_text(
            f"**{job['job_title']}** at {job['company']}\n🔗 {job['job_url']}",
            reply_markup=InlineKeyboardMarkup(kb),
            parse_mode="Markdown"
        )

async def applied(update: Update, context: ContextTypes.DEFAULT_TYPE):
    async with await get_db() as db:
        async with db.execute("SELECT * FROM applications WHERE user_id = ?", (update.effective_user.id,)) as cursor:
            apps = await cursor.fetchall()
            
    if not apps:
        await update.message.reply_text("You haven't tracked any applications yet.")
        return
        
    for app in apps:
        await update.message.reply_text(f"**{app['role']}** at {app['company']} | Status: {app['status']}", parse_mode="Markdown")

async def follow(update: Update, context: ContextTypes.DEFAULT_TYPE):
    company = " ".join(context.args)
    if not company:
        await update.message.reply_text("Usage: /follow [company name]")
        return
        
    async with await get_db() as db:
        await db.execute("INSERT OR IGNORE INTO watched_companies (user_id, company_name) VALUES (?, ?)", (update.effective_user.id, company))
        await db.commit()
    await update.message.reply_text(f"I'll alert you the moment {company} posts a new job!")

async def unfollow(update: Update, context: ContextTypes.DEFAULT_TYPE):
    async with await get_db() as db:
        async with db.execute("SELECT id, company_name FROM watched_companies WHERE user_id = ?", (update.effective_user.id,)) as cursor:
            comps = await cursor.fetchall()
            
    if not comps:
        await update.message.reply_text("You are not following any companies.")
        return
        
    kb = [[InlineKeyboardButton(f"Remove {c['company_name']}", callback_data=f"remove_follow_{c['id']}")] for c in comps]
    await update.message.reply_text("Watched companies:", reply_markup=InlineKeyboardMarkup(kb))

async def salary(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 2:
        await update.message.reply_text("Usage: /salary [role] [location]")
        return
    role = context.args[0]
    loc = " ".join(context.args[1:])
    insight = await generate_salary_insights(role, loc)
    await update.message.reply_text(insight, parse_mode="Markdown")

async def resume(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Please upload your PDF resume so I can analyze it against your top 3 saved jobs.")

# Note: We will handle document upload in a MessageHandler in bot.py

async def prefs_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await start_preferences(update, context)

async def myprofile_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await my_profile(update, context)

async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    async with await get_db() as db:
        async with db.execute("SELECT COUNT(*) FROM users") as c: users = (await c.fetchone())[0]
        async with db.execute("SELECT COUNT(*) FROM jobs WHERE date(posted_at) = date('now')") as c: jobs = (await c.fetchone())[0]
        
    await update.message.reply_text(f"📊 **JobRadar Stats**\nUsers: {users}\nJobs posted today: {jobs}", parse_mode="Markdown")

async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    async with await get_db() as db:
        await db.execute("UPDATE users SET is_active = 0 WHERE user_id = ?", (update.effective_user.id,))
        await db.commit()
    await update.message.reply_text("Your alerts have been deactivated. Your data is kept safe. Send /start to resume.")

async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "**📚 JobRadar Commands**\n"
        "/start - Start or setup profile\n"
        "/menu - Interactive dashboard\n"
        "/search [query] - Live search\n"
        "/saved - View saved jobs\n"
        "/applied - App tracker\n"
        "/follow [company] - Watch company\n"
        "/unfollow - Manage watch list\n"
        "/salary [role] [loc] - AI insights\n"
        "/resume - Resume matcher\n"
        "/preferences - Update prefs\n"
        "/myprofile - View profile\n"
        "/stats - Public stats\n"
        "/stop - Stop alerts\n"
        "/help - This menu"
    )
    await update.message.reply_text(text, parse_mode="Markdown")

def get_command_handlers():
    return [
        CommandHandler("start", start),
        CommandHandler("menu", menu),
        CommandHandler("search", search),
        CommandHandler("saved", saved),
        CommandHandler("applied", applied),
        CommandHandler("follow", follow),
        CommandHandler("unfollow", unfollow),
        CommandHandler("salary", salary),
        CommandHandler("resume", resume),
        CommandHandler("preferences", prefs_cmd),
        CommandHandler("myprofile", myprofile_cmd),
        CommandHandler("stats", stats),
        CommandHandler("stop", stop),
        CommandHandler("help", help_cmd)
    ]
