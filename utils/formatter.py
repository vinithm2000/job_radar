import datetime
from telegram import InlineKeyboardMarkup, InlineKeyboardButton

def _get_work_type_badge(work_type: str) -> str:
    wt = str(work_type).lower()
    if 'remote' in wt or 'wfh' in wt or 'home' in wt:
        return '🏠 Remote'
    elif 'hybrid' in wt:
        return '🔄 Hybrid'
    else:
        return '🏢 On-site'

def format_job_card(job: dict) -> tuple[str, InlineKeyboardMarkup]:
    """Format a job dictionary into an HTML string and InlineKeyboardMarkup."""
    
    company = job.get('company', 'Unknown Company')
    title = job.get('title', 'Unknown Title')
    location = job.get('location', 'India')
    
    work_type = job.get('work_type', 'Any')
    badge = _get_work_type_badge(work_type)
    
    salary = job.get('salary') or job.get('min_amount')
    if not salary or str(salary).strip() == '-' or str(salary).strip() == '':
        salary_str = "Not disclosed"
    else:
        salary_str = str(salary)
        if job.get('max_amount'):
            salary_str += f" - {job.get('max_amount')}"
            
    experience = job.get('experience', 'Not specified')
    score = job.get('score', 0)
    source = job.get('site', job.get('source_portal', 'Unknown'))
    
    # Calculate days ago if date provided
    posted_at = job.get('date_posted') or job.get('posted_at')
    days_ago = "Recently"
    if posted_at:
        try:
            # Basic parsing if ISO string
            post_date = datetime.datetime.fromisoformat(str(posted_at).replace('Z', '+00:00'))
            delta = datetime.datetime.now(datetime.timezone.utc) - post_date
            if delta.days > 0:
                days_ago = f"{delta.days} days ago"
            else:
                days_ago = "Today"
        except Exception:
            days_ago = str(posted_at)

    ai_summary = "Matches your domains perfectly. High growth potential role." # AI stub
    
    html = (
        f"🏢 <b>{company}</b>\n"
        f"💼 <b>{title}</b>\n"
        f"📍 {location} [{badge}]\n"
        f"💰 {salary_str}\n"
        f"⏳ {experience}\n"
        f"⭐ AI Score: {score}/10\n"
        f"📌 Source: {source.title()}\n"
        f"🕐 Posted: {days_ago}\n\n"
        f"<i>{ai_summary}</i>"
    )
    
    job_id = job.get('id', job.get('job_id', 'unknown'))
    url = job.get('job_url', job.get('url', ''))
    
    keyboard = [
        [
            InlineKeyboardButton("✅ Apply Now", url=url) if url else InlineKeyboardButton("✅ Apply Now", callback_data="no_url"),
            InlineKeyboardButton("💾 Save Job", callback_data=f"save_job_{job_id}")
        ],
        [
            InlineKeyboardButton("🎯 Interview Prep", callback_data=f"interview_{job_id}"),
            InlineKeyboardButton("📤 Share", callback_data=f"share_job_{job_id}")
        ]
    ]
    
    return html, InlineKeyboardMarkup(keyboard)

def format_morning_digest(jobs: list[dict]) -> str:
    """Format top jobs into a morning digest text."""
    if not jobs:
        return "🌅 Good Morning! No new top jobs match your profile today, but keep an eye out!"
        
    lines = ["🌅 <b>Good Morning! Here are today's top job picks for you 👇</b>\n"]
    
    for i, job in enumerate(jobs[:10], start=1):
        company = job.get('company', 'Unknown')
        title = job.get('title', 'Role')
        loc = job.get('location', 'India')
        url = job.get('url', job.get('job_url', ''))
        
        line = f"{i}. <b>{company}</b> - {title} ({loc})"
        if url:
            line += f" - <a href='{url}'>Apply</a>"
        lines.append(line)
        
    return "\n".join(lines)
