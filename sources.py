"""
Scoutly - Source Plugins
=================================
Each source returns a list of JobPosting dataclass instances.
"""

import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

import feedparser
import requests

import config

logger = logging.getLogger("job_scanner.sources")


@dataclass
class JobPosting:
    title: str
    company: str
    description: str
    url: str
    location: str = ""
    source: str = ""
    posted_date: Optional[str] = None
    salary: Optional[str] = None
    uid: str = ""

    def __post_init__(self):
        if not self.uid:
            self.uid = "{}:{}".format(self.source, self.url)


def fetch_adzuna(queries):
    if not config.ADZUNA_APP_ID or not config.ADZUNA_APP_KEY:
        logger.warning("Adzuna API keys not configured — skipping")
        return []
    jobs = []
    base = "https://api.adzuna.com/v1/api/jobs/{}/search/1".format(config.ADZUNA_COUNTRY)
    for q in queries:
        try:
            params = {
                "app_id": config.ADZUNA_APP_ID,
                "app_key": config.ADZUNA_APP_KEY,
                "what": q, "where": config.LOCATION,
                "results_per_page": 20, "content-type": "application/json",
            }
            resp = requests.get(base, params=params, timeout=15)
            resp.raise_for_status()
            data = resp.json()
            for r in data.get("results", []):
                salary_str = None
                if r.get("salary_min") and r.get("salary_max"):
                    salary_str = "${:,.0f} - ${:,.0f}".format(r["salary_min"], r["salary_max"])
                jobs.append(JobPosting(
                    title=r.get("title", ""), company=r.get("company", {}).get("display_name", "Unknown"),
                    description=r.get("description", ""), url=r.get("redirect_url", ""),
                    location=r.get("location", {}).get("display_name", ""), source="adzuna",
                    posted_date=r.get("created", ""), salary=salary_str,
                ))
            time.sleep(0.5)
        except Exception as e:
            logger.error("Adzuna error for '{}': {}".format(q, e))
    return jobs


def fetch_remotive(queries):
    jobs = []
    for q in queries:
        try:
            resp = requests.get("https://remotive.com/api/remote-jobs", params={"search": q, "limit": 20}, timeout=15)
            resp.raise_for_status()
            for r in resp.json().get("jobs", []):
                jobs.append(JobPosting(
                    title=r.get("title", ""), company=r.get("company_name", "Unknown"),
                    description=r.get("description", ""), url=r.get("url", ""),
                    location=r.get("candidate_required_location", "Remote"), source="remotive",
                    posted_date=r.get("publication_date", ""), salary=r.get("salary", None),
                    uid="remotive:{}".format(r.get("id", r.get("url", ""))),
                ))
            time.sleep(0.5)
        except Exception as e:
            logger.error("Remotive error for '{}': {}".format(q, e))
    return jobs


def fetch_arbeitnow(queries):
    jobs = []
    for q in queries:
        try:
            resp = requests.get("https://www.arbeitnow.com/api/job-board-api", params={"search": q, "page": 1}, timeout=15)
            resp.raise_for_status()
            for r in resp.json().get("data", []):
                if config.REMOTE_ONLY and not r.get("remote", False):
                    continue
                jobs.append(JobPosting(
                    title=r.get("title", ""), company=r.get("company_name", "Unknown"),
                    description=r.get("description", ""), url=r.get("url", ""),
                    location=r.get("location", ""), source="arbeitnow",
                    posted_date=r.get("created_at", ""),
                    uid="arbeitnow:{}".format(r.get("slug", r.get("url", ""))),
                ))
            time.sleep(0.5)
        except Exception as e:
            logger.error("Arbeitnow error for '{}': {}".format(q, e))
    return jobs


def fetch_usajobs(queries):
    if not config.USAJOBS_API_KEY or not config.USAJOBS_EMAIL:
        logger.warning("USAJobs credentials not configured — skipping")
        return []
    jobs = []
    headers = {"Authorization-Key": config.USAJOBS_API_KEY, "User-Agent": config.USAJOBS_EMAIL}
    for q in queries:
        try:
            resp = requests.get("https://data.usajobs.gov/api/Search",
                params={"Keyword": q, "LocationName": config.LOCATION, "ResultsPerPage": 20},
                headers=headers, timeout=15)
            resp.raise_for_status()
            for item in resp.json().get("SearchResult", {}).get("SearchResultItems", []):
                r = item.get("MatchedObjectDescriptor", {})
                pos_loc = r.get("PositionLocation", [{}])
                loc = pos_loc[0].get("LocationName", "") if pos_loc else ""
                salary_str = None
                remun = r.get("PositionRemuneration", [{}])
                if remun:
                    salary_str = "${} - ${}".format(remun[0].get("MinimumRange", "?"), remun[0].get("MaximumRange", "?"))
                desc = ""
                if r.get("UserArea"):
                    duties = r["UserArea"].get("Details", {}).get("MajorDuties", [""])
                    desc = duties[0] if duties else ""
                else:
                    desc = r.get("QualificationSummary", "")
                jobs.append(JobPosting(
                    title=r.get("PositionTitle", ""), company=r.get("OrganizationName", "US Government"),
                    description=desc, url=r.get("PositionURI", ""), location=loc, source="usajobs",
                    posted_date=r.get("PublicationStartDate", ""), salary=salary_str,
                    uid="usajobs:{}".format(r.get("PositionID", "")),
                ))
            time.sleep(0.5)
        except Exception as e:
            logger.error("USAJobs error for '{}': {}".format(q, e))
    return jobs


