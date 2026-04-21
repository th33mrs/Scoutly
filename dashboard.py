"""
Scoutly - Dashboard & Export
Usage:
  python dashboard.py                 → Show dashboard
  python dashboard.py --export        → Export to CSV
  python dashboard.py --summary       → Send weekly summary to Discord
  python dashboard.py --status SEARCH STATUS  → Update job status
  python dashboard.py --search KEYWORD       → Search tracked jobs
"""

import argparse
import csv
import json
import logging
from datetime import datetime
from pathlib import Path

import requests

import config
from tracker import JobTracker

logger = logging.getLogger("job_scanner.dashboard")


def show_dashboard(tracker):
    stats = tracker.get_stats()
    if stats["total"] == 0:
        print("\nNo tracked jobs yet. Run a scan first: python main.py --once")
        return

    print("\n" + "=" * 65)
    print("  JOB SCANNER DASHBOARD")
    print("=" * 65)

    print("\n  OVERVIEW")
    print("  Total tracked:    {}".format(stats["total"]))
    print("  Avg match score:  {:.1%}".format(stats["avg_score"]))
    print("  Top match score:  {:.1%}".format(stats["top_score"]))

    print("\n  BY STATUS")
    for status, count in sorted(stats.get("by_status", {}).items()):
        bar = "#" * count
        print("    {:<14s} {:>3d}  {}".format(status, count, bar))

    print("\n  BY SOURCE")
    for source, count in sorted(stats.get("by_source", {}).items(), key=lambda x: -x[1]):
        bar = "#" * count
        print("    {:<14s} {:>3d}  {}".format(source, count, bar))

    new_jobs = tracker.get_by_status("new")
    if new_jobs:
        print("\n  NEW JOBS (awaiting review)")
        print("  " + "-" * 63)
        for j in sorted(new_jobs, key=lambda x: -x["match_score"])[:15]:
            print("    {:.0%}  {} at {}".format(
                j["match_score"], j["title"][:35], j["company"][:20],
            ))
            print("         {}".format(j["url"][:60]))

    applied = tracker.get_by_status("applied")
    if applied:
        print("\n  APPLIED ({})".format(len(applied)))
        print("  " + "-" * 63)
        for j in applied:
            applied_str = j.get("applied_at", "")[:10] if j.get("applied_at") else "?"
            print("    {} | {} at {}".format(applied_str, j["title"][:30], j["company"][:20]))

    print("\n" + "=" * 65)


def export_csv(tracker, filename="job_matches.csv"):
    jobs = tracker.get_all()
    if not jobs:
        print("No jobs to export.")
        return
    fields = [
        "title", "company", "location", "match_score", "status",
        "source", "salary", "posted_date", "found_at", "applied_at",
        "url", "notes", "tags",
    ]
    with open(filename, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for job in sorted(jobs, key=lambda x: -x["match_score"]):
            row = dict(job)
            row["tags"] = ", ".join(row.get("tags", []))
            row["match_score"] = "{:.1%}".format(row["match_score"])
            writer.writerow(row)
    print("Exported {} jobs to {}".format(len(jobs), filename))


def send_weekly_summary(tracker):
    if not config.DISCORD_WEBHOOK_URL:
        print("Discord webhook not configured.")
        return
    recent = tracker.recent(days=7)
    stats = tracker.get_stats()
    if not recent:
        desc = "No new job matches this week."
    else:
        top_jobs = sorted(recent, key=lambda x: -x["match_score"])[:10]
        lines = []
        for j in top_jobs:
            status_emoji = {
                "new": "new", "reviewing": "eyes", "applied": "check",
                "interviewing": "dart", "rejected": "x", "offer": "tada", "skipped": "skip",
            }.get(j["status"], "?")
            lines.append("[{}] {:.0%} - {} at {}".format(
                status_emoji, j["match_score"], j["title"][:40], j["company"],
            ))
        desc = "\n".join(lines)
    by_status = stats.get("by_status", {})
    status_line = " | ".join("{}: {}".format(k, v) for k, v in sorted(by_status.items()))
    embed = {
        "title": "Weekly Job Scanner Summary",
        "color": 0x5865F2,
        "description": desc,
        "fields": [
            {"name": "This Week", "value": "{} new matches".format(len(recent)), "inline": True},
            {"name": "All Time", "value": "{} total tracked".format(stats["total"]), "inline": True},
            {"name": "Avg Score", "value": "{:.1%}".format(stats.get("avg_score", 0)), "inline": True},
            {"name": "Pipeline", "value": status_line or "n/a", "inline": False},
        ],
    }
    payload = {"username": "Scoutly", "embeds": [embed]}
    try:
        resp = requests.post(config.DISCORD_WEBHOOK_URL, json=payload, timeout=10)
        if resp.status_code == 204:
            print("Weekly summary sent to Discord!")
        else:
            print("Discord error {}: {}".format(resp.status_code, resp.text))
    except Exception as e:
        print("Discord send failed: {}".format(e))


def update_status(tracker, uid_fragment, status, notes=None):
    matches = [j for j in tracker.get_all() if uid_fragment.lower() in j["uid"].lower()
               or uid_fragment.lower() in j["title"].lower()]
    if not matches:
        print("No job found matching '{}'".format(uid_fragment))
        return
    if len(matches) > 1:
        print("Multiple matches for '{}':".format(uid_fragment))
        for j in matches:
            print("  - {} at {}".format(j["title"], j["company"]))
        print("Be more specific.")
        return
    job = matches[0]
    if tracker.update_status(job["uid"], status, notes):
        print("Updated '{}' -> {}".format(job["title"], status))


def search_jobs(tracker, keyword):
    results = tracker.search(keyword)
    if not results:
        print("No matches for '{}'".format(keyword))
        return
    print("\nFound {} results for '{}':".format(len(results), keyword))
    print("-" * 65)
    for j in sorted(results, key=lambda x: -x["match_score"]):
        print("  {:.0%} | {:<14s} | {} at {}".format(
            j["match_score"], j["status"], j["title"][:30], j["company"][:20],
        ))
        print("       {}".format(j["url"][:60]))


def main():
    parser = argparse.ArgumentParser(description="Job Scanner Dashboard")
    parser.add_argument("--export", action="store_true")
    parser.add_argument("--summary", action="store_true")
    parser.add_argument("--status", nargs=2, metavar=("SEARCH", "STATUS"))
    parser.add_argument("--notes", type=str)
    parser.add_argument("--search", type=str)
    args = parser.parse_args()
    tracker = JobTracker()
    if args.export:
        export_csv(tracker)
    elif args.summary:
        send_weekly_summary(tracker)
    elif args.status:
        update_status(tracker, args.status[0], args.status[1], args.notes)
    elif args.search:
        search_jobs(tracker, args.search)
    else:
        show_dashboard(tracker)


if __name__ == "__main__":
    main()
