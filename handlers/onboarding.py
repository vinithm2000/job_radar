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
from config import DOMAIN_CATEGORIES

logger = logging.getLogger(__name__)

# States
CHOOSING_DOMAINS, CHOOSING_EXPERIENCE, CHOOSING_WORK_TYPE, TYPING_LOCATION, CHOOSING_SALARY = range(5)

# --- Helper to build category keyboard ---
def build_category_keyboard(selected_domains):
    keyboard = []
    row = []
    categories = list(DOMAIN_CATEGORIES.keys())
    for idx, cat in enumerate(categories):
        cat_selected = sum(1 for d in DOMAIN_CATEGORIES[cat] if d in selected_domains)
        btn_text = f"{cat} ({cat_selected})" if cat_selected > 0 else cat
        row.append(InlineKeyboardButton(btn_text, callback_data=f"cat_{idx}"))
        if len(row) == 2:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)
        
    total_selected = len(selected_domains)
    keyboard.append([InlineKeyboardButton(f"➡️ Next Step ({total_selected} Selected)", callback_data="confirm_domains")])
    return InlineKeyboardMarkup(keyboard)

def build_subcategory_keyboard(cat_idx, selected_domains):
    category = list(DOMAIN_CATEGORIES.keys())[int(cat_idx)]
    keyboard = []
    row = []
    for domain in DOMAIN_CATEGORIES[category]:
        text = f"✅ {domain.title()}" if domain in selected_domains else domain.title()
        row.append(InlineKeyboardButton(text, callback_data=f"domain_{domain}"))
        if len(row) == 2:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)
        
    keyboard.append([InlineKeyboardButton("🔙 Back to Categories", callback_data="back_to_categories")])
    return InlineKeyboardMarkup(keyboard)

# --- Step 1: Start & Domains ---
async def start_preferences(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await add_or_update_user(user.id, user.username, user.full_name)
    
    context.user_data['domains'] = set()
    context.user_data['current_cat_idx'] = None
    reply_markup = build_category_keyboard(context.user_data['domains'])
    
    msg = "Let's set up your job preferences! 🎯\n\n<b>Step 1:</b> Select a category to pick your desired job domains. Click 'Next Step' when you are finished."
    
    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(text=msg, reply_markup=reply_markup, parse_mode='HTML')
    else:
        await update.message.reply_text(text=msg, reply_markup=reply_markup, parse_mode='HTML')
    
    return CHOOSING_DOMAINS

async def handle_domain_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    
    if data == "confirm_domains":
        if not context.user_data.get('domains'):
            await query.answer("Please select at least one domain!", show_alert=True)
            return CHOOSING_DOMAINS
        
        await query.answer()
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
        
    elif data == "back_to_categories":
        await query.answer()
        context.user_data['current_cat_idx'] = None
        selected = context.user_data.get('domains', set())
        msg = "Let's set up your job preferences! 🎯\n\n<b>Step 1:</b> Select a category to pick your desired job domains. Click 'Next Step' when you are finished."
        await query.edit_message_text(text=msg, reply_markup=build_category_keyboard(selected), parse_mode='HTML')
        return CHOOSING_DOMAINS
        
    elif data.startswith("cat_"):
        await query.answer()
        idx = int(data.replace("cat_", ""))
        context.user_data['current_cat_idx'] = idx
        selected = context.user_data.get('domains', set())
        
        category_name = list(DOMAIN_CATEGORIES.keys())[idx]
        await query.edit_message_text(
            text=f"📂 <b>Folder: {category_name}</b>\nTap to select or deselect domains below:",
            reply_markup=build_subcategory_keyboard(idx, selected),
            parse_mode='HTML'
        )
        return CHOOSING_DOMAINS
        
    elif data.startswith("domain_"):
        await query.answer()
        # Toggle domain
        domain = data.replace("domain_", "")
        selected = context.user_data.setdefault('domains', set())
        if domain in selected:
            selected.remove(domain)
        else:
            selected.add(domain)
            
        try:
            cat_idx = context.user_data.get('current_cat_idx')
            if cat_idx is not None:
                await query.edit_message_reply_markup(reply_markup=build_subcategory_keyboard(cat_idx, selected))
            else:
                await query.edit_message_reply_markup(reply_markup=build_category_keyboard(selected))
        except Exception as e:
            logger.error(f"Failed to edit markup: {e}")
            
        return CHOOSING_DOMAINS
        
    return CHOOSING_DOMAINS

# --- Step 2: Experience ---
async def handle_experience(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    
    if data.startswith("exp_"):
        await query.answer()
        experience = data.replace("exp_", "")
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
    return CHOOSING_EXPERIENCE

# --- Step 3: Work Type ---
async def handle_work_type(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    
    if data.startswith("work_"):
        await query.answer()
        work_type = data.replace("work_", "")
        context.user_data['work_type'] = work_type
        
        await query.edit_message_text(
            text="<b>Step 4:</b> What is your preferred location? (Type one or more cities separated by commas, e.g. 'Chennai, Bangalore', or type 'Any')",
            parse_mode='HTML'
        )
        return TYPING_LOCATION
    return CHOOSING_WORK_TYPE

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
    data = query.data
    
    if data.startswith("sal_"):
        await query.answer()
        salary = data.replace("sal_", "")
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
    return CHOOSING_SALARY

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
            CHOOSING_DOMAINS: [CallbackQueryHandler(handle_domain_selection)],
            CHOOSING_EXPERIENCE: [CallbackQueryHandler(handle_experience)],
            CHOOSING_WORK_TYPE: [CallbackQueryHandler(handle_work_type)],
            TYPING_LOCATION: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_location)],
            CHOOSING_SALARY: [CallbackQueryHandler(handle_salary)]
        },
        fallbacks=[CommandHandler('cancel', cancel)],
        per_user=True
    )
