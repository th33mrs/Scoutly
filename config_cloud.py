"""Trovly - Cloud Config (no secrets)"""

RESUME_TEXT = "placeholder"
BOOST_KEYWORDS = []
BOOST_WEIGHT = 0.05
SIMILARITY_THRESHOLD = 0.55
SEARCH_QUERIES = []
LOCATION = ""
REMOTE_ONLY = True
SCAN_INTERVAL_MINUTES = 1440

DISCORD_WEBHOOK_URL = ""
TELEGRAM_BOT_TOKEN = ""
TELEGRAM_CHAT_ID = ""

ENABLED_SOURCES = {
    "adzuna": False,
    "remotive": True,
    "arbeitnow": True,
    "usajobs": False,
    "the_muse": True,
    "jobicy": True,
    "himalayas": True,
    "rss_feeds": True,
}

ADZUNA_APP_ID = ""
ADZUNA_APP_KEY = ""
ADZUNA_COUNTRY = "us"
USAJOBS_API_KEY = ""
USAJOBS_EMAIL = ""

RSS_FEEDS = [
    "https://weworkremotely.com/categories/remote-back-end-programming-jobs.rss",
    "https://weworkremotely.com/categories/remote-full-stack-programming-jobs.rss",
    "https://weworkremotely.com/categories/remote-devops-sysadmin-jobs.rss",
    "https://weworkremotely.com/categories/remote-programming-jobs.rss",
]

SECTION_WEIGHTS = {}
DEFAULT_SECTION_WEIGHT = 1.0
NEGATIVE_KEYWORDS = []
SALARY_FLOOR = 0

SEEN_JOBS_DB = "seen_jobs.json"
LOG_FILE = "trovly.log"