def fetch_the_muse(queries):
    jobs = []
    for q in queries:
        try:
            resp = requests.get("https://www.themuse.com/api/public/jobs", params={"page": 1, "descending": "true"}, timeout=15)
            resp.raise_for_status()
            query_lower = q.lower()
            for r in resp.json().get("results", []):
                title = r.get("name", "")
                desc = r.get("contents", "")
                if query_lower not in title.lower() and query_lower not in desc.lower():
                    continue
                locs = r.get("locations", [])
                loc_str = ", ".join(l.get("name", "") for l in locs) if locs else ""
                jobs.append(JobPosting(
                    title=title, company=r.get("company", {}).get("name", "Unknown"),
                    description=desc, url=r.get("refs", {}).get("landing_page", ""),
                    location=loc_str, source="the_muse", posted_date=r.get("publication_date", ""),
                    uid="the_muse:{}".format(r.get("id", "")),
                ))
        except Exception as e:
            logger.error("The Muse error for '{}': {}".format(q, e))
    return jobs


def fetch_jobicy(queries):
    """Jobicy.com — remote jobs, free JSON API. No key needed."""
    jobs = []
    for q in queries:
        try:
            resp = requests.get("https://jobicy.com/api/v2/remote-jobs",
                params={"count": 50, "geo": "usa", "tag": q}, timeout=15)
            resp.raise_for_status()
            for r in resp.json().get("jobs", []):
                salary_str = None
                sal_min = r.get("annualSalaryMin") or r.get("salaryMin")
                sal_max = r.get("annualSalaryMax") or r.get("salaryMax")
                sal_currency = r.get("salaryCurrency", "USD")
                if sal_min and sal_max:
                    salary_str = "{} {} - {}".format(sal_currency, sal_min, sal_max)
                elif sal_min:
                    salary_str = "{} {}+".format(sal_currency, sal_min)
                jobs.append(JobPosting(
                    title=r.get("jobTitle", ""), company=r.get("companyName", "Unknown"),
                    description=r.get("jobDescription", "") or r.get("jobExcerpt", ""),
                    url=r.get("url", ""), location=r.get("jobGeo", "Remote"), source="jobicy",
                    posted_date=r.get("pubDate", ""), salary=salary_str,
                    uid="jobicy:{}".format(r.get("id", r.get("url", ""))),
                ))
            time.sleep(1)
        except Exception as e:
            logger.error("Jobicy error for '{}': {}".format(q, e))
    return jobs


def fetch_himalayas(queries):
    """Himalayas.app — remote jobs via RSS feed. No key needed."""
    jobs = []
    try:
        feed = feedparser.parse("https://himalayas.app/jobs/rss")
        for entry in feed.entries[:50]:
            desc = entry.get("summary", "") or entry.get("description", "")
            title = entry.get("title", "")
            combined = (title + " " + desc).lower()
            if not any(q.lower() in combined for q in queries):
                continue
            jobs.append(JobPosting(
                title=title, company=entry.get("author", "Unknown"),
                description=desc, url=entry.get("link", ""), location="Remote",
                source="himalayas", posted_date=entry.get("published", ""),
                uid="himalayas:{}".format(entry.get("link", "")),
            ))
    except Exception as e:
        logger.error("Himalayas error: {}".format(e))
    return jobs


def fetch_rss_feeds(queries):
    if not config.RSS_FEEDS:
        return []
    jobs = []
    for feed_url in config.RSS_FEEDS:
        try:
            feed = feedparser.parse(feed_url)
            for entry in feed.entries[:30]:
                desc = entry.get("summary", "") or entry.get("description", "")
                jobs.append(JobPosting(
                    title=entry.get("title", ""), company=entry.get("author", "Unknown"),
                    description=desc, url=entry.get("link", ""), source="rss",
                    posted_date=entry.get("published", ""),
                    uid="rss:{}".format(entry.get("link", "")),
                ))
        except Exception as e:
            logger.error("RSS feed error for '{}': {}".format(feed_url, e))
    return jobs


SOURCE_MAP = {
    "adzuna": fetch_adzuna,
    "remotive": fetch_remotive,
    "arbeitnow": fetch_arbeitnow,
    "usajobs": fetch_usajobs,
    "the_muse": fetch_the_muse,
    "jobicy": fetch_jobicy,
    "himalayas": fetch_himalayas,
    "rss_feeds": fetch_rss_feeds,
}


def fetch_all_jobs():
    all_jobs = []
    for source_name, fetcher in SOURCE_MAP.items():
        if config.ENABLED_SOURCES.get(source_name, False):
            logger.info("Fetching from {}...".format(source_name))
            try:
                results = fetcher(config.SEARCH_QUERIES)
                logger.info("  -> {} jobs from {}".format(len(results), source_name))
                all_jobs.extend(results)
            except Exception as e:
                logger.error("Source {} failed: {}".format(source_name, e))
    seen = set()
    unique = []
    for job in all_jobs:
        if job.uid not in seen:
            seen.add(job.uid)
            unique.append(job)
    logger.info("Total unique jobs fetched: {}".format(len(unique)))
    return unique
