import json
import logging
from datetime import datetime
from pathlib import Path

logger = logging.getLogger("job_scanner.saved_jds")

class SavedJDs:
    def __init__(self, path="saved_jds.json"):
        self.path = Path(path)
        self.entries = []
        self._load()

    def _load(self):
        if self.path.exists():
            try:
                self.entries = json.loads(self.path.read_text())
            except json.JSONDecodeError:
                self.entries = []

    def _save(self):
        self.path.write_text(json.dumps(self.entries, indent=2))

    def add(self, title, company, jd_text, analysis=None, url=""):
        entry = {
            "id": len(self.entries) + 1,
            "title": title,
            "company": company,
            "url": url,
            "jd_text": jd_text,
            "saved_at": datetime.now().isoformat(),
            "analysis": {
                "strong_count": len(analysis.get("strong_bullets", [])) if analysis else 0,
                "moderate_count": len(analysis.get("moderate_bullets", [])) if analysis else 0,
                "weak_count": len(analysis.get("weak_bullets", [])) if analysis else 0,
                "skill_matches": analysis.get("skill_matches", []) if analysis else [],
                "skill_gaps": analysis.get("skill_gaps", []) if analysis else [],
                "keywords_matched": analysis.get("jd_keywords_found", 0) if analysis else 0,
                "keywords_missing": analysis.get("jd_keywords_missing", 0) if analysis else 0,
            },
            "notes": "",
            "status": "saved",
        }
        for existing in self.entries:
            if existing["title"].lower() == title.lower() and existing["company"].lower() == company.lower():
                existing.update(entry)
                self._save()
                return existing["id"]
        self.entries.append(entry)
        self._save()
        return entry["id"]

    def get_all(self):
        return self.entries

    def get_by_id(self, jd_id):
        for e in self.entries:
            if e["id"] == jd_id:
                return e
        return None

    def search(self, keyword):
        kw = keyword.lower()
        return [e for e in self.entries
                if kw in e["title"].lower()
                or kw in e["company"].lower()
                or kw in e.get("jd_text", "").lower()]

    def delete(self, jd_id):
        self.entries = [e for e in self.entries if e["id"] != jd_id]
        self._save()

    def update_notes(self, jd_id, notes):
        for e in self.entries:
            if e["id"] == jd_id:
                e["notes"] = notes
                self._save()
                return True
        return False

    def count(self):
        return len(self.entries)
