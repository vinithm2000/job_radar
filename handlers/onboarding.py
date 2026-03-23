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
    
    msg = "Let's set up your job preferences! 🎯\n\n<b>Step 1:</b> Select the job domains you are interested in. You can select multiple. Click 'Next Step / Done' when you are finished."
    
    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(text=msg, reply_markup=reply_markup, parse_mode='HTML')
    else:
        await update.message.reply_text(text=msg, reply_markup=reply_markup, parse_mode='HTML')
    
    return CHOOSING_DOMAINS

async def handle_domain_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    data = query.data
    if data == "confirm_domains":
        if not context.user_data.get('domains'):
            await query.answer("Please click at least one domain above!", show_alert=True)
            return CHOOSING_DOMAINS
            
        # Move to Step 2
        keyboard = [
            [InlineKeyboardButton("Fresher (0-1yr)", callback_data="exp_Fresher")],
            [InlineKeyboardButton("Junior (1-3yr)", callback_data="exp_Junior")],
            [InlineKeyboardButton("Mid (3-5yr)", callback_data="exp_Mid")],
            [InlineKeyboardButton("Senior (5yr+)", callback_data="exp_Senior")],
            [InlineKeyboardButton("Any Experience", callback_data="exp_Any")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            text="<b>Step 2:</b> What is your experience level?",
            reply_markup=reply_markup, parse_mode='HTML'
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
        [InlineKeyboardButton("Work from Home / Remote", callback_data="work_Remote")],
        [InlineKeyboardButton("Hybrid Model", callback_data="work_Hybrid")],
        [InlineKeyboardButton("Office / On-site", callback_data="work_Office")],
        [InlineKeyboardButton("Any", callback_data="work_Any")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(
        text="<b>Step 3:</b> What is your preferred work type?",
        reply_markup=reply_markup, parse_mode='HTML'
    )
    return CHOOSING_WORK_TYPE

# --- Step 3: Work Type ---
async def handle_work_type(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    work_type = query.data.replace("work_", "")
    context.user_data['work_type'] = work_type
    
    await query.edit_message_text(
        text="<b>Step 4:</b> What is your preferred location? (Please TYPE a city name or type 'Any' in the chat box)",
        parse_mode='HTML'
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
        text="<b>Step 5:</b> What is your salary expectation?",
        reply_markup=reply_markup, parse_mode='HTML'
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
        "✅ <b>Preferences Saved Successfully!</b>\n\n"
        f"<b>Domains:</b> {domains_str.title()}\n"
        f"<b>Experience:</b> {exp}\n"
        f"<b>Work Type:</b> {work}\n"
        f"<b>Location:</b> {loc}\n"
        f"<b>Salary:</b> {salary}\n\n"
        "We will notify you when jobs matching these criteria get posted. Use /menu to view your dashboard."
    )
    await query.edit_message_text(text=summary, parse_mode='HTML')
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
        "👤 <b>Your JobRadar Profile</b>\n\n"
        f"<b>Domains:</b> {prefs['domains'].title()}\n"
        f"<b>Experience:</b> {prefs['experience_years']}\n"
        f"<b>Work Type:</b> {prefs['work_type']}\n"
        f"<b>Location:</b> {prefs['preferred_location']}\n"
        f"<b>Expected Salary:</b> {prefs['min_salary']}\n\n"
        "Use /preferences to update these settings."
    )
    await update.message.reply_text(text=summary, parse_mode='HTML')

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
