"""
Job Scanner Bot - Job Tracker
"""

import json
import logging
from datetime import datetime
from pathlib import Path

logger = logging.getLogger("job_scanner.tracker")

TRACKER_DB = "tracked_jobs.json"


class JobTracker:
    STATUSES = ["new", "reviewing", "applied", "interviewing", "rejected", "offer", "skipped"]

    def __init__(self, path=TRACKER_DB):
        self.path = Path(path)
        self.jobs = []
        self._load()

    def _load(self):
        if self.path.exists():
            try:
                self.jobs = json.loads(self.path.read_text())
            except json.JSONDecodeError:
                self.jobs = []

    def _save(self):
        self.path.write_text(json.dumps(self.jobs, indent=2))

    def add_job(self, job, score):
        entry = {
            "uid": job.uid,
            "title": job.title,
            "company": job.company,
            "location": job.location,
            "url": job.url,
            "source": job.source,
            "salary": job.salary,
            "posted_date": job.posted_date,
            "match_score": round(score, 4),
            "status": "new",
            "found_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "notes": "",
            "applied_at": None,
            "tags": [],
        }
        if not any(j["uid"] == job.uid for j in self.jobs):
            self.jobs.append(entry)
            self._save()
            logger.info("Tracked: {} at {} ({:.1%})".format(job.title, job.company, score))
            return True
        return False

    def update_status(self, uid, status, notes=None):
        if status not in self.STATUSES:
            return False
        for job in self.jobs:
            if job["uid"] == uid:
                job["status"] = status
                job["updated_at"] = datetime.now().isoformat()
                if notes:
                    job["notes"] = notes
                if status == "applied":
                    job["applied_at"] = datetime.now().isoformat()
                self._save()
                return True
        return False

    def add_tags(self, uid, tags):
        for job in self.jobs:
            if job["uid"] == uid:
                existing = set(job.get("tags", []))
                existing.update(tags)
                job["tags"] = list(existing)
                self._save()
                return True
        return False

    def get_by_status(self, status):
        return [j for j in self.jobs if j["status"] == status]

    def get_all(self):
        return self.jobs

    def get_stats(self):
        total = len(self.jobs)
        if total == 0:
            return {"total": 0}
        by_status = {}
        for j in self.jobs:
            s = j["status"]
            by_status[s] = by_status.get(s, 0) + 1
        scores = [j["match_score"] for j in self.jobs]
        by_source = {}
        for j in self.jobs:
            s = j["source"]
            by_source[s] = by_source.get(s, 0) + 1
        return {
            "total": total,
            "by_status": by_status,
            "by_source": by_source,
            "avg_score": round(sum(scores) / len(scores), 4),
            "top_score": max(scores),
            "lowest_score": min(scores),
        }

    def search(self, keyword):
        kw = keyword.lower()
        return [
            j for j in self.jobs
            if kw in j["title"].lower()
            or kw in j["company"].lower()
            or kw in j.get("notes", "").lower()
            or kw in " ".join(j.get("tags", [])).lower()
        ]

    def recent(self, days=7):
        cutoff = datetime.now().timestamp() - (days * 86400)
        results = []
        for j in self.jobs:
            try:
                found_ts = datetime.fromisoformat(j["found_at"]).timestamp()
                if found_ts >= cutoff:
                    results.append(j)
            except (ValueError, KeyError):
                pass
        return results
