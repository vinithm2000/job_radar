import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes, 
    ConversationHandler, 
    CommandHandler, 
    CallbackQueryHandler, 
    MessageHandler, 
    filters
)
from database.db import update_job_preferences, get_job_preferences, add_or_update_user
from config import JOB_DOMAINS

logger = logging.getLogger(__name__)

# States
CHOOSING_DOMAINS, CHOOSING_EXPERIENCE, CHOOSING_WORK_TYPE, TYPING_LOCATION, CHOOSING_SALARY = range(5)

# --- Helper to build domain keyboard ---
def build_domain_keyboard(selected_domains):
    keyboard = []
    row = []
    for domain in JOB_DOMAINS:
        text = f"✅ {domain.title()}" if domain in selected_domains else domain.title()
        row.append(InlineKeyboardButton(text, callback_data=f"domain_{domain}"))
        if len(row) == 2:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)
        
    keyboard.append([InlineKeyboardButton("➡️ Next Step / Done", callback_data="confirm_domains")])
    return InlineKeyboardMarkup(keyboard)

# --- Step 1: Start & Domains ---
async def start_preferences(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await add_or_update_user(user.id, user.username, user.full_name)
    
    context.user_data['domains'] = set()
    reply_markup = build_domain_keyboard(context.user_data['domains'])
    
    msg = "Let's set up your job preferences! 🎯\n\n**Step 1:** Select the job domains you are interested in. You can select multiple. Click 'Next Step' when you're done."
    
    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(text=msg, reply_markup=reply_markup, parse_mode='Markdown')
    else:
        await update.message.reply_text(text=msg, reply_markup=reply_markup, parse_mode='Markdown')
    
    return CHOOSING_DOMAINS

async def handle_domain_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    data = query.data
    if data == "confirm_domains":
        if not context.user_data.get('domains'):
            await query.answer("Please select at least one domain!", show_alert=True)
            return CHOOSING_DOMAINS
            
        # Move to Step 2
        keyboard = [
            [InlineKeyboardButton("Fresher (0-1yr)", callback_data="exp_Fresher (0-1yr)")],
            [InlineKeyboardButton("Junior (1-3yr)", callback_data="exp_Junior (1-3yr)")],
            [InlineKeyboardButton("Mid (3-5yr)", callback_data="exp_Mid (3-5yr)")],
            [InlineKeyboardButton("Senior (5yr+)", callback_data="exp_Senior (5yr+)")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            text="**Step 2:** What is your experience level?",
            reply_markup=reply_markup, parse_mode='Markdown'
        )
        return CHOOSING_EXPERIENCE
        
    # Toggle domain
    domain = data.replace("domain_", "")
    selected = context.user_data.setdefault('domains', set())
    if domain in selected:
        selected.remove(domain)
    else:
        selected.add(domain)
        
    await query.edit_message_reply_markup(reply_markup=build_domain_keyboard(selected))
    return CHOOSING_DOMAINS

# --- Step 2: Experience ---
async def handle_experience(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    experience = query.data.replace("exp_", "")
    context.user_data['experience'] = experience
    
    # Move to Step 3
    keyboard = [
        [InlineKeyboardButton("Work from Home", callback_data="work_Work from Home")],
        [InlineKeyboardButton("Hybrid", callback_data="work_Hybrid")],
        [InlineKeyboardButton("On-site", callback_data="work_On-site")],
        [InlineKeyboardButton("Any", callback_data="work_Any")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(
        text="**Step 3:** What is your preferred work type?",
        reply_markup=reply_markup, parse_mode='Markdown'
    )
    return CHOOSING_WORK_TYPE

# --- Step 3: Work Type ---
async def handle_work_type(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    work_type = query.data.replace("work_", "")
    context.user_data['work_type'] = work_type
    
    await query.edit_message_text(
        text="**Step 4:** What is your preferred location? (Type a city name or 'Any')",
        parse_mode='Markdown'
    )
    return TYPING_LOCATION

# --- Step 4: Location ---
async def handle_location(update: Update, context: ContextTypes.DEFAULT_TYPE):
    location = update.message.text.strip()
    context.user_data['location'] = location
    
    # Move to Step 5
    keyboard = [
        [InlineKeyboardButton("< 3 LPA", callback_data="sal_<3L")],
        [InlineKeyboardButton("3 - 6 LPA", callback_data="sal_3-6L")],
        [InlineKeyboardButton("6 - 10 LPA", callback_data="sal_6-10L")],
        [InlineKeyboardButton("10 - 15 LPA", callback_data="sal_10-15L")],
        [InlineKeyboardButton("15+ LPA", callback_data="sal_15L+")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        text="**Step 5:** What is your salary expectation?",
        reply_markup=reply_markup, parse_mode='Markdown'
    )
    return CHOOSING_SALARY

# --- Step 5: Salary & Save ---
async def handle_salary(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    salary = query.data.replace("sal_", "")
    user_id = update.effective_user.id
    
    # Save to db
    domains_str = ",".join(context.user_data['domains'])
    exp = context.user_data['experience']
    work = context.user_data['work_type']
    loc = context.user_data['location']
    
    # For DB schema, min/max salary isn't strictly numeric here, we use the string choice for simplicity
    await update_job_preferences(
        user_id=user_id,
        domains=domains_str,
        experience_years=exp,
        work_type=work,
        preferred_location=loc,
        min_salary=salary,
        max_salary=""
    )
    
    summary = (
        "✅ **Preferences Saved Successfully!**\n\n"
        f"**Domains:** {domains_str.title()}\n"
        f"**Experience:** {exp}\n"
        f"**Work Type:** {work}\n"
        f"**Location:** {loc}\n"
        f"**Salary:** {salary}\n\n"
        "We will notify you when jobs matching these criteria get posted. Use /myprofile to view or /preferences to change."
    )
    await query.edit_message_text(text=summary, parse_mode='Markdown')
    context.user_data.clear()
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancels and ends the conversation."""
    context.user_data.clear()
    await update.message.reply_text('Preference setup cancelled. Use /preferences anytime to try again.')
    return ConversationHandler.END

# View Profile
async def my_profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    prefs = await get_job_preferences(user_id)
    
    if not prefs:
        await update.message.reply_text("You haven't set up your preferences yet. Use /preferences to get started!")
        return
        
    summary = (
        "👤 **Your JobRadar Profile**\n\n"
        f"**Domains:** {prefs['domains'].title()}\n"
        f"**Experience:** {prefs['experience_years']}\n"
        f"**Work Type:** {prefs['work_type']}\n"
        f"**Location:** {prefs['preferred_location']}\n"
        f"**Expected Salary:** {prefs['min_salary']}\n\n"
        "Use /preferences to update these settings."
    )
    await update.message.reply_text(text=summary, parse_mode='Markdown')

def get_onboarding_handler():
    return ConversationHandler(
        entry_points=[CommandHandler('preferences', start_preferences)],
        states={
            CHOOSING_DOMAINS: [CallbackQueryHandler(handle_domain_selection, pattern="^(domain_|confirm_domains)")],
            CHOOSING_EXPERIENCE: [CallbackQueryHandler(handle_experience, pattern="^exp_")],
            CHOOSING_WORK_TYPE: [CallbackQueryHandler(handle_work_type, pattern="^work_")],
            TYPING_LOCATION: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_location)],
            CHOOSING_SALARY: [CallbackQueryHandler(handle_salary, pattern="^sal_")]
        },
        fallbacks=[CommandHandler('cancel', cancel)],
        per_user=True
    )
