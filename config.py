import os
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# App credentials
BOT_TOKEN = os.getenv("BOT_TOKEN")
CLAUDE_API_KEY = os.getenv("CLAUDE_API_KEY")

# DB Path
DB_PATH = os.getenv("DB_PATH", "jobradar.db")

# Ensure DB directory exists (Crucial for Railway Volumes like /app/data)
db_dir = os.path.dirname(DB_PATH)
if db_dir and not os.path.exists(db_dir):
    os.makedirs(db_dir, exist_ok=True)

# Job Categories and Domains Configured for the Bot
DOMAIN_CATEGORIES = {
    "📌 Tech & General": [
        "python developer", "java developer", "full stack developer",
        "react developer", "flutter developer", "devops engineer",
        "machine learning", "data analyst", "digital marketing", 
        "ui ux designer", "content writer", "customer support", "sales"
    ],
    "🎨 Design & Creative": [
        "graphic designer", "video editor", "motion graphics",
        "brand designer", "product designer"
    ],
    "🧪 Testing & QA": [
        "qa engineer", "manual tester", "automation tester",
        "performance tester", "sdet"
    ],
    "💻 Advanced Tech & Systems": [
        "android developer", "ios developer", "backend developer",
        "node.js developer", "php developer", "cybersecurity",
        "blockchain dev", "embedded systems", "cloud aws / azure",
        "network engineer", "game developer"
    ],
    "📊 Data & AI": [
        "data engineer", "data scientist", "business analyst",
        "ai prompt engineer", "power bi / tableau"
    ],
    "🏢 Business, Ops & HR": [
        "hr / recruiter", "project manager", "product manager",
        "operations manager", "supply chain", "accounting / tally",
        "legal / compliance", "scrum master / agile", "technical support"
    ],
    "📈 Marketing & Growth": [
        "seo specialist", "performance marketing", "social media manager",
        "email marketing", "growth hacker"
    ]
}

# Flatten for backward compatibility with scrapers
JOB_DOMAINS = [domain for category in DOMAIN_CATEGORIES.values() for domain in category]

# Supported Portals (Used by python-jobspy natively usually)
JOB_PORTALS = ["linkedin", "indeed", "glassdoor", "ziprecruiter"]

# Logging configuration
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)
