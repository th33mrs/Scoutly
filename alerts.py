"""
Job Scanner Bot - Alert System
================================
Sends matched job notifications via Discord and/or Telegram.
"""

import logging
from textwrap import shorten

import requests

import config
from sources import JobPosting

logger = logging.getLogger("job_scanner.alerts")


def _format_job_text(job: JobPosting, score: float) -> str:
    """Plain-text format for a matched job."""
    lines = [
        f"🎯 Match: {score:.1%}",
        f"📋 {job.title}",
        f"🏢 {job.company}",
    ]
    if job.location:
        lines.append(f"📍 {job.location}")
    if job.salary:
        lines.append(f"💰 {job.salary}")
    if job.posted_date:
        lines.append(f"📅 {job.posted_date[:10]}")
    lines.append(f"🔗 {job.url}")
    lines.append(f"📡 Source: {job.source}")
    return "\n".join(lines)


# ─── Discord ────────────────────────────────────────────────────────
def send_discord_alert(job: JobPosting, score: float) -> bool:
    """Send a rich embed to Discord via webhook."""
    if not config.DISCORD_WEBHOOK_URL:
        return False

    desc_clean = shorten(job.description[:300], width=280, placeholder="...")

    embed = {
        "title": f"🎯 {score:.1%} Match — {job.title}",
        "url": job.url,
        "color": _score_color(score),
        "fields": [
            {"name": "Company", "value": job.company or "—", "inline": True},
            {"name": "Location", "value": job.location or "—", "inline": True},
            {"name": "Source", "value": job.source, "inline": True},
        ],
        "description": desc_clean,
    }
    if job.salary:
        embed["fields"].append({"name": "Salary", "value": job.salary, "inline": True})
    if job.posted_date:
        embed["fields"].append({"name": "Posted", "value": job.posted_date[:10], "inline": True})

    payload = {
        "username": "Job Scanner Bot",
        "embeds": [embed],
    }

    try:
        resp = requests.post(config.DISCORD_WEBHOOK_URL, json=payload, timeout=10)
        if resp.status_code == 204:
            logger.info(f"Discord alert sent: {job.title}")
            return True
        else:
            logger.error(f"Discord error {resp.status_code}: {resp.text}")
            return False
    except Exception as e:
        logger.error(f"Discord send failed: {e}")
        return False


def _score_color(score: float) -> int:
    """Green for high scores, yellow for mid, orange for threshold."""
    if score >= 0.95:
        return 0x00FF00   # bright green
    elif score >= 0.90:
        return 0x7CFC00   # lawn green
    elif score >= 0.85:
        return 0xFFD700   # gold
    return 0xFFA500       # orange


# ─── Telegram ───────────────────────────────────────────────────────
def send_telegram_alert(job: JobPosting, score: float) -> bool:
    """Send alert via Telegram Bot API."""
    if not config.TELEGRAM_BOT_TOKEN or not config.TELEGRAM_CHAT_ID:
        return False

    text = _format_job_text(job, score)
    url = f"https://api.telegram.org/bot{config.TELEGRAM_BOT_TOKEN}/sendMessage"

    try:
        resp = requests.post(url, json={
            "chat_id": config.TELEGRAM_CHAT_ID,
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": False,
        }, timeout=10)

        if resp.status_code == 200:
            logger.info(f"Telegram alert sent: {job.title}")
            return True
        else:
            logger.error(f"Telegram error {resp.status_code}: {resp.text}")
            return False
    except Exception as e:
        logger.error(f"Telegram send failed: {e}")
        return False


# ─── Dispatch ───────────────────────────────────────────────────────
def send_alerts(matched_jobs: list[tuple[JobPosting, float]]) -> dict:
    """
    Send alerts for all matched jobs to all configured channels.
    Returns summary dict.
    """
    stats = {"discord": 0, "telegram": 0, "total": len(matched_jobs)}

    for job, score in matched_jobs:
        if config.DISCORD_WEBHOOK_URL:
            if send_discord_alert(job, score):
                stats["discord"] += 1

        if config.TELEGRAM_BOT_TOKEN:
            if send_telegram_alert(job, score):
                stats["telegram"] += 1

    logger.info(f"Alerts sent — Discord: {stats['discord']}, Telegram: {stats['telegram']}")
    return stats
