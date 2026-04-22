#!/usr/bin/env python3
"""
Trovly - Main Runner
================================
Scans job sources, matches against resume, sends alerts.
Run with: python main.py

Modes:
  python main.py              → Run once then schedule every N minutes
  python main.py --once       → Single scan (no scheduling)
  python main.py --stats      → Score distribution diagnostic (tune threshold)
  python main.py --reset      → Clear seen-jobs database
"""

import argparse
import json
import logging
import sys
import time
from datetime import datetime
from pathlib import Path

import schedule

import config
from alerts import send_alerts
from matcher import match_jobs, score_distribution
from sources import JobPosting, fetch_all_jobs
from tracker import JobTracker
from dateutil import parser as dateparser


def filter_by_age(jobs, max_days):
    """Remove jobs older than max_days."""
    if not max_days:
        return jobs
    cutoff = datetime.now().timestamp() - (max_days * 86400)
    kept = []
    for job in jobs:
        if not job.posted_date:
            kept.append(job)  # keep jobs with no date rather than discard
            continue
        try:
            posted_ts = dateparser.parse(job.posted_date, ignoretz=True).timestamp()
            if posted_ts >= cutoff:
                kept.append(job)
        except Exception:
            kept.append(job)  # keep if unparseable
    return kept



# ─── Logging Setup ──────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s │ %(name)-22s │ %(levelname)-5s │ %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(config.LOG_FILE, encoding="utf-8"),
    ],
)
logger = logging.getLogger("job_scanner")


# ─── Seen Jobs Tracking ────────────────────────────────────────────
class SeenJobsDB:
    """Simple JSON-backed deduplication store."""

    def __init__(self, path: str = config.SEEN_JOBS_DB):
        self.path = Path(path)
        self.data: dict[str, str] = {}  # uid -> ISO timestamp
        self._load()

    def _load(self):
        if self.path.exists():
            try:
                self.data = json.loads(self.path.read_text())
            except json.JSONDecodeError:
                logger.warning("Corrupt seen_jobs DB — starting fresh")
                self.data = {}

    def _save(self):
        self.path.write_text(json.dumps(self.data, indent=2))

    def is_seen(self, uid: str) -> bool:
        return uid in self.data

    def mark_seen(self, uid: str):
        self.data[uid] = datetime.now().isoformat()
        self._save()

    def count(self) -> int:
        return len(self.data)

    def reset(self):
        self.data = {}
        self._save()
        logger.info("Seen jobs database cleared")

    def prune(self, max_age_days: int = 30):
        """Remove entries older than max_age_days to keep DB lean."""
        cutoff = datetime.now().timestamp() - (max_age_days * 86400)
        before = len(self.data)
        self.data = {
            uid: ts for uid, ts in self.data.items()
            if datetime.fromisoformat(ts).timestamp() > cutoff
        }
        pruned = before - len(self.data)
        if pruned > 0:
            self._save()
            logger.info(f"Pruned {pruned} old entries from seen DB")


# ─── Core Scan ──────────────────────────────────────────────────────


def filter_negative_keywords(jobs):
    """Remove jobs containing any negative keyword from config."""
    if not hasattr(config, 'NEGATIVE_KEYWORDS') or not config.NEGATIVE_KEYWORDS:
        return jobs
    kept = []
    skipped = 0
    for job in jobs:
        # Combine title + description, lowercase for case-insensitive matching
        text = (job.title + ' ' + job.description).lower()
        # any() returns True if ANY keyword is found in the text
        if any(kw.lower() in text for kw in config.NEGATIVE_KEYWORDS):
            skipped += 1
        else:
            kept.append(job)
    if skipped > 0:
        logger.info('Negative keyword filter removed {} jobs'.format(skipped))
    return kept


def filter_salary_floor(jobs):
    """Remove jobs with posted salary below the configured floor."""
    if not hasattr(config, 'SALARY_FLOOR') or not config.SALARY_FLOOR:
        return jobs
    import re
    kept = []
    skipped = 0
    for job in jobs:
        if not job.salary:
            kept.append(job)  # No salary info = keep (don't penalize)
            continue
        # Extract all numbers from the salary string
        # re.findall(r"[\d,]+", ",000 - ,000") → ["85,000", "120,000"]
        numbers = re.findall(r"[\d,]+", job.salary)
        if not numbers:
            kept.append(job)  # Can't parse = keep
            continue
        # Convert to integers: "85,000" → 85000
        parsed = [int(n.replace(",", "")) for n in numbers]
        # Use the max salary in the range for comparison
        max_salary = max(parsed)
        # Handle hourly rates (rough heuristic: if under 500, assume hourly)
        if max_salary < 500:
            max_salary = max_salary * 2080  # 40 hrs/week * 52 weeks
        if max_salary >= config.SALARY_FLOOR:
            kept.append(job)
        else:
            skipped += 1
            logger.info('Salary filter skipped: {} ({})'.format(job.title, job.salary))
    if skipped > 0:
        logger.info('Salary floor filter removed {} jobs'.format(skipped))
    return kept


