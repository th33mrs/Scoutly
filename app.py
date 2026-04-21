"""
Scoutly Bot - Streamlit Dashboard
Run with: streamlit run app.py
"""

import json
import csv
import io
from datetime import datetime

import streamlit as st
import numpy as np
from sentence_transformers import SentenceTransformer

from tracker import JobTracker
from tailor import tailor_resume, _extract_keywords, _clean_text
import config

st.set_page_config(
    page_title="Scoutly",
    page_icon="mag",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600&family=Outfit:wght@300;400;500;600;700&display=swap');

html, body, [class*="css"] {
    font-family: 'Outfit', sans-serif;
}

code, .stCode, pre {
    font-family: 'JetBrains Mono', monospace !important;
}

.main .block-container {
    padding-top: 2rem;
    max-width: 1200px;
}

h1 { font-weight: 700 !important; letter-spacing: -0.02em !important; }
h2, h3 { font-weight: 600 !important; letter-spacing: -0.01em !important; }

div[data-testid="stMetric"] {
    background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
    border: 1px solid #0f3460;
    border-radius: 12px;
    padding: 16px 20px;
    box-shadow: 0 4px 16px rgba(0,0,0,0.2);
}

div[data-testid="stMetric"] label {
    color: #8892b0 !important;
    font-size: 0.85rem !important;
    text-transform: uppercase;
    letter-spacing: 0.08em;
}

div[data-testid="stMetric"] div[data-testid="stMetricValue"] {
    color: #e6f1ff !important;
    font-weight: 600 !important;
    font-size: 1.8rem !important;
}

div.stButton > button {
    border-radius: 8px;
    font-weight: 500;
    font-family: 'Outfit', sans-serif;
    transition: all 0.2s ease;
}

div.stButton > button:hover {
    transform: translateY(-1px);
    box-shadow: 0 4px 12px rgba(0,0,0,0.15);
}

.bullet-strong {
    background: rgba(100, 255, 218, 0.08);
    border-left: 3px solid #64ffda;
    padding: 8px 12px;
    margin: 4px 0;
    border-radius: 0 6px 6px 0;
}

.bullet-moderate {
    background: rgba(255, 203, 107, 0.06);
    border-left: 3px solid #ffcb6b;
    padding: 8px 12px;
    margin: 4px 0;
    border-radius: 0 6px 6px 0;
}

.bullet-weak {
    background: rgba(255, 83, 112, 0.05);
    border-left: 3px solid #ff5370;
    padding: 8px 12px;
    margin: 4px 0;
    border-radius: 0 6px 6px 0;
}
</style>
""", unsafe_allow_html=True)

tracker = JobTracker()


def get_status_emoji(status):
    return {
        "new": "🆕", "reviewing": "👀", "applied": "✅",
        "interviewing": "🎯", "rejected": "❌", "offer": "🎉", "skipped": "⏭️",
    }.get(status, "❓")


# ─── Sidebar ────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## ⚡ Scoutly")
    st.markdown("---")
    stats = tracker.get_stats()
    if stats["total"] > 0:
        st.metric("Total Tracked", stats["total"])
        st.metric("Avg Match Score", "{:.0%}".format(stats["avg_score"]))
        st.metric("Top Score", "{:.0%}".format(stats["top_score"]))
        st.markdown("---")
        st.markdown("#### Pipeline")
        for status, count in sorted(stats.get("by_status", {}).items()):
            emoji = get_status_emoji(status)
            st.markdown("{} **{}**: {}".format(emoji, status.title(), count))
        st.markdown("---")
        st.markdown("#### Sources")
        for source, count in sorted(stats.get("by_source", {}).items(), key=lambda x: -x[1]):
            st.markdown("📡 **{}**: {}".format(source, count))
    else:
        st.info("No jobs tracked yet.\n```\npython main.py --once\n```")
    st.markdown("---")
    st.markdown(
        "<div style='text-align:center;color:#676e95;font-size:0.75rem;'>"
        "Scoutly v1.0 · {} sources active"
        "</div>".format(sum(1 for v in config.ENABLED_SOURCES.values() if v)),
        unsafe_allow_html=True,
    )

# ─── Main ───────────────────────────────────────────────────────────
st.markdown("# 🎯 Scoutly Dashboard")
tab1, tab2, tab3, tab4 = st.tabs(["📋 Jobs", "📊 Analytics", "✂️ Resume Tailor", "⚙️ Settings"])

# ─── Tab 1: Jobs ────────────────────────────────────────────────────
with tab1:
    jobs = tracker.get_all()
    if not jobs:
        st.info("No tracked jobs yet. Run `python main.py --once` to start scanning.")
    else:
        col_f1, col_f2, col_f3 = st.columns(3)
        with col_f1:
            status_filter = st.multiselect(
                "Filter by Status", options=JobTracker.STATUSES,
                default=["new", "reviewing", "applied", "interviewing"],
            )
        with col_f2:
            sources = list(set(j["source"] for j in jobs))
            source_filter = st.multiselect("Filter by Source", options=sorted(sources), default=sources)
        with col_f3:
            min_score = st.slider("Min Match Score", 0.0, 1.0, 0.0, 0.05, format="%.0f%%")

        filtered = [
            j for j in jobs
            if j["status"] in status_filter
            and j["source"] in source_filter
            and j["match_score"] >= min_score
        ]
        st.markdown("**Showing {} of {} jobs**".format(len(filtered), len(jobs)))

        sort_by = st.selectbox("Sort by", ["Match Score", "Date Found", "Company", "Status"], index=0)
        sort_map = {
            "Match Score": lambda x: -x["match_score"],
            "Date Found": lambda x: x.get("found_at", ""),
            "Company": lambda x: x["company"].lower(),
            "Status": lambda x: x["status"],
        }
        filtered.sort(key=sort_map.get(sort_by, lambda x: -x["match_score"]))

        for idx, job in enumerate(filtered):
            score_pct = "{:.0%}".format(job["match_score"])
            emoji = get_status_emoji(job["status"])
            with st.expander("{} {} — {} at {}".format(emoji, score_pct, job["title"], job["company"])):
                col1, col2, col3 = st.columns([2, 2, 1])
                with col1:
                    st.markdown("**Title:** {}".format(job["title"]))
                    st.markdown("**Company:** {}".format(job["company"]))
                    st.markdown("**Location:** {}".format(job.get("location", "—")))
                    if job.get("salary"):
                        st.markdown("**Salary:** {}".format(job["salary"]))
                with col2:
                    st.markdown("**Source:** {}".format(job["source"]))
                    st.markdown("**Found:** {}".format(job.get("found_at", "")[:10]))
                    if job.get("posted_date"):
                        st.markdown("**Posted:** {}".format(job["posted_date"][:10]))
                    st.markdown("**Score:** {}".format(score_pct))
                with col3:
                    st.link_button("🔗 Apply", job["url"])

                st.markdown("---")
                col_s1, col_s2, col_s3 = st.columns([2, 2, 1])
                with col_s1:
                    new_status = st.selectbox(
                        "Update Status", options=JobTracker.STATUSES,
                        index=JobTracker.STATUSES.index(job["status"]),
                        key="status_{}".format(idx),
                    )
                with col_s2:
                    notes = st.text_input("Notes", value=job.get("notes", ""), key="notes_{}".format(idx))
                with col_s3:
                    st.markdown("<br>", unsafe_allow_html=True)
                    if st.button("Save", key="save_{}".format(idx)):
                        tracker.update_status(job["uid"], new_status, notes)
                        st.success("Updated!")
                        st.rerun()

        st.markdown("---")
        if st.button("📥 Export to CSV"):
            output = io.StringIO()
            fields = [
                "title", "company", "location", "match_score", "status",
                "source", "salary", "posted_date", "found_at", "applied_at", "url", "notes",
            ]
            writer = csv.DictWriter(output, fieldnames=fields, extrasaction="ignore")
            writer.writeheader()
            for job in sorted(jobs, key=lambda x: -x["match_score"]):
                row = dict(job)
                row["match_score"] = "{:.1%}".format(row["match_score"])
                writer.writerow(row)
            st.download_button(
                label="Download CSV",
                data=output.getvalue(),
                file_name="job_matches_{}.csv".format(datetime.now().strftime("%Y%m%d")),
                mime="text/csv",
            )

# ─── Tab 2: Analytics ───────────────────────────────────────────────
with tab2:
    jobs = tracker.get_all()
    if not jobs:
        st.info("No data yet. Run a scan first.")
    else:
        import pandas as pd
        st.markdown("### Overview")
        col1, col2, col3, col4 = st.columns(4)
        stats = tracker.get_stats()
        with col1:
            st.metric("Total Jobs", stats["total"])
        with col2:
            st.metric("Avg Score", "{:.0%}".format(stats["avg_score"]))
        with col3:
            st.metric("Applied", len(tracker.get_by_status("applied")))
        with col4:
            st.metric("Awaiting Review", len(tracker.get_by_status("new")))

        st.markdown("### Match Score Distribution")
        scores = [j["match_score"] for j in jobs]
        score_df = pd.DataFrame({"Match Score": scores})
        st.bar_chart(score_df["Match Score"].value_counts(bins=10).sort_index())

        st.markdown("### Jobs by Source")
        source_counts = {}
        for j in jobs:
            s = j["source"]
            source_counts[s] = source_counts.get(s, 0) + 1
        source_df = pd.DataFrame(
            list(source_counts.items()), columns=["Source", "Count"],
        ).sort_values("Count", ascending=False)
        st.bar_chart(source_df.set_index("Source"))

        st.markdown("### Pipeline Status")
        status_counts = stats.get("by_status", {})
        status_df = pd.DataFrame(
            list(status_counts.items()), columns=["Status", "Count"],
        ).sort_values("Count", ascending=False)
        st.bar_chart(status_df.set_index("Status"))

        st.markdown("### Discovery Timeline")
        dates = []
        for j in jobs:
            try:
                dates.append(j["found_at"][:10])
            except (KeyError, TypeError):
                pass
        if dates:
            date_counts = {}
            for d in dates:
                date_counts[d] = date_counts.get(d, 0) + 1
            timeline_df = pd.DataFrame(
                sorted(date_counts.items()), columns=["Date", "Jobs Found"],
            )
            st.line_chart(timeline_df.set_index("Date"))

        st.markdown("### Top 10 Matches")
        top = sorted(jobs, key=lambda x: -x["match_score"])[:10]
        top_data = []
        for j in top:
            top_data.append({
                "Score": "{:.0%}".format(j["match_score"]),
                "Title": j["title"],
                "Company": j["company"],
                "Source": j["source"],
                "Status": j["status"],
            })
        st.table(top_data)

# ─── Tab 3: Resume Tailor ──────────────────────────────────────────
with tab3:
    st.markdown("### ✂️ Resume Tailor")
    st.markdown("Paste a job description to see which resume bullets match, which to cut, and your skill gaps.")

    jd_input = st.text_area(
        "Job Description", height=250,
        placeholder="Paste the full job description here...",
    )

    if st.button("🔍 Analyze Match", type="primary"):
        if jd_input and len(jd_input) > 30:
            with st.spinner("Analyzing resume against job description..."):
                result = tailor_resume(jd_input, verbose=False)
            if "error" in result:
                st.error(result["error"])
            else:
                total = result["total_bullets"]
                strong_pct = len(result["strong_bullets"]) / total * 100 if total else 0

                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("Resume Relevance", "{:.0f}%".format(strong_pct))
                with col2:
                    st.metric("Strong Bullets", len(result["strong_bullets"]))
                with col3:
                    st.metric("Keywords Matched", result["jd_keywords_found"])
                with col4:
                    st.metric("Skill Gaps", result["jd_keywords_missing"])

                st.markdown("#### ✅ Strong Matches — Emphasize These")
                if result["strong_bullets"]:
                    for b in result["strong_bullets"]:
                        st.markdown(
                            "<div class='bullet-strong'><strong>{:.0%}</strong> — {}</div>".format(
                                b["relevance"], b["text"]),
                            unsafe_allow_html=True,
                        )
                else:
                    st.warning("No strong matches. Consider rewriting bullets to mirror the JD language.")

                st.markdown("#### 🟡 Moderate Matches — Keep, Consider Rewording")
                for b in result["moderate_bullets"][:8]:
                    st.markdown(
                        "<div class='bullet-moderate'><strong>{:.0%}</strong> — {}</div>".format(
                            b["relevance"], b["text"]),
                        unsafe_allow_html=True,
                    )

                st.markdown("#### 🔴 Weak Matches — Deprioritize or Cut")
                for b in result["weak_bullets"][:5]:
                    st.markdown(
                        "<div class='bullet-weak'><strong>{:.0%}</strong> — {}</div>".format(
                            b["relevance"], b["text"]),
                        unsafe_allow_html=True,
                    )

                col_s1, col_s2 = st.columns(2)
                with col_s1:
                    st.markdown("#### ✅ Skills You Match")
                    if result["skill_matches"]:
                        for skill in result["skill_matches"]:
                            st.markdown("• {}".format(skill))
                    else:
                        st.markdown("None detected")
                with col_s2:
                    st.markdown("#### ⚠️ Skill Gaps")
                    if result["skill_gaps"]:
                        for gap in result["skill_gaps"]:
                            st.markdown("• **{}**".format(gap))
                        st.info("Add these to your resume if you have any experience — even partial.")
                    else:
                        st.success("No gaps — your resume covers all detected keywords!")

    st.markdown("---")
    st.markdown("#### Quick Tailor from Tracked Jobs")
    tracked = tracker.get_all()
    if tracked:
        job_options = ["{} at {} ({:.0%})".format(j["title"], j["company"], j["match_score"]) for j in tracked]
        selected = st.selectbox("Select a tracked job", options=job_options)
        if selected and st.button("Fetch & Analyze"):
            idx = job_options.index(selected)
            job = tracked[idx]
            st.info("Fetching JD from {}...".format(job["url"][:50]))
            try:
                import requests
                resp = requests.get(job["url"], timeout=15)
                jd_text = _clean_text(resp.text)
                if len(jd_text) > 50:
                    result = tailor_resume(jd_text, verbose=False)
                    if "error" not in result:
                        st.success("Found {} strong, {} moderate, {} weak bullets. {} skill gaps.".format(
                            len(result["strong_bullets"]), len(result["moderate_bullets"]),
                            len(result["weak_bullets"]), result["jd_keywords_missing"],
                        ))
                    else:
                        st.error(result["error"])
                else:
                    st.warning("Could not extract enough text. Paste the JD manually above.")
            except Exception as e:
                st.error("Could not fetch: {}".format(e))
    else:
        st.info("No tracked jobs. Run a scan first.")

# ─── Tab 4: Settings ───────────────────────────────────────────────
with tab4:
    st.markdown("### ⚙️ Scanner Settings")
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**Threshold:** {:.0%}".format(config.SIMILARITY_THRESHOLD))
        st.markdown("**Scan Interval:** {} min".format(config.SCAN_INTERVAL_MINUTES))
        st.markdown("**Location:** {}".format(config.LOCATION))
        st.markdown("**Remote Only:** {}".format(config.REMOTE_ONLY))
    with col2:
        st.markdown("**Discord:** {}".format("Connected" if config.DISCORD_WEBHOOK_URL else "Not configured"))
        st.markdown("**Telegram:** {}".format("Connected" if config.TELEGRAM_BOT_TOKEN else "Not configured"))
        st.markdown("**Adzuna:** {}".format("Connected" if config.ADZUNA_APP_ID else "No API key"))

    st.markdown("#### Active Sources")
    for source, enabled in config.ENABLED_SOURCES.items():
        st.markdown("{} {}".format("✅" if enabled else "❌", source))

    st.markdown("#### Search Queries")
    for q in config.SEARCH_QUERIES:
        st.markdown("• {}".format(q))

    st.markdown("#### Boost Keywords")
    st.markdown(", ".join(config.BOOST_KEYWORDS))

    st.markdown("---")
    st.markdown("#### Quick Actions")
    col_a1, col_a2, col_a3 = st.columns(3)
    with col_a1:
        if st.button("🔄 Reset Seen DB"):
            from pathlib import Path
            seen_path = Path(config.SEEN_JOBS_DB)
            if seen_path.exists():
                seen_path.write_text("{}")
            st.success("Seen jobs database cleared!")
    with col_a2:
        if st.button("🗑️ Clear Tracker"):
            tracker.jobs = []
            tracker._save()
            st.success("Tracker cleared!")
            st.rerun()
    with col_a3:
        if st.button("📊 Send Discord Summary"):
            try:
                from dashboard import send_weekly_summary
                send_weekly_summary(tracker)
                st.success("Summary sent to Discord!")
            except Exception as e:
                st.error("Failed: {}".format(e))

    st.markdown(
        "<div style='text-align:center;color:#676e95;font-size:0.8rem;padding:20px;'>"
        "Edit config.py to change settings. Restart the dashboard after changes."
        "</div>",
        unsafe_allow_html=True,
    )
