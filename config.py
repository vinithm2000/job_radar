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

# Job Domains Configured for the Bot
JOB_DOMAINS = [
    "python developer",
    "java developer",
    "full stack developer",
    "react developer",
    "flutter developer",
    "data analyst",
    "digital marketing",
    "ui ux designer",
    "content writer",
    "customer support",
    "sales",
    "devops engineer",
    "machine learning"
]

# Supported Portals (Used by python-jobspy natively usually)
JOB_PORTALS = ["linkedin", "indeed", "glassdoor", "ziprecruiter"]

# Logging configuration
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)