def run_scan(seen_db: SeenJobsDB) -> dict:
    """Execute a full scan cycle. Returns summary stats."""
    scan_start = time.time()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    logger.info(f"{'='*60}")
    logger.info(f"SCAN STARTED — {now}")
    logger.info(f"{'='*60}")

    # 1. Fetch from all sources
    all_jobs = fetch_all_jobs()
    if not all_jobs:
        logger.warning("No jobs fetched from any source")
        return {"fetched": 0, "new": 0, "matched": 0, "alerted": 0}

    # 2. Filter out already-seen jobs
    new_jobs = [j for j in all_jobs if not seen_db.is_seen(j.uid)]
    logger.info(f"New jobs (not seen before): {len(new_jobs)} / {len(all_jobs)}")

    # Apply negative keyword filter
    new_jobs = filter_negative_keywords(new_jobs)

    # Apply salary floor filter
    new_jobs = filter_salary_floor(new_jobs)

    if not new_jobs:
        logger.info("No new jobs to process")
        return {"fetched": len(all_jobs), "new": 0, "matched": 0, "alerted": 0}

    # 3. Match against resume
    matched = match_jobs(new_jobs)

    # 4. Send alerts
    alert_stats = {"discord": 0, "telegram": 0}
    if matched:
        alert_stats = send_alerts(matched)

    # Track all matched jobs
    job_tracker = JobTracker()
    for job, score in matched:
        job_tracker.add_job(job, score)

    # 5. Mark ALL fetched new jobs as seen (not just matched ones)
    for job in new_jobs:
        seen_db.mark_seen(job.uid)

    # 6. Periodic prune
    seen_db.prune(max_age_days=30)

    elapsed = time.time() - scan_start
    summary = {
        "fetched": len(all_jobs),
        "new": len(new_jobs),
        "matched": len(matched),
        "alerted": alert_stats.get("discord", 0) + alert_stats.get("telegram", 0),
        "elapsed_sec": round(elapsed, 1),
    }

    logger.info(f"SCAN COMPLETE — {summary}")
    logger.info(f"Next scan in {config.SCAN_INTERVAL_MINUTES} minutes\n")
    return summary


# ─── Diagnostics ────────────────────────────────────────────────────
def run_stats():
    """Fetch jobs and show score distribution — helps tune threshold."""
    logger.info("Running score distribution diagnostic...")
    all_jobs = fetch_all_jobs()
    if not all_jobs:
        print("No jobs fetched — check your API keys and enabled sources.")
        return

    dist = score_distribution(all_jobs)
    print("\n" + "="*50)
    print("SCORE DISTRIBUTION DIAGNOSTIC")
    print("="*50)
    print(f"  Jobs scored:  {dist['count']}")
    print(f"  Mean:         {dist['mean']:.3f}")
    print(f"  Median:       {dist['median']:.3f}")
    print(f"  Std Dev:      {dist['std']:.3f}")
    print(f"  Min / Max:    {dist['min']:.3f} / {dist['max']:.3f}")
    print(f"\n  Histogram:")
    for bucket, count in dist.get("histogram", {}).items():
        bar = "█" * count
        print(f"    {bucket}: {count:3d} {bar}")
    print(f"\n  Current threshold: {config.SIMILARITY_THRESHOLD:.0%}")
    above = sum(1 for b, c in dist.get("histogram", {}).items()
                if float(b.split("-")[0]) >= config.SIMILARITY_THRESHOLD)
    print(f"  Buckets at/above threshold: {above}")
    print("="*50)


# ─── Entry Point ────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="Trovly")
    parser.add_argument("--once", action="store_true", help="Run a single scan and exit")
    parser.add_argument("--stats", action="store_true", help="Show score distribution diagnostic")
    parser.add_argument("--reset", action="store_true", help="Clear seen-jobs database")
    args = parser.parse_args()

    seen_db = SeenJobsDB()

    if args.reset:
        seen_db.reset()
        print("Seen jobs database cleared.")
        return

    if args.stats:
        run_stats()
        return

    # Preflight checks
    alert_configured = bool(config.DISCORD_WEBHOOK_URL or config.TELEGRAM_BOT_TOKEN)
    if not alert_configured:
        logger.warning("⚠️  No alert channels configured! Set DISCORD_WEBHOOK_URL or TELEGRAM_BOT_TOKEN in config.py")

    any_source = any(config.ENABLED_SOURCES.values())
    if not any_source:
        logger.error("No job sources enabled — edit ENABLED_SOURCES in config.py")
        return

    if config.RESUME_TEXT.strip().startswith("PASTE YOUR"):
        logger.error("⚠️  Resume not configured — paste your resume text into config.py RESUME_TEXT")
        return

    logger.info(f"Trovly starting")
    logger.info(f"  Threshold:  {config.SIMILARITY_THRESHOLD:.0%}")
    logger.info(f"  Interval:   {config.SCAN_INTERVAL_MINUTES} min")
    logger.info(f"  Sources:    {[k for k,v in config.ENABLED_SOURCES.items() if v]}")
    logger.info(f"  Alerts:     Discord={'✓' if config.DISCORD_WEBHOOK_URL else '✗'}  "
                f"Telegram={'✓' if config.TELEGRAM_BOT_TOKEN else '✗'}")
    logger.info(f"  Seen DB:    {seen_db.count()} entries")

    # Run first scan immediately
    run_scan(seen_db)

    if args.once:
        return

    # Schedule recurring scans
    schedule.every(config.SCAN_INTERVAL_MINUTES).minutes.do(run_scan, seen_db)

    logger.info(f"Scheduler active — scanning every {config.SCAN_INTERVAL_MINUTES} minutes (Ctrl+C to stop)")
    try:
        while True:
            schedule.run_pending()
            time.sleep(10)
    except KeyboardInterrupt:
        logger.info("Shutting down gracefully...")


if __name__ == "__main__":
    main()
