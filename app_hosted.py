"""
Trovly - Hosted App
Run with: streamlit run app_hosted.py
"""

import streamlit as st
from auth import login_page, logout, get_user_data, save_user_data
from resume_parser import parse_resume_file
from applications import (
    list_applications, get_application, add_application,
    update_application, delete_application, get_follow_ups,
    get_stats, STATUS_OPTIONS,
)
from usage_limits import (
    get_user_tier, can_scan, can_tailor,
    increment_scans, increment_tailors, get_usage_summary,
    get_tier_limits,
)

st.set_page_config(
    page_title="Trovly",
    page_icon="mag",
    layout="wide",
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Outfit:wght@400;500;600;700&display=swap');

:root {
    --cream: #fef9f0;
    --cream-warm: #fdf3e2;
    --cream-deep: #faead0;
    --white: #ffffff;
    --ink: #1f1612;
    --ink-soft: #3d2f26;
    --muted: #78645a;
    --gold: #f59e0b;
    --gold-light: #fbbf24;
    --coral: #ea580c;
    --pink: #db2777;
    --grad-sunrise: linear-gradient(135deg, #fbbf24 0%, #f59e0b 30%, #ea580c 65%, #db2777 100%);
    --grad-soft: linear-gradient(135deg, #fef3c7 0%, #fed7aa 50%, #fbcfe8 100%);
}

html, body, [class*="css"] { font-family: 'Outfit', sans-serif !important; }

.main .block-container {
    padding-top: 2rem;
    max-width: 1200px;
}

h1, h2, h3 {
    font-weight: 700 !important;
    letter-spacing: -0.02em !important;
    color: #1f1612 !important;
}

h1 {
    background: linear-gradient(135deg, #fbbf24 0%, #f59e0b 30%, #ea580c 65%, #db2777 100%);
    -webkit-background-clip: text;
    background-clip: text;
    -webkit-text-fill-color: transparent;
    display: inline-block;
}

/* Primary buttons - sunrise gradient */
.stButton > button[kind="primary"],
.stButton > button[data-testid="baseButton-primary"] {
    background: linear-gradient(135deg, #fbbf24 0%, #f59e0b 30%, #ea580c 65%, #db2777 100%) !important;
    color: white !important;
    font-weight: 600 !important;
    border: none !important;
    box-shadow: 0 4px 14px rgba(234, 88, 12, 0.3) !important;
    transition: transform 0.15s, box-shadow 0.2s !important;
}

.stButton > button[kind="primary"]:hover,
.stButton > button[data-testid="baseButton-primary"]:hover {
    transform: translateY(-1px) !important;
    box-shadow: 0 8px 24px rgba(234, 88, 12, 0.45) !important;
}

/* Secondary buttons */
.stButton > button:not([kind="primary"]):not([data-testid="baseButton-primary"]) {
    background: white !important;
    color: #1f1612 !important;
    border: 1.5px solid #faead0 !important;
    font-weight: 500 !important;
}

.stButton > button:not([kind="primary"]):not([data-testid="baseButton-primary"]):hover {
    border-color: #ea580c !important;
    color: #ea580c !important;
}

/* Metric cards with coral accent */
div[data-testid="stMetric"] {
    background: white;
    border: 1px solid #faead0;
    border-left: 3px solid #ea580c;
    border-radius: 12px;
    padding: 16px 20px;
    box-shadow: 0 2px 8px rgba(234, 88, 12, 0.06);
}

div[data-testid="stMetric"] label {
    color: #78645a !important;
    font-size: 0.85rem !important;
    font-weight: 500 !important;
}

div[data-testid="stMetric"] div[data-testid="stMetricValue"] {
    color: #1f1612 !important;
    font-weight: 700 !important;
}

/* Tabs */
.stTabs [data-baseweb="tab-list"] {
    gap: 8px;
    border-bottom: 1px solid #faead0;
}

.stTabs [data-baseweb="tab"] {
    color: #78645a !important;
    font-weight: 500 !important;
}

.stTabs [aria-selected="true"] {
    color: #ea580c !important;
}

.stTabs [data-baseweb="tab-highlight"] {
    background: linear-gradient(90deg, #f59e0b, #db2777) !important;
    height: 3px !important;
}

/* Sidebar */
section[data-testid="stSidebar"] {
    background: #fdf3e2 !important;
    border-right: 1px solid #faead0;
}

section[data-testid="stSidebar"] .stMarkdown h2 {
    background: linear-gradient(135deg, #f59e0b 0%, #db2777 100%);
    -webkit-background-clip: text;
    background-clip: text;
    -webkit-text-fill-color: transparent;
    font-size: 28px !important;
}

/* Alerts */
div[data-testid="stAlert"] {
    border-radius: 10px;
    border-width: 1px;
}

/* Sliders */
.stSlider [role="slider"] {
    background: #ea580c !important;
    border-color: #ea580c !important;
}

/* Inputs and textareas */
.stTextInput input, .stTextArea textarea {
    background: white !important;
    border: 1px solid #faead0 !important;
    color: #1f1612 !important;
    border-radius: 8px !important;
}

.stTextInput input:focus, .stTextArea textarea:focus {
    border-color: #ea580c !important;
    box-shadow: 0 0 0 1px #ea580c !important;
}

/* Expander */
.streamlit-expanderHeader {
    background: white !important;
    border: 1px solid #faead0 !important;
    border-radius: 10px !important;
    border-left: 3px solid #ea580c !important;
}

/* File uploader */
[data-testid="stFileUploadDropzone"] {
    background: white !important;
    border: 2px dashed #faead0 !important;
    border-radius: 12px !important;
}

[data-testid="stFileUploadDropzone"]:hover {
    border-color: #ea580c !important;
    background: #fdf3e2 !important;
}

/* Selectbox */
.stSelectbox [data-baseweb="select"] {
    background: white !important;
    border-color: #faead0 !important;
}

/* Links */
a {
    color: #ea580c !important;
}

a:hover {
    color: #db2777 !important;
}
</style>
""", unsafe_allow_html=True)

username = login_page()

if username is None:
    st.stop()

user_data = get_user_data(username)

with st.sidebar:
    st.markdown("## Trovly")
    st.markdown("Logged in as **{}**".format(username))

    # Tier and usage display
    tier = get_user_tier(user_data)
    summary = get_usage_summary(username, tier)

    if tier == "free":
        st.markdown("**Tier:** Free")
        if summary["scans_remaining"] == 0:
            st.error("Scans: {} / {} (limit reached)".format(summary["scans_used"], summary["scans_limit"]))
        else:
            st.info("Scans: {} / {}".format(summary["scans_used"], summary["scans_limit"]))
        st.caption("Resume analyses: {} / {}".format(summary["tailors_used"], summary["tailors_limit"]))
        st.markdown("---")
        st.markdown("**Upgrade to Pro** for unlimited scans, more sources, and analytics.")
        st.button("Upgrade to Pro", disabled=True, help="Payment integration coming soon")
    else:
        st.success("Tier: {}".format(summary["tier_label"]))

    st.markdown("---")
    if st.button("Log out"):
        logout()
    st.markdown("---")

tab1, tab2, tab3, tab4 = st.tabs(["Setup", "Scan", "Tailor", "Applications"])

with tab1:
    st.markdown("### Your Profile")
    st.markdown("Paste your resume and set up your job search.")

    resume = st.text_area(
        "Resume",
        value=user_data.get("resume", ""),
        height=300,
        placeholder="Paste your full resume here...",
    )

    queries_str = st.text_area(
        "Job titles to search (one per line)",
        value="\n".join(user_data.get("queries", [])),
        height=150,
        placeholder="python developer\ndevops engineer\ncloud engineer",
    )

    col1, col2 = st.columns(2)
    with col1:
        threshold = st.slider(
            "Match threshold",
            0.3, 0.95,
            user_data.get("threshold", 0.55),
            0.05,
            format="%.0f%%",
        )
    with col2:
        remote_only = st.checkbox(
            "Remote only",
            value=user_data.get("remote_only", True),
        )

    if st.button("Save profile", type="primary"):
        queries_list = [q.strip() for q in queries_str.strip().split("\n") if q.strip()]
        save_user_data(username, {
            "resume": resume,
            "queries": queries_list,
            "threshold": threshold,
            "remote_only": remote_only,
        })
        st.success("Profile saved.")

with tab2:
    st.markdown("### Scan for Jobs")

    if not user_data.get("resume"):
        st.warning("Set up your profile first — paste your resume in the Setup tab.")
    else:
        st.markdown("**Resume loaded:** {} characters".format(len(user_data.get("resume", ""))))
        st.markdown("**Queries:** {}".format(", ".join(user_data.get("queries", []))))
        st.markdown("**Threshold:** {:.0%}".format(user_data.get("threshold", 0.55)))

        if st.button("Run scan now", type="primary"):
            allowed, msg = can_scan(username, tier)
            if not allowed:
                st.error(msg)
                st.stop()
            increment_scans(username)
            with st.spinner("Scanning job sources... this takes about 60 seconds."):
                try:
                    import config
                    config.RESUME_TEXT = user_data.get("resume", "")
                    config.SEARCH_QUERIES = user_data.get("queries", [])
                    config.SIMILARITY_THRESHOLD = user_data.get("threshold", 0.55)
                    config.REMOTE_ONLY = user_data.get("remote_only", True)

                    from sources import fetch_all_jobs
                    from matcher import match_jobs, reload_resume

                    reload_resume()
                    jobs = fetch_all_jobs()
                    st.info("Fetched {} jobs. Matching...".format(len(jobs)))

                    matched = match_jobs(jobs)

                    if matched:
                        st.success("Found {} matches.".format(len(matched)))
                        for job, score in matched:
                            with st.expander("{:.0%} — {} at {}".format(score, job.title, job.company)):
                                st.markdown("**Location:** {}".format(job.location or "Remote"))
                                if job.salary:
                                    st.markdown("**Salary:** {}".format(job.salary))
                                st.markdown("**Source:** {}".format(job.source))
                                st.link_button("Apply", job.url)
                    else:
                        st.warning("No matches above {:.0%}. Try lowering threshold in Setup.".format(
                            user_data.get("threshold", 0.55)))

                except Exception as e:
                    st.error("Scan failed: {}".format(e))

with tab3:
    st.markdown("### Resume Tailor")

    if not user_data.get("resume"):
        st.warning("Set up your profile first.")
    else:
        jd_input = st.text_area(
            "Paste a job description",
            height=250,
            placeholder="Paste the full job description here...",
        )

        if st.button("Analyze", type="primary"):
            allowed, msg = can_tailor(username, tier)
            if not allowed:
                st.error(msg)
                st.stop()
            if jd_input and len(jd_input) > 30:
                increment_tailors(username)
                with st.spinner("Analyzing..."):
                    try:
                        import config
                        config.RESUME_TEXT = user_data.get("resume", "")

                        from tailor import tailor_resume
                        from matcher import reload_resume
                        reload_resume()

                        result = tailor_resume(jd_input, verbose=False)

                        if "error" in result:
                            st.error(result["error"])
                        else:
                            total = result["total_bullets"]
                            strong_pct = len(result["strong_bullets"]) / total * 100 if total else 0

                            col1, col2, col3 = st.columns(3)
                            with col1:
                                st.metric("Relevance", "{:.0f}%".format(strong_pct))
                            with col2:
                                st.metric("Keywords matched", result["jd_keywords_found"])
                            with col3:
                                st.metric("Skill gaps", result["jd_keywords_missing"])

                            if result["strong_bullets"]:
                                st.markdown("#### Strong matches")
                                for b in result["strong_bullets"]:
                                    st.markdown("**{:.0%}** — {}".format(b["relevance"], b["text"]))

                            if result["moderate_bullets"]:
                                st.markdown("#### Moderate matches")
                                for b in result["moderate_bullets"][:8]:
                                    st.markdown("**{:.0%}** — {}".format(b["relevance"], b["text"]))

                            if result["skill_gaps"]:
                                st.markdown("#### Skill gaps")
                                for gap in result["skill_gaps"]:
                                    st.markdown("- **{}**".format(gap))
                            else:
                                st.success("No skill gaps detected.")

                    except Exception as e:
                        st.error("Analysis failed: {}".format(e))

# ─── APPLICATIONS TAB ───────────────────────────────────────────────
with tab4:
    st.markdown("### Application Tracker")

    stats = get_stats(username)

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total applications", stats["total"])
    with col2:
        st.metric("Active", stats["active"])
    with col3:
        st.metric("Interview rate", "{}%".format(stats["interview_rate"]))
    with col4:
        st.metric("Offer rate", "{}%".format(stats["offer_rate"]))

    st.markdown("---")

    # Follow-up reminders
    follow_ups = get_follow_ups(username, days_threshold=7)
    if follow_ups:
        with st.expander("Follow-ups needed ({})".format(len(follow_ups)), expanded=True):
            for app in follow_ups[:10]:
                st.markdown("**{}** at {} - {} days since last update".format(
                    app["title"], app["company"], app["days_since_update"]
                ))

    st.markdown("---")

    # Add new application
    with st.expander("Add new application", expanded=False):
        col_t, col_c = st.columns(2)
        with col_t:
            new_title = st.text_input("Job title", key="new_app_title", max_chars=200)
            new_url = st.text_input("URL", key="new_app_url", max_chars=500)
            new_location = st.text_input("Location", key="new_app_location", max_chars=100)
        with col_c:
            new_company = st.text_input("Company", key="new_app_company", max_chars=100)
            new_salary = st.text_input("Salary", key="new_app_salary", max_chars=100)
            new_notes_short = st.text_input("Initial notes", key="new_app_notes", max_chars=500)

        if st.button("Add to tracker", type="primary"):
            success, msg, _ = add_application(
                username, new_title, new_company,
                url=new_url, location=new_location,
                salary=new_salary, notes=new_notes_short,
            )
            if success:
                st.success(msg)
                st.rerun()
            else:
                st.error(msg)

    st.markdown("---")

    # Filter controls
    col_f1, col_f2 = st.columns(2)
    with col_f1:
        filter_status = st.multiselect(
            "Filter by status",
            options=STATUS_OPTIONS,
            default=[],
            key="app_filter_status",
        )
    with col_f2:
        sort_options = {
            "date_applied": "Date applied (newest first)",
            "last_updated": "Last updated",
            "company": "Company A-Z",
            "status": "Status",
        }
        sort_choice = st.selectbox(
            "Sort by",
            options=list(sort_options.keys()),
            format_func=lambda x: sort_options[x],
            key="app_sort",
        )

    # List applications
    apps = list_applications(
        username,
        status_filter=filter_status if filter_status else None,
        sort_by=sort_choice,
        reverse=(sort_choice in ["date_applied", "last_updated"]),
    )

    if not apps:
        st.info("No applications tracked yet. Add one above or track from scan results.")
    else:
        st.markdown("**{} applications**".format(len(apps)))

        for app in apps:
            with st.expander("{} at {} - {}".format(app["title"], app["company"], app["status"])):
                col_l, col_r = st.columns([3, 1])

                with col_l:
                    if app.get("url"):
                        st.markdown("[Open posting]({})".format(app["url"]))
                    if app.get("location"):
                        st.markdown("**Location:** {}".format(app["location"]))
                    if app.get("salary"):
                        st.markdown("**Salary:** {}".format(app["salary"]))
                    st.caption("Applied: {}".format(app.get("date_applied", "")[:10]))
                    st.caption("Last updated: {}".format(app.get("last_updated", "")[:10]))

                with col_r:
                    new_status = st.selectbox(
                        "Status",
                        options=STATUS_OPTIONS,
                        index=STATUS_OPTIONS.index(app["status"]) if app["status"] in STATUS_OPTIONS else 0,
                        key="status_{}".format(app["id"]),
                    )
                    if new_status != app["status"]:
                        update_application(username, app["id"], {"status": new_status})
                        st.rerun()

                # Notes
                current_notes = app.get("notes", "")
                new_notes = st.text_area(
                    "Notes",
                    value=current_notes,
                    height=100,
                    key="notes_{}".format(app["id"]),
                    placeholder="Recruiter name, salary discussions, interview feedback, etc.",
                )

                col_save, col_del = st.columns([1, 1])
                with col_save:
                    if new_notes != current_notes:
                        if st.button("Save notes", key="save_notes_{}".format(app["id"])):
                            update_application(username, app["id"], {"notes": new_notes})
                            st.success("Notes saved")
                            st.rerun()
                with col_del:
                    confirm_key = "confirm_del_{}".format(app["id"])
                    if st.button("Delete", key="del_{}".format(app["id"]), type="secondary"):
                        if st.session_state.get(confirm_key):
                            delete_application(username, app["id"])
                            st.session_state[confirm_key] = False
                            st.rerun()
                        else:
                            st.session_state[confirm_key] = True
                            st.warning("Click Delete again to confirm")

                # Status history
                history = app.get("status_history", [])
                if len(history) > 1:
                    st.markdown("**Status history:**")
                    for h in history:
                        st.caption("{}: {}".format(h.get("date", "")[:10], h.get("status", "")))
