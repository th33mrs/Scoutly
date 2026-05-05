"""
Trovly - Application Tracker
Track every job application from applied to offer/rejected.
"""

import json
import logging
import secrets
from datetime import datetime, timedelta
from pathlib import Path

logger = logging.getLogger("trovly.applications")

STATUS_OPTIONS = [
    "Applied",
    "Phone Screen",
    "Interview",
    "Take Home",
    "Final Round",
    "Offer",
    "Rejected",
    "Ghosted",
    "Withdrew",
]

STATUS_COLORS = {
    "Applied": "#fbbf24",
    "Phone Screen": "#f59e0b",
    "Interview": "#f97316",
    "Take Home": "#f97316",
    "Final Round": "#ec4899",
    "Offer": "#10b981",
    "Rejected": "#ef4444",
    "Ghosted": "#6b7280",
    "Withdrew": "#6b7280",
}

ACTIVE_STATUSES = {"Applied", "Phone Screen", "Interview", "Take Home", "Final Round"}


def _path():
    return Path("applications.json")


def _load():
    if not _path().exists():
        return {}
    try:
        return json.loads(_path().read_text())
    except Exception as e:
        logger.error("Error loading applications: {}".format(e))
        return {}


def _save(data):
    _path().write_text(json.dumps(data, indent=2))


def list_applications(username, status_filter=None, sort_by="date_applied", reverse=True):
    """List applications for a user with optional filter and sort."""
    all_data = _load()
    apps = all_data.get(username, [])

    if status_filter:
        apps = [a for a in apps if a.get("status") in status_filter]

    return sorted(apps, key=lambda a: a.get(sort_by, ""), reverse=reverse)


def get_application(username, app_id):
    """Get a specific application."""
    apps = _load().get(username, [])
    for a in apps:
        if a.get("id") == app_id:
            return a
    return None


def add_application(username, title, company, url="", location="", salary="", source="manual", notes=""):
    """Add a new application."""
    if not title or not company:
        return False, "Title and company required", None

    all_data = _load()
    apps = all_data.get(username, [])

    # Check for duplicate (same company + title)
    for a in apps:
        if (a.get("title", "").lower() == title.lower() and
            a.get("company", "").lower() == company.lower()):
            return False, "You already tracked this application", a.get("id")

    new_id = secrets.token_urlsafe(8)
    now = datetime.now().isoformat()

    new_app = {
        "id": new_id,
        "title": title.strip(),
        "company": company.strip(),
        "url": url.strip(),
        "location": location.strip(),
        "salary": salary.strip(),
        "source": source,
        "status": "Applied",
        "notes": notes.strip(),
        "date_applied": now,
        "last_updated": now,
        "status_history": [{"status": "Applied", "date": now}],
        "follow_up_date": None,
    }

    apps.append(new_app)
    all_data[username] = apps
    _save(all_data)
    return True, "Application tracked", new_id


def update_application(username, app_id, updates):
    """Update fields on an application."""
    all_data = _load()
    apps = all_data.get(username, [])

    for a in apps:
        if a.get("id") == app_id:
            # Track status changes in history
            if "status" in updates and updates["status"] != a.get("status"):
                history = a.get("status_history", [])
                history.append({
                    "status": updates["status"],
                    "date": datetime.now().isoformat(),
                })
                a["status_history"] = history

            a.update(updates)
            a["last_updated"] = datetime.now().isoformat()
            all_data[username] = apps
            _save(all_data)
            return True, "Updated"

    return False, "Application not found"


def delete_application(username, app_id):
    """Delete an application."""
    all_data = _load()
    apps = all_data.get(username, [])
    apps = [a for a in apps if a.get("id") != app_id]
    all_data[username] = apps
    _save(all_data)
    return True, "Deleted"


def get_follow_ups(username, days_threshold=7):
    """Get applications that need follow-up (active >N days, no recent update)."""
    apps = list_applications(username, status_filter=ACTIVE_STATUSES)
    cutoff = datetime.now() - timedelta(days=days_threshold)
    follow_ups = []

    for a in apps:
        try:
            last_updated = datetime.fromisoformat(a.get("last_updated", ""))
            if last_updated < cutoff:
                days_since = (datetime.now() - last_updated).days
                follow_ups.append({**a, "days_since_update": days_since})
        except Exception:
            continue

    return sorted(follow_ups, key=lambda a: a.get("days_since_update", 0), reverse=True)


def get_stats(username):
    """Calculate application statistics."""
    apps = list_applications(username)
    if not apps:
        return {
            "total": 0,
            "active": 0,
            "interviews": 0,
            "offers": 0,
            "rejected": 0,
            "interview_rate": 0,
            "offer_rate": 0,
            "by_status": {},
            "by_source": {},
        }

    total = len(apps)
    by_status = {}
    by_source = {}

    for a in apps:
        status = a.get("status", "Applied")
        source = a.get("source", "manual")
        by_status[status] = by_status.get(status, 0) + 1
        by_source[source] = by_source.get(source, 0) + 1

    interviews = sum(by_status.get(s, 0) for s in
                     ["Phone Screen", "Interview", "Take Home", "Final Round", "Offer"])
    offers = by_status.get("Offer", 0)
    rejected = by_status.get("Rejected", 0)
    active = sum(by_status.get(s, 0) for s in ACTIVE_STATUSES)

    return {
        "total": total,
        "active": active,
        "interviews": interviews,
        "offers": offers,
        "rejected": rejected,
        "interview_rate": round(interviews / total * 100, 1) if total else 0,
        "offer_rate": round(offers / total * 100, 1) if total else 0,
        "by_status": by_status,
        "by_source": by_source,
    }
