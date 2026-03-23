import logging

logger = logging.getLogger(__name__)

async def generate_salary_insights(role: str, location: str) -> str:
    """Generate salary insights using Anthropic API (Claude)."""
    # Placeholder for actual Anthropic logic
    return f"📊 **Salary Insights for {role} in {location}**\n\n- Average Base: ₹5,00,000\n- High End: ₹12,00,000\n\n*(AI stub functionality)*"

async def analyze_resume_match(user_id: int, saved_jobs: list) -> str:
    """Analyze PDF resume against saved jobs."""
    # Placeholder for PyMuPDF extraction and Anthropic comparison
    jobs_summary = "\n".join([f"- {job['job_title']} at {job['company']}" for job in saved_jobs])
    return f"📄 **Resume Match Analysis**\n\nComparing against:\n{jobs_summary}\n\nAnalysis: You have an 85% match for these roles! *(AI stub functionality)*"

async def generate_interview_prep(job_id: str) -> str:
    """Returns static interview prep tips."""
    return (
        "🧠 <b>Universal Interview Guide</b>\n\n"
        "Here are 5 steps to help you crack this interview:\n\n"
        "1️⃣ <b>Research the Company:</b> Spend 10 mins reading their recent news and 'About Us' page.\n"
        "2️⃣ <b>Master your Resume:</b> Be ready to explain every bullet point and project in detail.\n"
        "3️⃣ <b>The Pitch:</b> Prepare your 'Tell me about yourself' to be roughly 90 seconds (Present -> Past -> Future).\n"
        "4️⃣ <b>STAR Method:</b> Answer behavioral questions using Situation, Task, Action, Result.\n"
        "5️⃣ <b>Ask Questions:</b> Always ask 2 intelligent questions at the end to show you care.\n\n"
        "<i>Good luck! You've got this!</i> 💪"
    )
